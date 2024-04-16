import json
import boto3
import os

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('CHAT_DB'))


def lambda_handler(event, context):
    message_body = json.loads(event['body'])

    update_connection = message_body.get('update_connection', None)
    client_id = message_body.get('client_id', None)
    buddy_id = message_body.get('buddy_id', None)

    client_message = message_body.get('client_message', "")
    client_event = message_body.get('client_event', "")
    client_dt = message_body.get('client_date_time', "")

    # this is to update connection ID on reconnect
    if client_id and update_connection:

        response = table.query(
            KeyConditionExpression='client_id = :client_id',
            ExpressionAttributeValues={':client_id': str(client_id)}
        )

        items = response['Items']

        for item in items:
            table.update_item(
                Key={
                    'client_id': item['client_id'],
                    'buddy_id': item['buddy_id']
                },
                UpdateExpression='SET client_connection_id = :conn_id',
                ExpressionAttributeValues={
                    ':conn_id': event['requestContext']['connectionId']
                },
                ReturnValues="NONE"
            )

    elif client_id and buddy_id:
        user_message = {
            'role': 'user',
            'text': client_message,
            'event': client_event,
            'local_dt': client_dt
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
