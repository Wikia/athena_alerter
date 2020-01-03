import boto3
import settings

"""
This class sends metrics about finished athena queryies to cloudwatch
"""
class CloudwatchMetrics:

    cloudwatch = boto3.client('cloudwatch')

    @classmethod
    def report_query_metric(cls, metric_value, user):
        """
        Send metric to cloudwatch about the scanned size for the particular query
        You just need to submit scanned size and the name of the user, who submitted the query
        """
        metric_data = cls._prepare_metric_dict(metric_value, user)
        cls.cloudwatch.put_metric_data(
            MetricData=metric_data,
            Namespace=settings.CLOUDWATCH_METRIC_NAMESPACE
        )

    @classmethod
    def _prepare_metric_dict(cls, value, user):
        return [
            {
                'MetricName': settings.CLOUDWATCH_METRIC_NAME,
                'Dimensions': [
                    {
                        'Name': 'athena_user',
                        'Value': user
                    },
                ],
                'Unit': 'Bytes',
                'Value': value
            },
        ]
