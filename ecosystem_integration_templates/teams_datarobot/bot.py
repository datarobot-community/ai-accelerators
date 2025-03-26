# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

from datetime import datetime
import json

from botbuilder.core import (
    ActivityHandler,
    CardFactory,
    ConversationState,
    MemoryStorage,
    MessageFactory,
    TurnContext,
)
from botbuilder.core.teams import TeamsActivityHandler
from botbuilder.schema import Activity, ActivityTypes, Attachment, ChannelAccount
from config import DefaultConfig
import datarobotx as drx
from utilities import generate_links

adaptive_card_json = json.load(open("./card_template.json"))

CONFIG = DefaultConfig()
# DataRobot Connect
drx.Context(token=CONFIG.DATAROBOT_TOKEN, endpoint=CONFIG.DATAROBOT_ENDPOINT)
deployment_id = CONFIG.DATAROBOT_DEPLOYMENT
deployment = drx.Deployment(deployment_id)

# store chat history
memstore = MemoryStorage()
convstate = ConversationState(memstore)


class ConversationData:
    def __init__(self, chat_history=[]):
        self.chat_history = chat_history


class MyBot(TeamsActivityHandler):
    # See https://aka.ms/about-bot-activity-message to learn more about the message and other activity types.
    def __init__(self, app_id: str, app_password: str):
        self._app_id = app_id
        self._app_password = app_password
        self.convstate_accessor = convstate.create_property("convdata")

    async def on_message_activity(self, turn_context: TurnContext):
        time_start = datetime.now()
        convdata = await self.convstate_accessor.get(turn_context, ConversationData)
        chat_history = convdata.chat_history
        TurnContext.remove_recipient_mention(turn_context.activity)
        answer = deployment.predict_unstructured(
            {"question": turn_context.activity.text, "chat_history": chat_history}
        )
        print("deployment response")
        print(answer)
        answer_formatted = answer["answer"]
        references = generate_links(answer["references"])
        print(json.dumps(answer))
        chat_history.append((turn_context.activity.text, answer_formatted))
        time_end = datetime.now()
        link_block = []
        if len(references) > 0:
            link_block.append({"type": "TextBlock", "size": "medium", "text": "References:"})
            fs = {"type": "FactSet", "facts": []}
            for link in references:
                # [Adaptive cards!](https://adaptivecards.io)
                fs["facts"].append({"value": "[" + link + "](" + link + ")"})
            link_block.append(fs)
        adaptive_card_json["body"] = link_block
        message = Activity(
            text=answer_formatted,
            type=ActivityTypes.message,
            attachments=[CardFactory.adaptive_card(adaptive_card_json)],
        )
        await turn_context.send_activity(message)

    async def on_members_added_activity(
        self, members_added: ChannelAccount, turn_context: TurnContext
    ):
        for member_added in members_added:
            if member_added.id != turn_context.activity.recipient.id:
                await turn_context.send_activity(
                    "Hello!. I am DataRobot's Generative AI Bot, how can I help you?"
                )
