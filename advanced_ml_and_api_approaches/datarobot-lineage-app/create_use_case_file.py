import json
import os
from pathlib import Path

import datarobot as dr
from dotenv import load_dotenv

load_dotenv(override=True)
script_path = Path(__file__).parent.absolute()
print(script_path)
client = dr.Client()

use_cases = dr.UseCase.list()
use_cases_list = [dict(name=u.name, id=u.id) for u in use_cases]


with open(os.path.join(script_path, "use_case_list.json"), "w") as f:
    f.write(json.dumps(use_cases_list))
