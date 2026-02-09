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

"""agui_chat_changes

Adds / modifies tables to support AGUI format.

Revision ID: 4d5262be920d
Revises: 5efc58e62518
Create Date: 2025-10-28 08:34:48.838213

"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4d5262be920d"
down_revision: Union[str, Sequence[str], None] = "5efc58e62518"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "chat",
        sa.Column(
            "thread_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True, default=None
        ),
    )
    with op.batch_alter_table("chat") as batch_op:
        batch_op.create_unique_constraint(
            constraint_name=op.f("uq_thread_id_user"), columns=["thread_id", "user"]
        )
    op.create_index(
        index_name=op.f("ix_thread_id_user"),
        table_name="chat",
        columns=("thread_id", "user"),
    )
    op.alter_column(table_name="message", column_name="model", new_column_name="name")
    # This column had not been used in code, so will be all blank/default. This update properly implements it with tool + reasoning tables
    op.drop_column(table_name="message", column_name="components")
    op.add_column(
        table_name="message",
        column=sa.Column(
            "agui_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True, default=None
        ),
    )
    op.add_column(
        table_name="message",
        column=sa.Column(
            "step", sqlmodel.sql.sqltypes.AutoString(), nullable=True, default=None
        ),
    )
    with op.batch_alter_table("message") as batch_op:
        batch_op.create_unique_constraint(
            constraint_name=op.f("uq_chat_id_agui_id"), columns=["chat_id", "agui_id"]
        )
    op.create_index(
        index_name=op.f("ix_chat_id_agui_id"),
        table_name="message",
        columns=("chat_id", "agui_id"),
    )

    op.create_table(
        "message_tool_call",
        sa.Column("uuid", sa.Uuid(), nullable=False),
        sa.Column("message_uuid", sa.Uuid(), nullable=False),
        sa.Column("agui_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("tool_call_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("role", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("arguments", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("content", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("in_progress", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("error", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.ForeignKeyConstraint(["message_uuid"], ["message.uuid"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("uuid"),
    )
    op.create_index(
        op.f("ix_message_tool_call_message_uuid"),
        "message_tool_call",
        ["message_uuid"],
        unique=False,
    )
    op.create_index(
        op.f("ix_message_tool_call_created_at"),
        "message_tool_call",
        ["created_at"],
        unique=False,
    )

    op.create_table(
        "message_reasoning",
        sa.Column("uuid", sa.Uuid(), nullable=False),
        sa.Column("message_uuid", sa.Uuid(), nullable=False),
        sa.Column("agui_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("role", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("content", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("in_progress", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("error", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.ForeignKeyConstraint(["message_uuid"], ["message.uuid"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("uuid"),
    )
    op.create_index(
        op.f("ix_message_reasoning_message_uuid"),
        "message_reasoning",
        ["message_uuid"],
        unique=False,
    )
    op.create_index(
        op.f("ix_message_reasoning_created_at"),
        "message_reasoning",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("chat"):
        op.drop_constraint(table_name="chat", constraint_name=op.f("uq_thread_id_user"))
        op.drop_index(table_name="chat", index_name=op.f("ix_thread_id_user"))
        op.drop_column(table_name="chat", column_name="thread_id")
    with op.batch_alter_table("message"):
        op.alter_column(
            table_name="message", column_name="name", new_column_name="model"
        )
        op.add_column(
            table_name="message",
            column=sa.Column(
                "components", sqlmodel.sql.sqltypes.AutoString(), nullable=False
            ),
        )
        op.drop_constraint(
            table_name="message", constraint_name=op.f("uq_chat_id_agui_id")
        )
        op.drop_index(table_name="message", index_name=op.f("ix_chat_id_agui_id"))
        op.drop_column(table_name="message", column_name="agui_id")
        op.drop_column(table_name="message", column_name="step")
    op.drop_index(op.f("ix_message_reasoning_message_uuid"))
    op.drop_index(op.f("ix_message_reasoning_created_at"))
    op.drop_table("message_reasoning")
    op.drop_index(op.f("ix_message_tool_call_message_uuid"))
    op.drop_index(op.f("ix_message_tool_call_created_at"))
    op.drop_table("message_tool_call")
