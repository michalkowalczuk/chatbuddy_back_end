import boto3
import os

import vertexai.preview
from google.oauth2.service_account import Credentials
from vertexai.generative_models import Content, Part

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('CHAT_DB'))

model_id = "gemini-1.5-pro-preview-0409"
project_id = "chatbuddy-420408"
region = "us-central1"

vertexai.init(project=project_id, location=region,
              credentials=Credentials.from_service_account_file('google_sa.json'))


def lambda_handler(event, context):
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
            print(google_format_message_history(messages))
            if messages and messages[-1]['role'] == 'user':
                dummy_message = {"role": "model", "text": "this is nonsense from assistant"}
                table.update_item(
                    Key={
                        'client_id': str(client_id),
                        'buddy_id': str(buddy_id)
                    },
                    UpdateExpression="SET messages = :msg",
                    ExpressionAttributeValues={
                        ':msg': messages + [dummy_message],
                    },

                    ReturnValues="NONE"
                )


def google_format_message_history(messages):
    history = []
    for message in messages:

        if message['role'] == 'model':
            history.append(history_content(role='model', text=message.get('text', '')))

        elif message['role'] == 'user':
            user_text = user_message(
                event=message.get('event', ''),
                message=message.get('message', ''))
            history.append(history_content(role='user', text=user_text))

    return history


def history_content(role, text):
    return Content(role=role, parts=[Part.from_text(text)])


def user_message(event="", message=""):
    return f"""
        <event>{event}</event>
        <message>{message}</message>
    """
