# xAI Grok Model Wrapper 

This code folder provides a wrapper for Grok models developed by xAI. This bolt-on wrapper allows grok to be monitored and guarded by DataRobot's AI suite. 

For DataRobot 10.2, this wrapper is fully compliant with the OpenAI client Specification. So just simply swap your endpoint and you gain access to all of DataRobot's monitoring, evaluations and guardrails. 

## Testing Locally

You can test this wrapper locally using drum. 

First install the requirements file in new virtual environment:

```
python -m pip venv venv
source venv/bin/activate
pip install -r requirements.txt
```


Now you can run drum server

```
export TARGET_NAME=resultText
export xai_grok_api_key=<YOUR GrokAI KEY>
drum server -cd . --target-type textgeneration --address localhost:6789
```

You can test the wrapper by running the test script

```
./test_server.sh
```
