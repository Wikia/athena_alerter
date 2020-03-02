"""
This file contains a lambda function which cyclically checks for recent athena queries and updates their data usage.
It sends sqs events when a query is finished.

"""

import dataclasses
import json
from datetime import datetime, timedelta

import boto3

from . import settings
from .model import QueryState
from .query_dao import QueryDao


def lambda_handler(event, context):
    athena = boto3.client('athena')
    sqs = boto3.client('sqs')
    dynamodb = boto3.resource('dynamodb')
    query_dao = QueryDao(settings, dynamodb)

    updater = UsageUpdater(settings, query_dao, athena, sqs)
    updater.update_query_usage()


class UsageUpdater:

    def __init__(self, config, query_dao, athena, sqs):
        self.config = config
        self.athena = athena
        self.sqs = sqs
        self.query_dao = query_dao

    def update_query_usage(self):
        queries = self.get_queries()
        queries = [query for query in queries if query.query_state == QueryState.RUNNING.value]
        for query in queries:
            details = self.get_query_details(query_execution_id=query.query_execution_id)
            if details.get('query_state') not in [QueryState.QUEUED.value, QueryState.RUNNING.value]:
                query.query_state = details['query_state']
                query.data_scanned = details['data_scanned']
                query.query_sql = details['query']
                if hasattr(self.config, 'USER_MAPPING_FUNCTION'):
                    mapped_user = self.config.USER_MAPPING_FUNCTION(details['query'])
                    if mapped_user:
                        query.executing_user = mapped_user
                self.query_dao.update_query(query)
                self.send_event_query_updated(query)

    # For easier mocking
    def now(self):
        return datetime.now()

    def get_queries(self):
        current_timestamp = self.now()
        since_timestamp = current_timestamp - timedelta(hours=1)
        items = self.query_dao.get_running_queries(current_timestamp.date(), since_timestamp)
        # we keep data in daily partitions so we may need to query a range of two partitions
        if current_timestamp.day != since_timestamp.day:
            items.extend(self.query_dao.get_running_queries(since_timestamp.date(), since_timestamp))
        return items

    def get_query_details(self, query_execution_id):
        response = self.athena.get_query_execution(QueryExecutionId=query_execution_id)
        execution = response['QueryExecution']
        return dict(
            query_state=execution['Status']['State'],
            data_scanned=execution.get('Statistics', {}).get('DataScannedInBytes', 0),
            query=execution['Query']
        )

    def send_event_query_updated(self, query):
        self.sqs.send_message(
            QueueUrl=self.config.SQS_QUEUE_URL,
            MessageBody=json.dumps(dataclasses.asdict(query)))
