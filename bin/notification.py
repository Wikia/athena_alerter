"""
This file contains a lambda function reacting to query update sqs event and sending notifications for large queries

Currently only slack notifications are supported
"""

import json
import logging
from botocore.vendored import requests
from abc import ABC, abstractmethod

import settings
from model import AthenaQuery, AnomalyDetectionEvent, AnomalyDetectionMessage, AnomalyDetectionSns


logger = logging.getLogger()

def lambda_handler(event, context):
    """
    This lambda handler may be invoked by more than one events:
    as of Jan 2020 its hard threshold notification or anomaly detection notification.
    We have a simple logic which recognizes which event do we have at hand and we invoke an appropriate notifier
    """
    hard_threshold_notificator = HardThresholdNotificator(config=settings)
    anomaly_detection_notificator = AnomalyDetectionNotificator(config=settings)
    for record in event['Records']:
        if is_hard_threshold_event(record):
            anomaly_detection_notificator.handle_single_event(record=record)
        elif is_anomaly_detecion_alert_event(record):
            hard_threshold_notificator.handle_single_event(body=record['body'])
        else:
            logging.error("ERROR! Unknown event type!")
            logging.debug(json.dumps(event))
            raise Exception("ERROR! Unknown event type!")

def is_anomaly_detecion_alert_event(record):
    return 'EventSubscriptionArn' in record and 'anomaly_detection' in str.lower(record['EventSubscriptionArn'])

def is_hard_threshold_event(record):
    return 'eventSourceARN' in record and 'athena-queries' in record['eventSourceARN']


class Notificator(ABC):
    """
    Abstract class sharing common methods for different notifier classes.
    Handles incoming queue messages and sends slack notifications to appropriate users/channels when applicable
    """

    def __init__(self, config):
        self.config = config

    @abstractmethod
    def handle_single_event(self, record):
        """
        main queue record handling needs to be implemented here
        """
        pass

    def send_slack_to_channel(self, text):
        """
        Sends slack notification to a channel defined in config
        """
        requests.post(self.config.SLACK_WEBHOOK_URL, json={'text': text, 'link_names': 1})

    def send_slack_to_user(self, user_id, text):
        """
        Sends slack notification to the user with submitted user_id
        """
        response = requests.post('https://slack.com/api/conversations.open',
                                 headers={'Authorization': f'Bearer {self.config.SLACK_BOT_TOKEN}'},
                                 json={'users': user_id})
        response.raise_for_status()

        if response.status_code == requests.codes.ok:
            j = response.json()
            if j.get('channel'):
                channel_id = j['channel']['id']
                response = requests.post('https://slack.com/api/chat.postMessage',
                                         headers={'Authorization': f'Bearer {self.config.SLACK_BOT_TOKEN}'},
                                         json={'channel': channel_id, 'text': text})
                if response.status_code != requests.codes.ok:
                    logging.error(f'Unexpected response from slack api when sending message: {response}')
            else:
                logging.error(f'Unexpected response content from slack api when '
                              f'opening conversation with user {user_id}: {response}')
        else:
            logging.error(
                f'Unexpected response code from slack api when opening conversation with user {user_id}: {response}')


class AnomalyDetectionNotificator(Notificator):
    """
    Handles messages form CloudWatch about abnormally large (for the given user) athena queries
    """

    def __init__(self, config):
        self.config = config

    def handle_single_event(self, record):
        event = AnomalyDetectionEvent(**record)
        record_sns = AnomalyDetectionSns(**event.Sns)
        subject = record_sns.Subject
        message = AnomalyDetectionMessage(record_sns.Message)
        new_state_value = message.new_state_value
        if str.lower(new_state_value) == 'alarm':
            new_state_reason = message.new_state_reason
            user = message.user
            params = dict(subject=subject, user=user, new_state_reason=new_state_reason)
            text = self.config.SLACK_ANOMALY_DETECTION_THRESHOLD_MESSAGE.format(**params)
            self.send_slack_to_channel(text)
            if hasattr(self.config, 'SLACK_USER_MAPPINGS'):
                slack_user = self.config.SLACK_USER_MAPPINGS.get(user)
            if not slack_user:
                logger.warning(f'Couldn\'t find slack user mapping for user {user}')
            else:
                self.send_slack_to_user(slack_user, text)

class HardThresholdNotificator(Notificator):
    """
    Handles notifications that an athena query has ended.
    Events for all finished athena queries are submitted here.
    The class checks if scanned size thresholds are crossed and, if so, send appropriate notifications to slack.
    There are separate notifications for user and for the admin channel
    """

    def __init__(self, config):
        self.config = config

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
            data_scanned_bytes = query.data_scanned,
            data_scanned_gb = int(query.data_scanned / (1024*1024*1024)),
            slack_user_id = slack_user,
            user = query.executing_user
        )

        text = self.config.SLACK_HARD_THRESHOLD_MESSAGE.format(**params)
        if is_send_to_admin_channel:
            self.send_slack_to_channel(text)
        if not slack_user:
            logger.warning(f'Couldn\'t find slack user mapping for user {query.executing_user}')
        else:
            if is_send_to_user:
                self.send_slack_to_user(slack_user, text)
