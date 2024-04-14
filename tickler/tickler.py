import json
import boto3
import os

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('CHAT_DB'))
client = boto3.client('apigatewaymanagementapi',
                      endpoint_url=os.environ.get('WSS_MANAGEMENT_ENDPOINT'))


def lambda_handler(event, context):
    for record in event['Records']:
        if record['eventName'] == 'MODIFY':
            new_image = record['dynamodb'].get('NewImage', None)
            old_image = record['dynamodb'].get('OldImage', None)
            if new_image and old_image and new_image.get('messages', []) != old_image.get('messages', []):
                client_id = new_image['client_id']['S']
                buddy_id = new_image['buddy_id']['S']

                db_response = table.get_item(Key={'chat_id': client_id, 'buddy_id': buddy_id})

                item = db_response['Item']
                connection_id = item.get('client_connection_id')

                do_tickle(connection_id, client_id, buddy_id)


def do_tickle(connection_id, client_id, buddy_id):
    payload = {
        'action': 'tickle',
        'client_id': client_id,
        'buddy_id': buddy_id
    }

    try:
        client.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps(payload)
        )

    except client.exceptions.GoneException:
        print(f"Connection {connection_id} is no longer available.")

    except Exception as e:
        print(f"Error sending message: {str(e)}")
