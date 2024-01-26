# DataRobot Simple Log Lister

This note book provides a user with a method of changing the output of User Activity Monitor to allow the user to drop an entire column of output or change the contents of that column in a way to preserve the anonymity of the column but maintain consistency for reporting.

## Required Permissions

The user that executes this notebook, must have the following permissions:

- `ADMIN_API_ACCESS`
- `CAN_ACCESS_USER_ACTIVITY`

## NOTE 1:

This notebook assumes usage from a local laptop or similar, using a `.env` file with the following format:

```bash
# Where to connect
DATAROBOT_ENDPOINT = 'https://datarobot.example.com'

# A valid API key from a user with the permissions above
DATAROBOT_API_TOKEN = ''
```

### Copyright 2024 DataRobot Inc

**All Rights Reserved.**

This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, express or implied.
