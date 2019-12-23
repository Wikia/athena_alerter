"""
This file contains a lambda function reacting to query update sqs event and sending notifications for large queries

Currently only slack notifications are supported
"""

import json
import logging
from botocore.vendored import requests

import settings
from model import AthenaQuery, QueryState


logger = logging.getLogger()

def lambda_handler(event, context):
    notificator = Notificator(config=settings)
    notificator.handle_batch_event(event)


class Notificator:

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

    def send_slack_to_channel(self, text):
        requests.post(self.config.SLACK_WEBHOOK_URL, json={'text': text, 'link_names': 1})

    def send_slack_to_user(self, user_id, text):
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

        text = self.config.SLACK_MESSAGE.format(**params)
        if is_send_to_admin_channel:
            self.send_slack_to_channel(text)
        if slack_user and is_send_to_user:
            self.send_slack_to_user(slack_user, text)
        else:
            logger.warning(f'Couldn\'t find slack user mapping for user {query.executing_user}')
