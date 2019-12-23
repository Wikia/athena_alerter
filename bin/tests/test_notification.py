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

    @staticmethod
    def prepare_config_mock(user_threshold, channel_threshold):
        config = Mock()
        config.SLACK_ALERT_DATA_USER_THRESHOLD = user_threshold
        config.SLACK_ALERT_DATA_CHANNEL_THRESHOLD = channel_threshold
        config.SLACK_USER_MAPPINGS = {'test': 'mapped_user'}
        config.SLACK_MESSAGE = 'test message'
        config.SLACK_WEBHOOK_URL = 'url'
        config.SLACK_BOT_TOKEN = 'token'
        return config

    @patch('notification.requests')
    def test_handle_batch_event_user_and_channel_value_above_threshold(self, requests):
        config = NotificatorTest.prepare_config_mock(user_threshold=100, channel_threshold=100)
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

    @patch('notification.requests')
    def test_handle_batch_event_test_separate_thresholds(self, requests):
        # we should get only one API call as user threshold is above the actual value and channel threshold is below
        # please be advised that if slack API will change in the future...
        # ...this test may start to fail (as more than one requests may be needed)
        config = NotificatorTest.prepare_config_mock(user_threshold=10000000000000000, channel_threshold=100)
        body = utils.get_content('fixtures/notification_sqs_event.json')

        requests.post.side_effect = NotificatorTest.requests_side_effect
        requests.codes.ok = 200

        events = dict(Records=[dict(body=body)])

        sut = Notificator(config)
        sut.handle_batch_event(events)

        requests.post.assert_any_call('url', json={'text': 'test message', 'link_names': 1})
        requests.post.assert_called_once()

    @patch('notification.requests')
    def test_handle_batch_event_user_and_channel_value_below_threshold(self, requests):
        # we should have no API calls as user and channel thresholds are above the actual value
        config = NotificatorTest.prepare_config_mock(user_threshold=10000000000000000, channel_threshold=10000000000000)
        body = utils.get_content('fixtures/notification_sqs_event.json')

        requests.post.side_effect = NotificatorTest.requests_side_effect
        requests.codes.ok = 200

        events = dict(Records=[dict(body=body)])

        sut = Notificator(config)
        sut.handle_batch_event(events)

        requests.post.assert_not_called()


if __name__ == '__main__':
    unittest.main()
