import json
import logging
from typing import Mapping

from ..model import AthenaQuery
from .notificator import Notificator

logger = logging.getLogger()


class HardThresholdNotificator(Notificator):
    """
    Handles notifications that an athena query has ended.
    Events for all finished athena queries are submitted here.
    The class checks if scanned size thresholds are crossed and, if so, send appropriate notifications to slack.
    There are separate notifications for user and for the admin channel
    """

    def is_record_type_handled(self, record: Mapping) -> bool:
        return 'eventSourceARN' in record and 'athena-queries' in record['eventSourceARN']

    def handle_batch_event(self, event):
        # actually SQS should be configured to always provide a single event, hence no extra try/catch between records
        for record in event['Records']:
            self.handle_single_event(body=record['body'])

    def handle_single_event(self, body):
        query = AthenaQuery(**json.loads(body))
        # alert may be sent either to the user who submitted the query or to the admin team channel, or to both
        # here we decide where the notification is to be sent
        # if at least one threshold is reached, we call the send function with params where the message is to be sent
        is_send_to_user = query.data_scanned > self.config.SLACK_ALERT_DATA_USER_THRESHOLD
        is_send_to_admin_channel = query.data_scanned > self.config.SLACK_ALERT_DATA_CHANNEL_THRESHOLD
        if is_send_to_user or is_send_to_admin_channel:
            self.send_slack_notification(query, is_send_to_user, is_send_to_admin_channel)

    def send_slack_notification(self, query, is_send_to_user=True, is_send_to_admin_channel=True):
        slack_user = None
        if hasattr(self.config, 'SLACK_USER_MAPPINGS'):
            slack_user = self.config.SLACK_USER_MAPPINGS.get(query.executing_user)
        params = dict(
            data_scanned_bytes=query.data_scanned,
            data_scanned_gb=int(query.data_scanned / (1024 * 1024 * 1024)),
            slack_user_id=slack_user,
            user=query.executing_user
        )

        text = self.config.SLACK_HARD_THRESHOLD_MESSAGE.format(**params)
        text_additional_1 = self.config.SLACK_HARD_THRESHOLD_MESSAGE_ADDITIONAL_1.format(**params)
        text_additional_2 = self.config.SLACK_HARD_THRESHOLD_MESSAGE_ADDITIONAL_2.format(**params)
        if is_send_to_admin_channel:
            self.send_slack_to_channel(text + text_additional_1)
        if not slack_user:
            logger.warning(f'Couldn\'t find slack user mapping for user {query.executing_user}')
        else:
            if is_send_to_user:
                self.send_slack_to_user(slack_user, text + text_additional_2)
