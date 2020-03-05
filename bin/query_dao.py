from dataclasses import asdict
from datetime import datetime

from boto3.dynamodb.conditions import Key, Attr

from .model import AthenaQuery, TIMESTAMP_FORMAT


class QueryDao:

    def __init__(self, config, dynamodb):
        self.config = config
        self.dynamodb = dynamodb

    def insert_query(self, query):
        # DynamoDB does not support empty strings, so we need to drop such attributes
        query_dict = {key: value for key, value in asdict(query).items() if value is not None}
        self.dynamodb.Table(self.config.QUERIES_TABLE).put_item(Item=query_dict)

    def get_running_queries(self, partition_timestamp, start_timestamp):
        date_str = datetime.strftime(partition_timestamp, '%Y-%m-%d')
        timestamp_str = datetime.strftime(start_timestamp, TIMESTAMP_FORMAT)
        response = self.dynamodb.Table(self.config.QUERIES_TABLE).query(
            KeyConditionExpression=Key('start_date').eq(date_str) & Key('start_timestamp').gte(timestamp_str),
            FilterExpression=Attr('query_state').eq('RUNNING'),
        )
        return [AthenaQuery(**item) for item in response.get('Items', [])]

    def update_query(self, query):
        self.dynamodb.Table(self.config.QUERIES_TABLE).update_item(
            Key={
                'start_date': query.start_date,
                'start_timestamp': query.start_timestamp},
            UpdateExpression="set query_state = :query_state, data_scanned = :data_scanned, "
                             "executing_user = :executing_user, query_sql = :query_sql",
            ExpressionAttributeValues={
                ':query_state': query.query_state,
                ':executing_user': query.executing_user,
                ':data_scanned': query.data_scanned,
                ':query_sql': query.query_sql
            }
        )
