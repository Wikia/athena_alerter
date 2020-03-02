import unittest
from datetime import datetime, date
from unittest.mock import Mock

from . import utils
from bin.query_dao import QueryDao
from bin.model import AthenaQuery


class QueryDaoTest(unittest.TestCase):
    def test_update_query(self):
        config = Mock()
        config.QUERIES_TABLE = 'test_table'

        dynamodb = Mock()

        sut = QueryDao(config, dynamodb)
        sut.update_query(AthenaQuery(start_date='2019-01-21',
                                     start_timestamp='2019-01-21 09:34:13',
                                     query_execution_id = '1',
                                     query_state = 'SUCCEEDED',
                                     executing_user = 'test',
                                     data_scanned = 29944425990,
                                     query_sql = 'select * from foo.bar'))

        dynamodb.Table.return_value.update_item.assert_called_with(
            Key={
                'start_date': '2019-01-21',
                'start_timestamp': '2019-01-21 09:34:13'},
            UpdateExpression="set query_state = :query_state, data_scanned = :data_scanned, "
                             "executing_user = :executing_user, query_sql = :query_sql",
            ExpressionAttributeValues={
                ':query_state': 'SUCCEEDED',
                ':executing_user': 'test',
                ':data_scanned': 29944425990,
                ':query_sql': 'select * from foo.bar'
            }
        )

    def test_insert_query(self):
        config = Mock()
        config.QUERIES_TABLE = 'test_table'

        dynamodb = Mock()

        sut = QueryDao(config, dynamodb)
        sut.insert_query(AthenaQuery(start_date='2019-01-21',
                                     start_timestamp='2019-01-21 09:34:13',
                                     query_execution_id = '1',
                                     query_state = 'SUCCEEDED',
                                     executing_user = 'test',
                                     data_scanned = 29944425990,
                                     query_sql = None))

        dynamodb.Table.assert_called_with('test_table')
        dynamodb.Table.return_value.put_item.assert_called_with(Item=dict(
            start_date='2019-01-21',
            start_timestamp='2019-01-21 09:34:13',
            query_execution_id='1',
            query_state='SUCCEEDED',
            executing_user='test',
            data_scanned=29944425990
        ))

    def test_get_running_queries(self):
        config = Mock()
        config.QUERIES_TABLE = 'test_table'

        dynamodb = Mock()
        dynamodb.Table.return_value.query.return_value = utils.get_json_content(
            'fixtures/query_dao_dynamodb_queries.json')

        sut = QueryDao(config, dynamodb)
        queries = sut.get_running_queries(partition_timestamp=date(2019, 1, 21),
                                          start_timestamp=datetime(2019, 1, 21, 9, 34, 13))

        self.assertEqual(len(queries), 1)
        query = queries[0]
        self.assertEqual(query.start_date, '2019-01-21')
        self.assertEqual(query.start_timestamp, '2019-01-21 09:34:13')
        self.assertEqual(query.query_execution_id, '6acb55b1-fddd-4608-bef8-ed206e1262de')
        self.assertEqual(query.query_state, 'RUNNING')
        self.assertEqual(query.executing_user, 'test')
        self.assertEqual(query.data_scanned, 0)
        self.assertEqual(query.query_sql, '')


if __name__ == '__main__':
    unittest.main()
