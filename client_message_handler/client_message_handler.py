import json
import boto3
import os

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('CHAT_DB'))


def lambda_handler(event, context):
    message_body = json.loads(event['body'])
    customer_message = message_body.get('message', None)
    chat_id = message_body.get('chat_id', None)
    buddy_id = message_body.get('buddy_id', None)

    # this is to update connection ID on reconnect
    if not customer_message:
        table.update_item(
            Key={
                'client_id': str(chat_id),
                'buddy_id': str(buddy_id)
            },
            UpdateExpression="SET client_connection_id = :conn_id",
            ExpressionAttributeValues={
                ':conn_id': event['requestContext']['connectionId']
            },
            ReturnValues="NONE"
        )

    else:
        user_message = {'role': 'user', 'content': customer_message}
        table.update_item(
            Key={
                'client_id': str(chat_id),
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
