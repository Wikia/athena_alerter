import unittest
from unittest.mock import Mock, patch
import requests

from notification import Notificator
from tests import utils


class NotificatorTest(unittest.TestCase):

    @staticmethod
    def requests_side_effect(url, json, headers=None):
        response_mock = Mock()
        response_mock.status_code = requests.codes.ok
        if url == 'https://slack.com/api/conversations.open':
            response_mock.json.return_value = dict(channel=dict(id='test_channel'))

        return response_mock

    @patch('notification.requests')
    def test_handle_batch_event(self, requests):

        config = Mock()
        config.SLACK_ALERT_DATA_THRESHOLD = 100
        config.SLACK_USER_MAPPINGS = {'test': 'mapped_user'}
        config.SLACK_MESSAGE = 'test message'
        config.SLACK_WEBHOOK_URL = 'url'
        config.SLACK_BOT_TOKEN = 'token'

        body = utils.get_content('fixtures/notification_sqs_event.json')

        requests.post.side_effect = NotificatorTest.requests_side_effect
        requests.codes.ok = 200

        events = dict(Records=[dict(body=body)])

        sut = Notificator(config)
        sut.handle_batch_event(events)

        requests.post.assert_any_call('url', json={'text': 'test message', 'link_names': 1})
        requests.post.assert_any_call('https://slack.com/api/conversations.open',
                                      headers={'Authorization': 'Bearer token'},
                                      json={'users': 'mapped_user'})
        requests.post.assert_any_call('https://slack.com/api/chat.postMessage',
                                      headers={'Authorization': 'Bearer token'},
                                      json={'channel': 'test_channel', 'text': 'test message'})

if __name__ == '__main__':
    unittest.main()
