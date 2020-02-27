import json
from dataclasses import dataclass
from enum import Enum

TIMESTAMP_FORMAT = '%Y-%m-%d %H:%M:%S'


class QueryState(Enum):
    QUEUED = 'QUEUED'
    RUNNING = 'RUNNING'
    SUCCEEDED = 'SUCCEEDED'
    FAILED = 'FAILED'
    CANCELLED = 'CANCELLED'


@dataclass
class AthenaQuery:
    start_date: str
    start_timestamp: str
    query_execution_id: str
    query_state: str
    executing_user: str
    data_scanned: int = 0
    query_sql: str = None


@dataclass
class AnomalyDetectionEvent:
    """
    dataclass corresponding to a sns message about anomaly detection from cloudwatch
    should match also other sns messages
    """
    EventSource: str
    EventVersion: str
    EventSubscriptionArn: str
    Sns: dict


@dataclass
class AnomalyDetectionSns:
    """
    dataclass corresponding to a part of sns message about anomaly detection from cloudwatch
    should match also other sns messages
    """
    Type: str
    MessageId: str
    TopicArn: str
    Subject: str
    Message: str
    Timestamp: str
    SignatureVersion: str
    Signature: str
    SigningCertUrl: str
    UnsubscribeUrl: str
    MessageAttributes: str


class AnomalyDetectionMessage:
    """
    class corresponding to a part of sns message about anomaly detection from cloudwatch
    this one is specific to our cloudwatch metric anomaly detection alerts
    """

    def __init__(self, message_json):
        message = json.loads(message_json)
        self.new_state_value = message['NewStateValue']
        self.new_state_reason = message['NewStateReason']
        self.user = dict([(i['name'], i['value']) for i in message['Trigger']['Dimensions']])['athena_user']
