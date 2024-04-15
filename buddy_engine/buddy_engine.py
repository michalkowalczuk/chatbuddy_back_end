import boto3
import os

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('CHAT_DB'))


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
