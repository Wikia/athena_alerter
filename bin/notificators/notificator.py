import logging
from abc import ABC, abstractmethod
from typing import Mapping

import requests


class Notificator(ABC):
    """
    Abstract class sharing common methods for different notifier classes.
    Handles incoming queue messages and sends slack notifications to appropriate users/channels when applicable
    """

    def __init__(self, config):
        self.config = config

    @classmethod
    @abstractmethod
    def is_record_type_handled(cls, record: Mapping) -> bool:
        """
        Check for recognizing event records belonging to this particulator Notificator
        """
        pass

    @abstractmethod
    def handle_single_event(self, body):
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