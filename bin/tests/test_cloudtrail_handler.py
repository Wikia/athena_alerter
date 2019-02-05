import unittest
import os
from unittest.mock import Mock
import gzip
from io import BytesIO

from model import AthenaQuery
from cloudtrail_handler import CloudtrailHandler


class CloudtrailHandlerTest(unittest.TestCase):

    def get_gziped_content(self, path):
        dir = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(dir, path)) as fixture:
            stream = BytesIO()
            with gzip.GzipFile(None, 'wb', fileobj=stream) as file:
                file.write(bytes(fixture.read(), 'utf-8'))
            return stream.getvalue()

    def test_update_query_usage(self):
        #given
        config = Mock()
        config.QUERIES_TABLE = 'test_table'

        dynamodb = Mock()

        s3 = Mock()
        s3_object = Mock()
        s3.Object.return_value.get.return_value = dict(Body=s3_object)
        s3_object.read.return_value = self.get_gziped_content('fixtures/query_write_cloudtrail.json')

        query_dao = Mock()

        event = dict(Records=[dict(s3=dict(bucket=dict(name='bucket'), object=dict(key='key')))])

        #when
        sut = CloudtrailHandler(config, s3, query_dao)
        sut.process_log(event)

        #then
        s3.Object.assert_called_with('bucket', 'key')

        query_dao.insert_query.assert_called_with(AthenaQuery(
            start_date='2019-01-17',
            start_timestamp='2019-01-17 11:57:30',
            query_execution_id='fda9a497-05e8-4c76-9734-561118eb3623',
            query_state='RUNNING',
            executing_user='testUser',
            data_scanned=0,
            query_sql=None))

if __name__ == '__main__':
    unittest.main()
