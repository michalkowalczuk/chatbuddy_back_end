import json
import boto3
import os

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('CHAT_DB'))


def lambda_handler(event, context):
    message_body = json.loads(event['body'])
    client_id = message_body.get('client_id', None)
    buddy_id = message_body.get('buddy_id', None)

    response = table.get_item(
        Key={
            'client_id': str(client_id),
            'buddy_id': str(buddy_id)
        },
    )

    if 'Item' in response:
        item = response['Item']
        return {
            'statusCode': 200,
            'body': json.dumps(item)
        }

    else:
        return {
            'statusCode': 404,
            'body': json.dumps({'message': 'Item not found'})
        }
