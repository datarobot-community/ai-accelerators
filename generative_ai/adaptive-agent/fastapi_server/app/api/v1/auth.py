# Copyright 2025 DataRobot, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import logging
import uuid

from datarobot.auth.oauth import (
    OAuthData,
    OAuthProvider,
    OAuthToken,
)
from datarobot.auth.session import AuthCtx
from datarobot.auth.typing import Metadata
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError

from app.api.v1.schema import ErrorCodes, ErrorSchema
from app.auth.api_key import APIKeyValidator, DRUser, dr_api_key_schema
from app.auth.ctx import AUTH_SESS_KEY, get_auth_ctx, must_get_auth_ctx
from app.auth.session import restore_oauth_session, store_oauth_sess
from app.users.identity import AuthSchema, Identity, IdentityUpdate
from app.users.tokens import Tokens
from app.users.user import User, UserCreate

logger = logging.getLogger(name=__name__)


class OAuthRedirectSchema(BaseModel):
    redirect_url: str


class OAuthProviderListSchema(BaseModel):
    providers: list[OAuthProvider]


class OAuthDataSchema(BaseModel):
    providers: list[OAuthProvider]


class OAuthIdentityValidationSchema(BaseModel):
    provider_id: str
    provider_type: str
    is_valid: bool
    error_status_code: int | None = None


class ValidateOAuthIdentitiesResponse(BaseModel):
    identities: list[OAuthIdentityValidationSchema]


class IdentitySchema(BaseModel):
    uuid: uuid.UUID
    type: str
    provider_id: str
    provider_type: str
    provider_user_id: str
    provider_identity_id: str | None = None

    @classmethod
    def from_identity(cls, identity: Identity) -> "IdentitySchema":
        return cls(
            uuid=identity.uuid,
            type=identity.type.value,
            provider_id=identity.provider_id,
            provider_type=identity.provider_type,
            provider_user_id=identity.provider_user_id,
            provider_identity_id=identity.provider_identity_id,
        )


class UserSchema(BaseModel):
    uuid: uuid.UUID
    email: str
    first_name: str | None = None
    last_name: str | None = None
    profile_image_url: str | None = None

    identities: list[IdentitySchema] = Field(..., alias="identities")

    @classmethod
    def from_user(cls, user: User) -> "UserSchema":
        return cls(
            uuid=user.uuid,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            profile_image_url=user.profile_image_url,
            identities=[
                IdentitySchema.from_identity(identity) for identity in user.identities
            ],
        )


class OAuthTokenRequestSchema(BaseModel):
    identity_id: int
    scope: str | None = None

    class Config:
        json_schema_extra = {
            "example": {
                "identity_id": 1,
                "scope": None,
            }
        }


auth_router = APIRouter(tags=["Authentication"])


@auth_router.get("/oauth/")
async def oauth_list_providers(request: Request) -> OAuthProviderListSchema:
    """
    List available OAuth providers.
    """
    auth = request.app.state.deps.auth
    providers = await auth.get_providers()

    return OAuthProviderListSchema(providers=providers)


@auth_router.post("/oauth/authorize/")
async def oauth_login(
    request: Request, *, provider_id: str, redirect_uri: str | None = None
) -> OAuthRedirectSchema:
    """
    Start the OAuth flow for the given provider.
    """
    auth = request.app.state.deps.auth

    # Ensure the redirect_uri respects the application's root_path (URL prefix)
    root_path = request.scope.get("root_path", "")
    callback_path = str(request.url_for("oauth_callback"))
    if root_path and callback_path.startswith("/"):
        real_redirect = root_path.rstrip("/") + callback_path
    else:
        real_redirect = callback_path

    if redirect_uri:
        real_redirect = redirect_uri

    oauth_sess = await auth.get_authorization_url(
        provider_id=provider_id,
        redirect_uri=real_redirect,
    )

    # APP-4401. Resolve after this is fixed in the DataRobot oauth-providers-service
    oauth_sess.authorization_url = oauth_sess.authorization_url.replace(
        "root_readonly", "root_readwrite"
    )
    store_oauth_sess(request, oauth_sess)

    return OAuthRedirectSchema(
        redirect_url=oauth_sess.authorization_url,
    )


@auth_router.get("/oauth/callback/")  # for local tests
@auth_router.post("/oauth/callback/")
async def oauth_callback(
    request: Request,
    auth_ctx: AuthCtx[Metadata] | None = Depends(get_auth_ctx),
) -> UserSchema:
    """
    Finish the OAuth Authorization Flow for the given provider.
    If there is an existing user session, we are trying to link it to the new OAuth provider connection.
    If not, then we try to find an existing user account by email and create a new OAuth connection for it.
    Otherwise, this is a completely new user to authenticate.
    """
    user_repo = request.app.state.deps.user_repo
    identity_repo = request.app.state.deps.identity_repo
    auth = request.app.state.deps.auth

    params = request.query_params

    # Provider returned error (e.g., user cancelled consent)
    if "error" in params:
        err = ErrorSchema(code=ErrorCodes.UNKNOWN_ERROR, message=params["error"])
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=err.model_dump()
        )

    state = params.get("state")

    logger.debug("OAuth callback", extra={"state": state})

    if not state or "code" not in params:
        err = ErrorSchema(
            code=ErrorCodes.INVALID_OAUTH_STATE,
            message="OAuth authorization code and state are required",
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=err.model_dump()
        )

    oauth_sess = restore_oauth_session(request, state)

    if oauth_sess is None:
        err = ErrorSchema(
            code=ErrorCodes.INVALID_OAUTH_STATE,
            message="Invalid OAuth state or session expired. Try to start the OAuth flow again.",
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=err.model_dump()
        )

    provider_id = oauth_sess.provider_id

    logger.info(
        "exchanging oauth authorization code", extra={"provider_id": provider_id}
    )

    try:
        oauth_data: OAuthData = await auth.exchange_code(
            provider_id=provider_id,
            sess=oauth_sess,
            params=params,
        )
    except Exception as e:
        logger.exception(
            "OAuth service error during code exchange",
            extra={"provider_id": provider_id, "error": str(e)},
            exc_info=True,
        )
        err = ErrorSchema(
            code=ErrorCodes.UNKNOWN_ERROR,
            message=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=err.model_dump()
        )

    token_data = oauth_data.token_data
    user_profile = oauth_data.user_profile

    if not user_profile:
        err = ErrorSchema(
            code=ErrorCodes.UNKNOWN_ERROR,
            message="Could not get user profile from OAuth provider, but it must be there to authenticate user",
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=err.model_dump()
        )

    token_data_update = {}

    if token_data:
        token_data_update = {
            "access_token": token_data.access_token,
            "refresh_token": token_data.refresh_token,
            "expires_at": token_data.expires_at,
        }

    identity_update = IdentityUpdate(
        provider_identity_id=oauth_data.authorization_id,
        **token_data_update,
    )

    user: User

    if auth_ctx:
        # there is already a user session which means we are trying to link an OAuth Provider to existing user account
        identity = await identity_repo.upsert_identity(
            auth_type=AuthSchema.OAUTH2,
            user_id=int(auth_ctx.user.id),
            provider_id=oauth_data.provider.id,
            provider_type=oauth_data.provider.type,
            provider_user_id=user_profile.id,
            update=identity_update,
        )

        logger.info(
            "upserted identity for existing user",
            extra={"identity": identity, "user_id": auth_ctx.user.id},
        )

        # refresh the session
        user = await user_repo.get_user(user_id=int(auth_ctx.user.id))

        if not user:
            logger.error("session user not found", extra={"auth_ctx": auth_ctx})
            err = ErrorSchema(
                code=ErrorCodes.UNKNOWN_ERROR,
                message="Could not find user in the session during callback",
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=err.model_dump(),
            )

        request.session[AUTH_SESS_KEY] = user.to_auth_ctx().model_dump()

        return UserSchema.from_user(user)

    # we are trying to authenticate a user at this point
    identity = await identity_repo.get_by_external_user_id(
        provider_type=oauth_data.provider.type,
        provider_user_id=user_profile.id,
    )

    if not identity:
        user = await user_repo.get_user(email=user_profile.email)

        if not user:
            # we did our best to find an existing user, but we couldn't, so let's create a new user account
            try:
                user = await user_repo.create_user(
                    UserCreate(
                        first_name=user_profile.given_name,
                        last_name=user_profile.family_name,
                        email=user_profile.email,
                        profile_image_url=user_profile.photo_url,
                    ),
                )
                logger.info("created new user", extra={"user_id": user.id})
            except IntegrityError:
                # Race condition: user was created between our check and create attempt
                # Try to get the existing user
                user = await user_repo.get_user(email=user_profile.email)
                if not user:
                    # If we still can't find the user, re-raise the original error
                    raise
                logger.info(
                    "loaded existing user after race condition",
                    extra={"user_id": user.id},
                )
        else:
            logger.info("loaded user by email", extra={"user_id": user.id})

        identity = await identity_repo.upsert_identity(
            auth_type=AuthSchema.OAUTH2,
            user_id=user.id,
            provider_id=oauth_data.provider.id,
            provider_type=oauth_data.provider.type,
            provider_user_id=user_profile.id,
            update=identity_update,
        )

        logger.info("logged in user", extra={"user_id": user.id, "identity": identity})

        # Refresh the user in order to get the actual identities array

        user = await user_repo.get_user(user_id=identity.user_id)
        request.session[AUTH_SESS_KEY] = user.to_auth_ctx().model_dump()

        return UserSchema.from_user(user)

    user = await user_repo.get_user(user_id=identity.user_id)
    request.session[AUTH_SESS_KEY] = user.to_auth_ctx().model_dump()

    return UserSchema.from_user(user)


async def validate_dr_api_key(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(dr_api_key_schema),
) -> DRUser:
    """
    Loads DataRobot API key from the incoming request and validates it.
    """
    api_key_validator: APIKeyValidator = request.app.state.deps.api_key_validator

    api_key = credentials.credentials
    dr_user = await api_key_validator.validate(api_key)

    if not dr_user:
        err = ErrorSchema(
            code=ErrorCodes.NOT_AUTHED,
            message="You are not authenticated to access this resource.",
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=err.model_dump()
        )

    return dr_user


@auth_router.post("/oauth/token/", responses={401: {"model": ErrorSchema}})
async def get_token(
    request: Request,
    payload: OAuthTokenRequestSchema,
    # TODO: we check the existence/validity of the key, we still miss the authorization/permission checks here.
    dr_user: DRUser = Depends(validate_dr_api_key),
) -> OAuthToken:
    identity_repo = request.app.state.deps.identity_repo
    oauth_tokens: Tokens = request.app.state.deps.tokens

    identity = await identity_repo.get_identity_by_id(identity_id=payload.identity_id)

    if not identity:
        err = ErrorSchema(
            code=ErrorCodes.IDENTITY_NOT_FOUND,
            message=f"Identity with id {payload.identity_id} not found",
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=err.model_dump()
        )

    logger.info(
        "getting access token by identity",
        extra={
            "identity_id": payload.identity_id,
            "scope": payload.scope,
            "provider_id": identity.provider_id,
            "provider_type": identity.provider_type,
        },
    )

    token_data = await oauth_tokens.get_access_token(identity, payload.scope)

    return token_data


@auth_router.get("/user/", responses={401: {"model": ErrorSchema}})
async def get_user(
    request: Request, auth_ctx: AuthCtx[Metadata] = Depends(must_get_auth_ctx)
) -> UserSchema:
    """
    Get the current user information.
    """
    user_repo = request.app.state.deps.user_repo

    user = await user_repo.get_user(user_id=int(auth_ctx.user.id))

    if not user:
        logger.error("session user not found", extra={"auth_ctx": auth_ctx})
        err = ErrorSchema(
            code=ErrorCodes.UNKNOWN_ERROR,
            message="Could not find user in the session",
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=err.model_dump()
        )

    # refresh our session just in case
    request.session[AUTH_SESS_KEY] = user.to_auth_ctx().model_dump()

    return UserSchema.from_user(user)


@auth_router.post("/oauth/validate/", responses={401: {"model": ErrorSchema}})
async def validate_oauth_identities(
    request: Request,
    auth_ctx: AuthCtx[Metadata] = Depends(must_get_auth_ctx),
) -> ValidateOAuthIdentitiesResponse:
    """
    Validate OAuth tokens for all connected identities by forcing a refresh.
    Deletes identities that have been revoked (401/404/410).
    """
    user_repo = request.app.state.deps.user_repo
    identity_repo = request.app.state.deps.identity_repo
    tokens: Tokens = request.app.state.deps.tokens

    user = await user_repo.get_user(user_id=int(auth_ctx.user.id))

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorSchema(
                code=ErrorCodes.UNKNOWN_ERROR, message="User not found"
            ).model_dump(),
        )

    results: list[OAuthIdentityValidationSchema] = []
    deleted_any = False

    for identity in user.identities:
        # Skip non-OAuth identities
        if identity.type == AuthSchema.OAUTH2:
            is_valid, error_code = await tokens.validate_token(identity.to_data())

            results.append(
                OAuthIdentityValidationSchema(
                    provider_id=identity.provider_id,
                    provider_type=identity.provider_type,
                    is_valid=is_valid,
                    error_status_code=error_code,
                )
            )

            # Delete identity if revoked (401/404/410)
            if not is_valid and error_code in (401, 404, 410):
                await identity_repo.delete_by_id(identity.id)
                deleted_any = True
                logger.info(
                    "Deleted revoked OAuth identity",
                    extra={"identity_id": identity.id, "user_id": user.id},
                )

    # Refresh session if any identities were deleted to keep session in sync
    if deleted_any:
        user = await user_repo.get_user(user_id=int(auth_ctx.user.id))
        if user:
            request.session[AUTH_SESS_KEY] = user.to_auth_ctx().model_dump()

    return ValidateOAuthIdentitiesResponse(identities=results)


@auth_router.post("/logout/", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: Request) -> None:
    """Logout the current user"""
    request.session.clear()

    return None
