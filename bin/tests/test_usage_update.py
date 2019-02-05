import unittest
from datetime import datetime, date
from unittest.mock import Mock, patch
from boto3.dynamodb.conditions import Key, Attr

from usage_update import UsageUpdater
from tests import utils
from model import AthenaQuery


def mocked_get_now():
    return datetime(2019, 1, 1, 0, 10, 10)

class UsageUpdaterTest(unittest.TestCase):
    
    @patch('usage_update.UsageUpdater.now', side_effect=mocked_get_now)
    def test_update_query_usage(self, mock_obj):
        query_execution_id = '6acb55b1-fddd-4608-bef8-ed206e1262de'

        config = Mock()
        config.QUERIES_TABLE = 'test_table'
        config.SQS_QUEUE_URL = 'url'
        config.USER_MAPPING_FUNCTION = lambda user: None

        query_dao = Mock()
        query_dao.get_running_queries.return_value = [AthenaQuery(
            start_date='2019-01-17',
            start_timestamp='2019-01-17 11:57:30',
            query_execution_id='6acb55b1-fddd-4608-bef8-ed206e1262de',
            query_state='RUNNING',
            executing_user='testUser',
            data_scanned=0,
            query_sql='')]

        athena = Mock()
        athena.get_query_execution.return_value=utils.get_json_content('fixtures/usage_update_athena_queries.json')

        sqs = Mock()

        sut = UsageUpdater(config, query_dao, athena, sqs)
        sut.update_query_usage()

        athena.get_query_execution.assert_called_with(QueryExecutionId=query_execution_id)

        query_dao.get_running_queries.assert_any_call(
            date(2019, 1, 1), datetime(2018, 12, 31, 23, 10, 10))
        query_dao.get_running_queries.assert_any_call(
            date(2018, 12, 31), datetime(2018, 12, 31, 23, 10, 10))
        query_dao.update_query.assert_called_with(AthenaQuery(
            start_date='2019-01-17',
            start_timestamp='2019-01-17 11:57:30',
            query_execution_id='6acb55b1-fddd-4608-bef8-ed206e1262de',
            query_state='SUCCEEDED',
            executing_user='testUser',
            data_scanned=29944425990,
            query_sql='select * from foo.bar'))

        sqs.send_message.assert_called_with(QueueUrl='url', MessageBody=
            '{"start_date": "2019-01-17", "start_timestamp": "2019-01-17 11:57:30", '
            '"query_execution_id": "6acb55b1-fddd-4608-bef8-ed206e1262de", "query_state": "SUCCEEDED", '
            '"executing_user": "testUser", "data_scanned": 29944425990, "query_sql": "select * from foo.bar"}')

if __name__ == '__main__':
    unittest.main()
