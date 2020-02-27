"""
This file contains a lambda function reacting to query update sqs event and sending notifications for large queries

Currently only slack notifications are supported
"""

import json
import logging
from typing import Sequence

import settings
from notificators.notificator import Notificator

logger = logging.getLogger()


def lambda_handler(event, context):
    """
    This handles events and may handle more than one event type.
    If you have more events that you'd like to be notified on,
    register them in settings.py under NOTIFICATORS
    """
    notificators: Sequence[Notificator] = [notificator(config=settings) for notificator in settings.NOTIFICATORS]

    for record in event['Records']:
        for notificator in notificators:
            if notificator.is_record_type_handled(record):
                notificator.handle_single_event(body=record['body'])
                break
        else:
            logging.error("ERROR! Unknown event type!")
            logging.debug(json.dumps(event))
            raise Exception("ERROR! Unknown event type!")


