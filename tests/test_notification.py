import unittest
from unittest.mock import Mock

import requests

from bin.notificators.hard_threshold_notificator import HardThresholdNotificator


class NotificationTest(unittest.TestCase):

    @staticmethod
    def requests_side_effect(url, json, headers=None):
        response_mock = Mock()
        response_mock.status_code = requests.codes.ok
        if url == 'https://slack.com/api/conversations.open':
            response_mock.json.return_value = dict(channel=dict(id='test_channel'))

        return response_mock

    @staticmethod
    def get_mocked_config(user_threshold=None, channel_threshold=None, notificators=(HardThresholdNotificator)):
        config = Mock()
        config.SLACK_ALERT_DATA_USER_THRESHOLD = user_threshold
        config.SLACK_ALERT_DATA_CHANNEL_THRESHOLD = channel_threshold
        config.NOTIFICATORS = notificators
        config.SLACK_USER_MAPPINGS = {'test': 'mapped_user'}
        config.SLACK_HARD_THRESHOLD_MESSAGE = 'tests message'
        config.SLACK_HARD_THRESHOLD_MESSAGE_ADDITIONAL_ADMIN_MAIN_CHANNEL = 'text message admin channel'
        config.SLACK_HARD_THRESHOLD_MESSAGE_ADDITIONAL_PRIVATE_MESSAGE = 'text message private user'
        config.SLACK_WEBHOOK_URL = 'url'
        config.SLACK_BOT_TOKEN = 'token'
        config.CLOUDWATCH_METRIC_NAMESPACE = 'athena_alerter'
        config.CLOUDWATCH_METRIC_NAME = 'athena_alerter_bytes_scanned_test'
        config.ATHENA_PRICE_PER_TB = 5.0
        return config


if __name__ == '__main__':
    unittest.main()
