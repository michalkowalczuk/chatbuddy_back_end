import json

import boto3
import os

import vertexai.preview
from google.oauth2.service_account import Credentials
from vertexai.generative_models import Content, Part
from vertexai.preview.generative_models import GenerativeModel

import buddies

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('CHAT_DB'))

model_id = "gemini-1.5-pro-preview-0409"
project_id = "chatbuddy-420408"
region = "us-central1"


def lambda_handler(event, context):
    service_acc_creds = json.loads(get_secret('google_service_acc'))
    vertexai.init(project=project_id, location=region,
                  credentials=Credentials.from_service_account_info(service_acc_creds))

    for record in event['Records']:
        if record['eventName'] in ['INSERT', 'MODIFY']:
            client_id = record['dynamodb']['Keys']['client_id']['S']
            buddy_id = record['dynamodb']['Keys']['buddy_id']['S']

            db_response = table.get_item(
                Key={
                    'client_id': str(client_id),
                    'buddy_id': str(buddy_id)
                },
            )

            item = db_response['Item']
            if not item:
                pass

            messages = item.get('messages', [])

            if messages and messages[-1]['role'] == 'user':
                model_response = generate_model_response(messages, str(buddy_id))

                model_message = {"role": "model", "text": model_response}

                table.update_item(
                    Key={
                        'client_id': str(client_id),
                        'buddy_id': str(buddy_id)
                    },
                    UpdateExpression="SET messages = :msg",
                    ExpressionAttributeValues={
                        ':msg': messages + [model_message],
                    },

                    ReturnValues="NONE"
                )


def generate_model_response(history, buddy_id):
    system_instr = [
        buddies.buddies_system_prompts[buddy_id],
        """
            User messages are structured as follows:
            
            <local_date_time>Local date the message was sent to you, formatted as YYYY-mm-dd HH:MM:SS</local_date_time>
            <events>User events and/or additional information about user</event>
            <message>Actual message from the user</message>
            
            You do not respond in that way, respond with text only without any HTML tags.

        """]

    generative_multimodal_model = GenerativeModel(model_id, system_instruction=system_instr)
    google_formatted_history = google_format_message_history(history)
    response = generative_multimodal_model.generate_content(google_formatted_history)

    return response.candidates[0].text


def google_format_message_history(messages):
    history = []
    previous_role = None

    for message in messages:

        if message['role'] == 'model':
            if previous_role == 'model':
                history[-1].parts.append(Part.from_text(message.get('text', '')))
            else:
                history.append(history_content(role='model', text=message.get('text', '')))

        elif message['role'] == 'user':
            user_text = user_message(
                event=message.get('event', ''),
                message=message.get('text', ''),
                local_date_time=message.get('local_dt'))

            if previous_role == 'user':
                history[-1].parts.append(Part.from_text(user_text))
            else:
                history.append(history_content(role='user', text=user_text))

        previous_role = message['role']

    return history


def history_content(role, text):
    return Content(role=role, parts=[Part.from_text(text)])


def user_message(event="", message="", local_date_time=""):
    return f"""
        <local_date_time>{local_date_time}</local_date_time>
        <event>{event}</event>
        <message>{message}</message>
    """


def get_secret(name):
    secret_name = "buddy_keys"
    region_name = os.environ['AWS_REGION']

    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    get_secret_value_response = client.get_secret_value(
        SecretId=secret_name
    )

    secret = get_secret_value_response['SecretString']
    return json.loads(secret).get(name, None)
