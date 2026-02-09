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
from app.users.auth import box_user_info_mapper


def test__box_user_info_mapper() -> None:
    user_id = "11446498"
    email = "jim.halpert@example.com"

    raw_data = {
        "id": user_id,
        "type": "user",
        "address": "8200 KEYSTONE DR, OMAHA NE",
        "avatar_url": "https://www.box.com/api/avatar/large/181216415",
        "can_see_managed_users": True,
        "created_at": "2012-12-12T10:53:43-08:00",
        "enterprise": {"id": "11446498", "type": "enterprise", "name": "Acme Inc."},
        "external_app_user_id": "my-user-1234",
        "hostname": "https://example.app.box.com/",
        "is_exempt_from_device_limits": True,
        "is_exempt_from_login_verification": True,
        "is_external_collab_restricted": True,
        "is_platform_access_only": True,
        "is_sync_enabled": True,
        "job_title": "CEO",
        "language": "en",
        "login": email,
        "max_upload_size": 2147483648,
        "modified_at": "2012-12-12T10:53:43-08:00",
        "my_tags": ["important"],
        "name": "Jim Halpert",
        "notification_email": {
            "email": "notifications@example.com",
            "is_confirmed": True,
        },
        "phone": "6509241374",
        "role": "admin",
        "space_amount": 11345156112,
        "space_used": 1237009912,
        "status": "active",
        "timezone": "Africa/Bujumbura",
        "tracking_codes": [
            {"name": "department", "type": "tracking_code", "value": "Sales"}
        ],
    }

    user = box_user_info_mapper(raw_data)

    assert user.id == user_id
    assert user.email == email
    assert user.photo_url
    assert user.name
    assert user.phone_number
    assert user.given_name == "Jim"
    assert user.family_name == "Halpert"
    assert user.metadata
    assert len(user.metadata.keys()) == 32
