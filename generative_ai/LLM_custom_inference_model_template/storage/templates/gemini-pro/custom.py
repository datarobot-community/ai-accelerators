from datarobot_drum import RuntimeParameters
import google.generativeai as genai
import pandas as pd


def load_model(*args, **kwargs):
    genai.configure(
        api_key=RuntimeParameters.get("google_api_key")["apiToken"],
    )
    return genai.GenerativeModel("gemini-pro")


def score(data, model, **kwargs):
    prompts = data["promptText"].tolist()
    responses = []

    # set temp to 0.1 for rag
    generation_config = genai.types.GenerationConfig(temperature=0.1)
    safety_settings = {
        genai.types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: genai.types.HarmBlockThreshold.BLOCK_NONE,
        genai.types.HarmCategory.HARM_CATEGORY_HATE_SPEECH: genai.types.HarmBlockThreshold.BLOCK_NONE,
        genai.types.HarmCategory.HARM_CATEGORY_HARASSMENT: genai.types.HarmBlockThreshold.BLOCK_NONE,
        genai.types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: genai.types.HarmBlockThreshold.BLOCK_NONE,
    }

    for prompt in prompts:
        response = model.generate_content(
            prompt, generation_config=generation_config, safety_settings=safety_settings
        )
        responses.append(response.text)

    return pd.DataFrame({"resultText": responses})
