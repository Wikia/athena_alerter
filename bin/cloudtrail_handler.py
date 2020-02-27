"""
This file contains a lambda function reacting to cloudtrail events that a new athena query has been started.
It adds new entries to a dynamodb table containing all queries
"""

import gzip
import json
import logging
from datetime import datetime, timezone
from io import BytesIO

import boto3

import settings
from model import AthenaQuery, QueryState, TIMESTAMP_FORMAT
from query_dao import QueryDao

CLOUDTRAIL_TIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ'

logger = logging.getLogger()


def lambda_handler(event, context):
    s3 = boto3.resource('s3')
    dynamodb = boto3.resource('dynamodb')

    query_dao = QueryDao(settings, dynamodb)

    writer = CloudtrailHandler(settings, s3, query_dao)

    writer.process_log(event)


class CloudtrailHandler:

    def __init__(self, config, s3, query_dao):
        self.config = config
        self.s3 = s3
        self.query_dao = query_dao

    def process_log(self, event):
        s3_record = event['Records'][0]['s3']
        bucket = s3_record['bucket']['name']
        key = s3_record['object']['key']
        object = self.s3.Object(bucket, key).get()
        stream = BytesIO(object['Body'].read())
        with gzip.GzipFile(None, 'rb', fileobj=stream) as file:
            try:
                data = json.load(file)
            except json.JSONDecodeError:
                logger.warning(f'Not a valid cloudtrail json file {bucket}/{key}', exc_info=True)
                return
            for record in data.get('Records', []):
                if record.get('eventName') == 'StartQueryExecution':
                    self.process_query_record(record)

    def process_query_record(self, record):
        if record.get('responseElements') and record.get('userIdentity'):
            time = datetime.strptime(record['eventTime'], CLOUDTRAIL_TIME_FORMAT).replace(
                tzinfo=timezone.utc)
            query = AthenaQuery(
                start_date=datetime.strftime(time, '%Y-%m-%d'),
                start_timestamp=datetime.strftime(time, TIMESTAMP_FORMAT),
                query_execution_id=record['responseElements']['queryExecutionId'],
                query_state=QueryState.RUNNING.value,
                executing_user=record['userIdentity']['userName'],
                data_scanned=0,
                query_sql=None)

            self.query_dao.insert_query(query)
