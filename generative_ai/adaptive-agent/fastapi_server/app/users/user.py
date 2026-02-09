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
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from datarobot.auth.session import AuthCtx
from datarobot.auth.typing import Metadata
from datarobot.auth.users import User as UserData
from sqlalchemy import Column, DateTime
from sqlmodel import Field, Relationship, SQLModel, select

from app.db import DBCtx

if TYPE_CHECKING:
    from app.users.identity import Identity


class User(SQLModel, table=True):
    """The application user."""

    id: int | None = Field(default=None, primary_key=True, unique=True)
    uuid: uuidpkg.UUID = Field(default_factory=uuidpkg.uuid4, index=True, unique=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    first_name: str | None = Field(None, min_length=2)
    last_name: str | None = Field(None)
    email: str = Field(..., unique=True, min_length=2, max_length=255)
    profile_image_url: str | None = None

    identities: list["Identity"] = Relationship(
        back_populates="user",
        cascade_delete=True,
        sa_relationship_kwargs={"lazy": "joined"},
    )

    def to_auth_ctx(self) -> AuthCtx[Metadata]:
        """
        Convert the User model to a UserData object.
        """
        user_data = UserData(
            id=str(self.id),
            given_name=self.first_name,
            family_name=self.last_name,
            email=self.email,
            profile_picture_url=self.profile_image_url,
        )

        return AuthCtx[Metadata](
            user=user_data,
            identities=[identity.to_data() for identity in self.identities],
        )


class UserCreate(SQLModel):
    """
    Schema for creating a new user.
    """

    first_name: str | None = Field(None, min_length=2, max_length=50)
    last_name: str | None = Field(None, max_length=50)
    email: str = Field(..., unique=True, min_length=2, max_length=255)
    profile_image_url: str | None = None


class UserRepository:
    """
    User repository class to handle user-related database operations.
    """

    def __init__(self, db: DBCtx):
        self._db = db

    async def get_user(
        self,
        user_id: int | None = None,
        user_uuid: uuidpkg.UUID | None = None,
        email: str | None = None,
    ) -> User | None:
        """
        Retrieve a user by their ID.
        """
        if user_id is None and user_uuid is None and email is None:
            raise ValueError("Either user_id, user_uuid, or email must be provided.")

        async with self._db.session() as sess:
            query = await sess.exec(
                select(User).where(
                    (User.id == user_id)
                    | (User.uuid == user_uuid)
                    | (User.email == email)
                )
            )

            return query.first()

    async def create_user(self, user_data: UserCreate) -> User:
        """
        Create a new user in the database.
        """
        user = User(**user_data.model_dump())

        async with self._db.session(writable=True) as session:
            session.add(user)
            await session.commit()
            await session.refresh(user)

        return user
