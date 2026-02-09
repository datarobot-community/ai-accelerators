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

"""change_identity_unique_constraint_to_composite

Revision ID: f57c1294b74e
Revises: a9506ba8d2ab
Create Date: 2025-10-23 08:52:19.793177

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f57c1294b74e"
down_revision: Union[str, Sequence[str], None] = "a9506ba8d2ab"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop the old single-column unique constraint
    with op.batch_alter_table("identity", schema=None) as batch_op:
        batch_op.drop_constraint("uq_identity_provider_user_id", type_="unique")

        # Create the new composite unique constraint
        batch_op.create_unique_constraint(
            "uq_identity_provider_user_id_type",
            ["provider_user_id", "provider_type"],
        )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop the composite unique constraint
    with op.batch_alter_table("identity", schema=None) as batch_op:
        batch_op.drop_constraint("uq_identity_provider_user_id_type", type_="unique")

        # Recreate the old single-column unique constraint
        batch_op.create_unique_constraint(
            "uq_identity_provider_user_id", ["provider_user_id"]
        )
