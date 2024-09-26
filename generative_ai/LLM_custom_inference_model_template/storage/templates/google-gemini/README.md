# Google Gemini Model Wrapper 

This code folder provides a wrapper for any OpenAI model so that your prompts and responses are monitored and governend by DataRobot. 

For DataRobot 10.2, this wrapper is fully compliant with the OpenAI client Specification. So just simply swap your endpoint and you gain access to all of DataRobot's monitoring, evaluations and guardrails. You can use any Anthropic model by changin the model parameter on the chat input. Gemini models support 
for the OpenAI Spec is now in preview. https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/call-vertex-using-openai-library

## Testing Locally

You can test this wrapper locally using drum. 

First install the requirements file in new virtual environment:

```
python -m pip venv venv
source venv/bin/activate
pip install -r requirements.txt
```

You should follow the direction to locally authenticate to google apis using application default credentials
https://cloud.google.com/docs/authentication/application-default-credentials

On DataRobot, the api will authenticate using a DataRobot credential and Google Cloud Service account. 

Now you can run drum server. 

```
export TARGET_NAME=resultText

drum server -cd . --target-type textgeneration --address localhost:6789
```

You can test the wrapper by running the test script

```
curl http://localhost:6789/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "google/gemini-1.5-flash-001",
    "messages": [
      {
        "role": "system",
        "content": "You are a helpful assistant."
      },
      {
        "role": "user",
        "content": "Hello!"
      }
    ]
  }'

```


