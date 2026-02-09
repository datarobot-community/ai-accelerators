# Feature Flag validation

Put yaml files here with feature flags that are required. 

`__main__.py` will automatically discover and validate them to ensure the required flags
for the DataRobot endpoint are enabled.


## Example

In `infra/feature_flags/` create: `llm_features.yaml`

That file could look something like:

```yaml
---
ENABLE_MLOPS: true
ENABLE_PUBLIC_NETWORK_ACCESS_FOR_ALL_CUSTOM_MODELS: true
ENABLE_MLOPS_TEXT_GENERATION_TARGET_TYPE: true
ENABLE_LLM_GATEWAY: true
```
