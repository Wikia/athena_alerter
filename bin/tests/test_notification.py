import unittest
from unittest.mock import Mock, patch
import requests
import json

from notificators.hard_threshold_notificator import HardThresholdNotificator
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
        config.SLACK_HARD_THRESHOLD_MESSAGE = 'test message'
        config.SLACK_ANOMALY_DETECTION_THRESHOLD_MESSAGE = 'test message anomaly'
        config.SLACK_WEBHOOK_URL = 'url'
        config.SLACK_BOT_TOKEN = 'token'
        config.CLOUDWATCH_METRIC_NAMESPACE = 'athena_alerter'
        config.CLOUDWATCH_METRIC_NAME = 'athena_alerter_bytes_scanned_test'
        return config

    @patch('notification.requests')
    def test_handle_batch_event_user_and_channel_value_above_threshold(self, requests):
        config = NotificatorTest.prepare_config_mock(user_threshold=100, channel_threshold=100)
        body = utils.get_content('fixtures/notification_sqs_event.json')

        requests.post.side_effect = NotificatorTest.requests_side_effect
        requests.codes.ok = 200

        events = dict(Records=[dict(body=body)])

        sut = HardThresholdNotificator(config)
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

        sut = HardThresholdNotificator(config)
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

        sut = HardThresholdNotificator(config)
        sut.handle_batch_event(events)

        requests.post.assert_not_called()

    @patch('notification.requests')
    def test_anomaly_detection_notifier(self, requests):
        requests.post.side_effect = NotificatorTest.requests_side_effect
        requests.codes.ok = 200
        config = NotificatorTest.prepare_config_mock(user_threshold=100, channel_threshold=100)
        body = json.loads(utils.get_content('fixtures/anomaly_detection_sns.json'))
        anomaly_not = AnomalyDetectionNotificator(config)
        anomaly_not.handle_single_event(body)

        requests.post.assert_any_call('url', json={'text': 'test message anomaly', 'link_names': 1})
        requests.post.assert_any_call('https://slack.com/api/conversations.open',
                                      headers={'Authorization': 'Bearer token'},
                                      json={'users': 'mapped_user'})
        requests.post.assert_any_call('https://slack.com/api/chat.postMessage',
                                      headers={'Authorization': 'Bearer token'},
                                      json={'channel': 'test_channel', 'text': 'test message anomaly'})

    def test_is_anomaly_detecion_alert_event(self):
        body = json.loads(utils.get_content('fixtures/anomaly_detection_sns.json'))
        self.assertTrue(is_anomaly_detecion_alert_event(body))
        self.assertFalse(is_hard_threshold_event(body))

    def test_anomaly_detecion_alert_event_recognition(self):
        body = json.loads(utils.get_content('fixtures/anomaly_detection_sns.json'))
        self.assertTrue(is_anomaly_detecion_alert_event(body))
        self.assertFalse(is_hard_threshold_event(body))

if __name__ == '__main__':
    unittest.main()
