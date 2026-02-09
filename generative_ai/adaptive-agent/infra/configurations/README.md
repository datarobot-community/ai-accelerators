# Infrastructure Configurations

This folder is for alternative configurations for a given infrastructure component. This enables template customizers to look at the options for a given component and choose one either by directly
symlinking their chosen option, or doing it a runtime via environment variables.

To control them at runtime you can use specialized environment variables to symlink a given configration option in as the name module. Using a concrete example, say you have a folder here called `llm`, and inside that configuration folder you have two configuration options called `llm_gateway.py` and `external_llm.py`. You can symlink one of these into the `infra/infra` folder as
`llm.py` to select that module. To control them during runtime and swap them out, you can also
do it via environment variable. To do so, that would be `INFRA_ENABLE_<FOLDER>=<filename>`. If that variable is set, the existing choice will get overridden. Taking our previous example, if `llm_gateway.py` is current set as `infra/infra/llm.py` and you have `INFRA_ENABLE_LLM=external_llm.py` set when you run `pulumi up` or `task deploy`, it will swap out the `llm.py` with `external_llm.py`.