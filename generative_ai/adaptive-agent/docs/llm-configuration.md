# LLM configuration

This template supports multiple LLM options, including:

- LLM Gateway (default)
- Already Deployed Text Generation model in DataRobot
- LLM Blueprint with an External LLM provider

## LLM configuration recommended option

You can edit the LLM configuration by manually changing which configuration is active.
Simply run:

```sh
ln -sf ../configurations/<chosen_configuration> infra/infra/llm.py
```

After doing so, you'll likely want to edit the `llm.py` file to select the correct model, particularly for non-LLM Gateway options.

## LLM configuration alternative option

If you want to configure it dynamically, you can set it as a configuration value in your `.env` file:

```sh
INFRA_ENABLE_LLM=<chosen_configuration>
```

Choose from the available options in the `infra/configurations/llm` folder.

Here are some examples of each configuration using the dynamic option described above:

### LLM Gateway (default)

The default option is **LLM Gateway**, if not specified in your `.env` file.

```sh
INFRA_ENABLE_LLM=gateway_direct.py
```

### Existing LLM deployment in DataRobot

Uncomment and configure these in your `.env` file:

```sh
TEXTGEN_DEPLOYMENT_ID=<your_deployment_id>
INFRA_ENABLE_LLM=deployed_llm.py
```

### External LLM provider

Configure an LLM with an external LLM provider like Azure, Bedrock, Anthropic, or VertexAI. Here's an Azure OpenAI example:

```sh
INFRA_ENABLE_LLM=blueprint_with_external_llm.py
LLM_DEFAULT_MODEL="azure/gpt-5-mini-2025-08-07"
OPENAI_API_VERSION='2024-08-01-preview'
OPENAI_API_BASE='https://<your_custom_endpoint>.openai.azure.com'
OPENAI_API_DEPLOYMENT_ID='<your deployment_id>'
OPENAI_API_KEY='<your_api_key>'
```

See the [DataRobot documentation](https://docs.datarobot.com/en/docs/gen-ai/playground-tools/deploy-llm.html) for details on other providers.

In addition to the `.env` file changes, you can also edit the respective `llm.py` file to make additional changes, such as the default LLM, temperature, top_p, etc., within the chosen configuration.
