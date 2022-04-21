import unittest
from unittest.mock import patch

from bin.notificators.hard_threshold_notificator import HardThresholdNotificator
from .. import utils
from ..test_notification import NotificationTest


class TestHardThresholdNotificator(unittest.TestCase):

    @patch('bin.notificators.notificator.requests')
    def test_handle_batch_event_user_and_channel_value_above_threshold(self, requests):
        config = NotificationTest.get_mocked_config(user_threshold=100, channel_threshold=100)
        body = utils.get_content('fixtures/notification_sqs_event.json')

        requests.post.side_effect = NotificationTest.requests_side_effect
        requests.codes.ok = 200

        events = dict(Records=[dict(body=body)])

        sut = HardThresholdNotificator(config)
        sut.handle_batch_event(events)

        requests.post.assert_any_call('url', json={'text': 'tests message', 'link_names': 1})
        requests.post.assert_any_call('https://slack.com/api/conversations.open',
                                      headers={'Authorization': 'Bearer token'},
                                      json={'users': 'mapped_user'})
        requests.post.assert_any_call('https://slack.com/api/chat.postMessage',
                                      headers={'Authorization': 'Bearer token'},
                                      json={'channel': 'test_channel', 'text': 'tests message'})

    @patch('bin.notificators.notificator.requests')
    def test_handle_batch_event_test_separate_thresholds_channel_only(self, requests):
        # we should get only one API call as user threshold is above the actual value and channel threshold is below
        # please be advised that if slack API will change in the future...
        # ...this tests may start to fail (as more than one requests may be needed)
        config = NotificationTest.get_mocked_config(user_threshold=10000000000000000, channel_threshold=100)
        body = utils.get_content('fixtures/notification_sqs_event.json')

        requests.post.side_effect = NotificationTest.requests_side_effect
        requests.codes.ok = 200

        events = dict(Records=[dict(body=body)])

        sut = HardThresholdNotificator(config)
        sut.handle_batch_event(events)

        requests.post.assert_any_call('url', json={'text': 'tests message\ntext message admin channel', 'link_names': 1})
        requests.post.assert_called_once()

    @patch('bin.notificators.notificator.requests')
    def test_handle_batch_event_user_and_channel_value_below_threshold(self, requests):
        # we should have no API calls as user and channel thresholds are above the actual value
        config = NotificationTest.get_mocked_config(user_threshold=10000000000000000,
                                                    channel_threshold=10000000000000)
        body = utils.get_content('fixtures/notification_sqs_event.json')

        requests.post.side_effect = NotificationTest.requests_side_effect
        requests.codes.ok = 200

        events = dict(Records=[dict(body=body)])

        sut = HardThresholdNotificator(config)
        sut.handle_batch_event(events)

        requests.post.assert_not_called()


if __name__ == '__main__':
    unittest.main()
