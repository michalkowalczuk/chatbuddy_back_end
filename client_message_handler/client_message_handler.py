import json
import boto3
import os

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('CHAT_DB'))


def lambda_handler(event, context):
    message_body = json.loads(event['body'])
    client_message = message_body.get('client_message', "")
    client_event = message_body.get('client_event', "")
    client_id = message_body.get('client_id', None)
    buddy_id = message_body.get('buddy_id', None)

    # this is to update connection ID on reconnect
    if not client_message:
        table.update_item(
            Key={
                'client_id': str(client_id),
                'buddy_id': str(buddy_id)
            },
            UpdateExpression="SET client_connection_id = :conn_id",
            ExpressionAttributeValues={
                ':conn_id': event['requestContext']['connectionId']
            },
            ReturnValues="NONE"
        )

    else:
        user_message = {
            'role': 'user',
            'text': client_message,
            'event': client_event
        }

        table.update_item(
            Key={
                'client_id': str(client_id),
                'buddy_id': str(buddy_id)
            },
            UpdateExpression="SET client_connection_id = :conn_id, messages = list_append(if_not_exists(messages, "
                             ":empty_list), :msg)",
            ExpressionAttributeValues={
                ':conn_id': event['requestContext']['connectionId'],
                ':msg': [user_message],
                ':empty_list': []
            },
            ReturnValues="NONE"
        )

    return {'statusCode': 204}
