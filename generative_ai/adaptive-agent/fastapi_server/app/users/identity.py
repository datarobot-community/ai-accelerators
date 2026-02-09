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
import uuid as uuidpkg
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Final

from datarobot.auth.identity import Identity as IdentityData
from sqlalchemy import Column, DateTime, UniqueConstraint
from sqlalchemy.exc import IntegrityError
from sqlmodel import Field, Relationship, SQLModel, select

from app.db import DBCtx
from app.users.user import User

UPSERT_RETRIES: Final = 3


class AuthSchema(str, Enum):
    """The type of connection"""

    DATAROBOT = "datarobot"
    OAUTH2 = "oauth2"


class ProviderType(str, Enum):
    DATAROBOT_USER = "datarobot_user"
    EXTERNAL_EMAIL = "datarobot_ext_email"
    GOOGLE = "google"
    BOX = "box"
    MICROSOFT = "microsoft"


class Identity(SQLModel, table=True):
    """The sign-in identity of the application user for a given provider."""

    __table_args__ = (
        UniqueConstraint(
            "provider_user_id",
            "provider_type",
            name="uq_identity_provider_user_id_type",
        ),
    )

    id: int | None = Field(default=None, primary_key=True, unique=True)
    uuid: uuidpkg.UUID = Field(default_factory=uuidpkg.uuid4, index=True, unique=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    type: AuthSchema = Field(
        default=AuthSchema.OAUTH2,
        description="Type of connection that represents authentication schema",
    )

    user_id: int = Field(foreign_key="user.id", index=True, nullable=False)
    user: User = Relationship(back_populates="identities")

    provider_id: str = Field(None, description="The ID of the provider")
    provider_type: str = Field(
        description="The name of the provider"
    )  # keep it str to make extensible
    provider_user_id: str = Field(
        description="The external user ID on the provider side"
    )
    provider_identity_id: str | None = Field(
        None,
        unique=True,
        description="The external connection ID on the provider side (if the provider manages connections internally)",
    )

    access_token: str | None = Field(
        None, description="The access token for the connection"
    )
    access_token_expires_at: datetime | None = Field(
        None,
        description="The expiration date of the access token",
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    refresh_token: str | None = Field(
        None, description="The refresh token for the connection"
    )

    datarobot_org_id: str | None = Field(
        None,
        description="The DataRobot organization ID associated with the connection",
    )

    datarobot_tenant_id: str | None = Field(
        None,
        description="The DataRobot tenant ID associated with the connection",
    )

    def access_token_expired(self, leeway_secs: int | None = None) -> bool:
        if self.access_token_expires_at is None:
            return False

        leeway = timedelta(seconds=leeway_secs or 0)
        token_expires_at = (
            self.access_token_expires_at.replace(tzinfo=timezone.utc) - leeway
        )

        return datetime.now(timezone.utc) > token_expires_at

    def to_data(self) -> IdentityData:
        return IdentityData(
            id=str(self.id),
            type=self.type,
            provider_type=self.provider_type,
            provider_user_id=self.provider_user_id,
            provider_identity_id=self.provider_identity_id,
        )


class IdentityUpdate(SQLModel):
    """
    Schema for updating an existing connection.
    """

    provider_user_id: str | None = None
    provider_identity_id: str | None = None

    access_token: str | None = None
    access_token_expires_at: datetime | None = None
    refresh_token: str | None = None

    datarobot_org_id: str | None = None
    datarobot_tenant_id: str | None = None


class IdentityCreate(IdentityUpdate):
    """
    Schema for creating a new connection.
    """

    user_id: int
    type: AuthSchema = AuthSchema.OAUTH2
    provider_id: str
    provider_type: str
    provider_user_id: str


class IdentityRepository:
    """
    Connection repository class to handle connection-related database operations.
    """

    def __init__(self, db: DBCtx):
        self._db = db

    async def create_identity(self, identity_data: IdentityCreate) -> Identity:
        """
        Create a new connection in the database.
        """
        identity = Identity(**identity_data.model_dump())

        async with self._db.session(writable=True) as sess:
            sess.add(identity)
            await sess.commit()
            await sess.refresh(identity)

        return identity

    async def get_identity_by_id(
        self, identity_id: int | None = None, identity_uuid: uuidpkg.UUID | None = None
    ) -> Identity | None:
        """
        Retrieve a connection by its ID.
        """
        if identity_id is None and identity_uuid is None:
            raise ValueError("Either identity_id or identity_uuid must be provided.")

        async with self._db.session() as sess:
            query = await sess.exec(
                select(Identity).where(
                    (Identity.id == identity_id) | (Identity.uuid == identity_uuid)
                )
            )

            return query.first()

    async def get_by_user_id(self, provider_type: str, user_id: int) -> Identity | None:
        """
        Retrieve a connection by its provider and user ID.
        """
        async with self._db.session() as sess:
            query = await sess.exec(
                select(Identity).where(
                    (Identity.provider_type == provider_type)
                    & (Identity.user_id == user_id)
                )
            )

            return query.first()

    async def get_by_external_user_id(
        self,
        provider_type: str,
        provider_user_id: str,
        auth_type: AuthSchema = AuthSchema.OAUTH2,
    ) -> Identity | None:
        """
        Retrieve a connection by its provider and provider user ID.
        """
        async with self._db.session() as sess:
            query = await sess.exec(
                select(Identity).where(
                    (Identity.type == auth_type)
                    & (Identity.provider_type == provider_type)
                    & (Identity.provider_user_id == provider_user_id)
                )
            )

            return query.first()

    async def upsert_identity(
        self,
        user_id: int,
        auth_type: AuthSchema,
        provider_id: str,
        provider_type: str,
        provider_user_id: str,
        update: IdentityUpdate | None = None,
    ) -> Identity:
        """
        Upsert a connection in the database.

        Note: provider_user_id has a unique constraint, so the same email
        can only exist once in the database, regardless of provider.
        """
        provider_id_str = provider_id
        provider_type_str = provider_type

        attempt = 0
        while True:
            attempt += 1
            async with self._db.session(writable=True) as sess:
                query = await sess.exec(
                    select(Identity).where(
                        (Identity.provider_user_id == provider_user_id)
                        & (Identity.provider_type == provider_type_str)
                    )
                )
                identity = query.first()

                if identity is None:
                    identity = Identity(
                        type=auth_type,
                        user_id=user_id,
                        provider_id=provider_id_str,
                        provider_type=provider_type_str,
                        provider_user_id=provider_user_id,
                        provider_identity_id=None,
                        access_token=None,
                        access_token_expires_at=None,
                        refresh_token=None,
                        datarobot_org_id=None,
                        datarobot_tenant_id=None,
                    )
                else:
                    identity.type = auth_type
                    identity.user_id = user_id
                    identity.provider_id = provider_id_str
                    identity.provider_type = provider_type_str

                if update:
                    for field, value in update.model_dump(exclude_unset=True).items():
                        if value is not None:
                            setattr(identity, field, value)

                sess.add(identity)
                try:
                    await sess.flush()
                    await sess.commit()
                    return identity
                except IntegrityError:
                    await sess.rollback()
                    if attempt >= UPSERT_RETRIES:
                        raise
                    continue

    async def update_identity(
        self, identity_id: int, update: IdentityUpdate
    ) -> Identity | None:
        """
        Update an existing connection in the database.
        """
        async with self._db.session(writable=True) as sess:
            identity = await self.get_identity_by_id(identity_id=identity_id)

            if not identity:
                return None

            for field, value in update.model_dump(exclude_unset=True).items():
                setattr(identity, field, value)

            sess.add(identity)
            await sess.commit()
            await sess.refresh(identity)

        return identity

    async def delete_by_id(self, identity_id: int) -> None:
        """
        Delete a connection by its ID.
        """
        async with self._db.session(writable=True) as sess:
            identity = await self.get_identity_by_id(identity_id)

            if not identity:
                return

            await sess.delete(identity)
            await sess.commit()

    async def delete_by_user_id(self, user_id: int) -> None:
        """
        Delete all connections for a given user ID.
        """
        async with self._db.session(writable=True) as sess:
            async with sess.begin():
                connections = await sess.exec(
                    select(Identity).where(Identity.user_id == user_id)
                )

                for connection in connections:
                    await sess.delete(connection)

                await sess.commit()
