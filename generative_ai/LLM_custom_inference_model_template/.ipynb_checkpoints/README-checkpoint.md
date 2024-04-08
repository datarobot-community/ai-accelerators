# Use an LLM custom inference model template

There are a wide variety of LLM model such as OpenAI (not Azure), Gemini Pro, Cohere and Claude. Managing and monitoring these LLM models is crucial to effectively using them. Data drift monitoring by DataRobot MLOps enables you to detect the changes in a user prompt and its responses. Sidecar models can prevent a jailbreak, replace Personally Identifiable Information (PII), and evaluate LLM responses with a global model in the Registry. Data export functionality shows you of what a user desired to know at each moment and provides the necessary data you should be included in RAG system. Custom metrics indicate your own KPIs which you inform your decisions (e.g., token costs, toxicity, and hallucination).

In addition, DataRobot's LLM Playground enables you to compare the RAG system of LLM models that you want to try once you deploy the models in MLOps. You can obtain the best LLM model to accelerate your business. The comparison of variety of LLM models is key element to success the RAG system.

The LLM custom inference model template enables you to deploy and accelerate your own LLM, along with "batteries-included" LLMs like Azure OpenAI, Google, and AWS.

Currently, DataRobot has a template for OpenAI (not Azure), Gemini Pro, Cohere, and Claude. To use this template follow the instructions outline below. 

# How to use the template

1. Open the model workshop in the Registry. Click **+ Add Model** to add the new custom model.

![Model workshop + add model](./storage/_images/img1.png "+ add model")

2. Select **Text Generation** for the target type and provide **resultText** as the target. Provide a name for the model.

![enter configure](./storage/_images/img2.png "enter configure")

3. Select a base environment (`[DataRobot] Python 3.11 GenAI`) to use the template. If you modify the environment, you can choose any appropriate environment and then upload the model file from template. Note that the LLM custom inference model templates are in storage.

![upload template](./storage/_images/img3.png "upload template")

4. Build the model and then provide the runtime parameters.

5. Test and deploy the model.

# LLM custom inference model template details

The LLM custom inference model templates are in `/storage/templates` and there are `custom.py`, `model-metadata.yaml` and `requirements.txt`.

| File name            |  Description           |
|----------------------|------------------------|
| custom.py            | Calls the LLM model via the API. |
| model-metadata.yaml  | The model information and runtime parameter configuration. |
| requirements.txt     | The required library to call the LLM API. |

## List of templates

- gemini-pro
- openai-gpt-3.5
- openai-gpt-4
- cohere 
- claude-3-opus
- claude-3-sonnet
- claude-3-haiku
- mistralai/Mixtral-8x7B-Instruct-v0.1(together.ai)
- meta-llama/Llama-2-13b-chat-hf(together.ai)
- NousResearch/Nous-Capybara-7B-V1p9(together.ai)
- deepseek-ai/deepseek-coder-33b-instruct(together.ai)
- google/gemma-7b-it(Cloudflare Workers AI)

## How to obtain an API key

### gemini-pro

[Google AI for Developers](https://ai.google.dev/tutorials/setup).

Refer to the `Get an API key` section to create a key.

### OpenAI

- openai-gpt-3.5
- openai-gpt-4

[OpenAI website](https://openai.com/). You can find your OpenAI Secret API key on the [API key page](https://platform.openai.com/api-keys).

### cohere

- cohere command-r
- cohere command-r-plus

[Cohere AI website](https://docs.cohere.com/).

### claude

- claude-3-opus
- claude-3-sonnet
- claude-3-haiku

[ANTHROPIC website](https://www.anthropic.com/). You can find the docs for [getting started with the api](https://docs.anthropic.com/claude/reference/getting-started-with-the-api).

### together.ai

- mistralai/Mixtral-8x7B-Instruct-v0.1
- meta-llama/Llama-2-13b-chat-hf
- NousResearch/Nous-Capybara-7B-V1p9
- deepseek-ai/deepseek-coder-33b-instruct

[together.ai website](https://www.together.ai/). You can find `sign in` page. You can change the model as listed in the [Inference Models](https://docs.together.ai/docs/inference-models) section.

### Cloudflare Workers AI

- google/gemma-7b-it

[Workers AI website](https://dash.cloudflare.com/). You can find the docs and how to obtain credentials on its [developer site](https://developers.cloudflare.com/workers-ai/). <br>

You can change the model as listed on the [Models](https://developers.cloudflare.com/workers-ai/models/) page.

## Model testing

An example for custom LLM model is `storage/custom_model_prompts_example.csv`, You can upload and test the custom model.
