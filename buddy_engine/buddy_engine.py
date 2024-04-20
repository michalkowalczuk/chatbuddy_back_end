import json
import os

import boto3
import vertexai.preview
from google.oauth2.service_account import Credentials
from vertexai.generative_models import Content, Part, FunctionDeclaration, Tool
from vertexai.preview import generative_models
from vertexai.preview.generative_models import GenerativeModel

import buddies

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('CHAT_DB'))

MODEL_ID = "gemini-1.5-pro-preview-0409"
PROJECT_ID = "chatbuddy-420408"
REGION = "us-central1"


def lambda_handler(event, context):
    service_acc_creds = json.loads(get_secret('google_service_acc'))
    vertexai.init(
        project=PROJECT_ID,
        location=REGION,
        credentials=Credentials.from_service_account_info(service_acc_creds)
    )

    for record in event['Records']:
        if record['eventName'] in ['INSERT', 'MODIFY']:
            client_id = record['dynamodb']['Keys']['client_id']['S']
            buddy_id = record['dynamodb']['Keys']['buddy_id']['S']

            item = get_chat_item(client_id, buddy_id)
            if not item:
                continue

            messages = item.get('messages', [])
            if messages and messages[-1]['role'] == 'user':
                model_response = generate_model_response(messages, buddy_id, client_id)
                if model_response:
                    update_chat_item(client_id, buddy_id, messages + [{"role": "model", "text": model_response}])


def get_chat_item(client_id, buddy_id):
    response = table.get_item(Key={'client_id': client_id, 'buddy_id': buddy_id})
    return response.get('Item')


def update_chat_item(client_id, buddy_id, messages):
    table.update_item(
        Key={'client_id': client_id, 'buddy_id': buddy_id},
        UpdateExpression="SET messages = :msg",
        ExpressionAttributeValues={':msg': messages},
        ReturnValues="NONE"
    )


def generate_model_response(history, buddy_id, client_id):
    system_instr = [
        buddies.buddies_system_prompts[buddy_id],
        """
            User messages are structured as follows:

            <local_date_time>Local date the message was sent to you, formatted as YYYY-mm-dd HH:MM:SS</local_date_time>
            <events>User events and/or additional information about user</event>
            <message>Actual message from the user</message>

            You do not respond in that way, respond with text only without any HTML tags.
        """
    ]

    model = GenerativeModel(MODEL_ID, system_instruction=system_instr)

    delete_chat_function_declaration = FunctionDeclaration(
        name="delete_chat",
        description="Deletes any previous conversations with you from the database on users request, you need "
                    "to confirm with user if he want to delete the conversations",
        parameters={"type": "object", "properties": {
            "confirmation": {"type": "string", "description": "Describe the way user confirm chat deletion"}}, }
    )

    response = model.generate_content(format_message_history(history),
                                      tools=[Tool(function_declarations=[delete_chat_function_declaration])],
                                      safety_settings={
                                          generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT: generative_models.HarmBlockThreshold.BLOCK_ONLY_HIGH,
                                          generative_models.HarmCategory.HARM_CATEGORY_UNSPECIFIED: generative_models.HarmBlockThreshold.BLOCK_ONLY_HIGH,
                                          generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: generative_models.HarmBlockThreshold.BLOCK_ONLY_HIGH,
                                          generative_models.HarmCategory.HARM_CATEGORY_HATE_SPEECH: generative_models.HarmBlockThreshold.BLOCK_ONLY_HIGH,
                                      })

    if response.candidates[0].function_calls:
        delete_chat(client_id, buddy_id)
        return None
    else:
        return response.candidates[0].text


def format_message_history(messages):
    history = []
    prev_role = None

    for msg in messages:
        role, text = msg['role'], msg.get('text', '')

        if role == 'model':
            history[-1].parts.append(Part.from_text(text)) if prev_role == 'model' else history.append(
                Content(role=role, parts=[Part.from_text(text)]))
        elif role == 'user':
            user_text = format_user_message(msg.get('event', ''), text, msg.get('local_dt'))
            history[-1].parts.append(Part.from_text(user_text)) if prev_role == 'user' else history.append(
                Content(role=role, parts=[Part.from_text(user_text)]))

        prev_role = role

    return history


def format_user_message(event="", message="", local_date_time=""):
    return f"""
        <local_date_time>{local_date_time}</local_date_time>
        <event>{event}</event>
        <message>{message}</message>
    """


def delete_chat(client_id, buddy_id):
    item = get_chat_item(client_id, buddy_id)
    if not item:
        pass
    table.update_item(
        Key={'client_id': client_id, 'buddy_id': buddy_id},
        UpdateExpression='SET messages = :empty_list',
        ExpressionAttributeValues={':empty_list': []}
    )


def get_secret(name):
    secret_name = "buddy_keys"
    region_name = os.environ['AWS_REGION']

    get_secret_value_response = boto3.session.Session() \
        .client(
        service_name='secretsmanager',
        region_name=region_name
    ) \
        .get_secret_value(
        SecretId=secret_name
    )

    return json.loads(get_secret_value_response['SecretString']).get(name, None)
