# Use DataRobot generative AI with Microsoft Teams

Microsoft Teams offers workspace chat and video conferencing, file storage, and application integration to organizations. Workspace chat feature aloow you to interact with other users and bots in their day-to-day activities. This feature is useful for deploying Generative AI agents to improve employee productivity. With DataRobot's Generative AI offerings, organizations can deploy chatbots without the need for an additional front-end or consumption layers. 

## How it works

Most messenger/communication apps support [bots](https://learn.microsoft.com/en-us/microsoftteams/platform/bots/what-are-bots). A bot is a program that interacts with the users of the messenger application by ingesting the user message and providing responses. Bot can be static or dynamic depending on the logic encoded. A bot in most cases is a service exposing Rest Endpoints which recieve user text and respond back with text. Instead of developers starting from scratch, Microsoft provides an [SDK](https://learn.microsoft.com/en-us/azure/bot-service/index-bf-sdk?view=azure-bot-service-4.0) which can be used as building blocks or boilerplate. This SDK supports different languages including [python](https://github.com/microsoft/botbuilder-python). The code demonstrated here uses this [code](https://github.com/microsoft/BotBuilder-Samples/tree/main/samples/python/02.echo-bot) as boilerplate.

Note: Python support is deprecated. A Typescript version of the code will be released.

## Prerequisites

1. **Developer Account:** Developers need access to the [Teams Developer Portal](https://dev.teams.microsoft.com/). This portal allows developers to register and configure apps and bots that will be visible in their organization's Teams Portal.

2. **Hosting:** As mentioned before, the bot is an always on service which needs to be hosted somewhere. Microsoft provides different options like Power Virtual Agents and Azure AI Bot Service. Organizations can also host their bots if the bot architecture is complex.

3. **HTTPS:** The bot's REST endpoints should be HTTPS secure. To enable data encryption Teams requires https endpoints and this doesn't include self-signed certificates.  

## Bot backend

1. Install the required libraries using ``` pip install -r requirements.txt ```.
2. Ensure your DataRobot LLM deployment is working and [deployed](https://app.datarobot.com/deployments/list). Use ```create_llm_deployment.ipynb``` for reference.
3. Update the appropriate identifiers in the configuration file ```config.py``` . 
    - PORT: Port to run the bot service on.
    - SERVER: Server IP. Accepts localhost.
    - APP_ID: Bot Identifier from ``` https://dev.teams.microsoft.com/bots/<<IDENTIFIER>>/configure ```.
    - APP_PASSWORD: Client Secret from Bot Configure page. Point 4 in Bot Publish section below.
    - DATAROBOT_TOKEN: DataRobot API token.
    - DATAROBOT_ENDPOINT: DataRobot endpoint.
    - DATAROBOT_DEPLOYMENT: DataRobot LLM deployment identifier.
4. Activate the bot backend by running ``` python app.py  ```.
5. If your bot service is not HTTPS, you can use port forwarding services like [ngrok](https://ngrok.com/). If you are using Azure VMs, please find the associated documentation to secure the VM using HTTPS [here](https://learn.microsoft.com/en-us/azure/virtual-machines/windows/tutorial-secure-web-server).
6. The bot service is now online. 

## Bot testing

Developers can use the [Bot Emulator Framework](https://github.com/microsoft/BotFramework-Emulator) for testing the bot locally. The emulator offers quality of life features like restarting or replaying conversations with the bot. 

## Bot publishing

1. Log into [Teams Developer Portal](https://dev.teams.microsoft.com/) and navigate to the **Apps** tab.
2. Click the **Tools** tab in the sidebar and then click **Bot management**.
3. Click **New Bot**. In the **Configure** section, add the secure endpoint("/api/messages") in **Endpoint Address**. This is the URL from step 4 in the "Bot backend" section above. 
4. In the Client secrets section, create a new secret. Note the secret key for the next steps.
5. Click **New App** and fill in the basic information fields.
6. In the **Configure** Tab, click **App features > Bot**. Select your bot from step 3 from the drodown.
7. Publish your bot by clicking **Submit app update**. Upon approval from your Teams organization admin, which is handled by your IT support team, your bot will be available in the Teams homepage.
