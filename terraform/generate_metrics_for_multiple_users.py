from jinja2 import Template
import argparse

"""
This scripts generates a terraform file with multiple alerts, one alert per user in USERS_LIST_FILE.
It works by filling jinja2 template with terraform instructions.
The template contains loop instruction over the submitted users list
"""

# default values
TEMPLATE_FILE = 'anomaly_detection.template'
GENERATED_TERRAFORM_FILE_NAME = 'anomaly_detection.tf'
USERS_LIST_FILE_NAME = 'users.lst'
METRIC_NAME = 'athena_alerter_bytes_scanned_test'
NAMESPACE = 'athena_alerter'
ALERT_SNS_QUEUE_ARN = "arn:aws:sns:us-east-1:170047911957:athena_alerter_anomaly_detection_test"

# you may override arguments with --option_name cmd params
parser = argparse.ArgumentParser()
parser.add_argument('--template_file', type=str, help='Where the file with Jinja2 template is stored')
parser.add_argument('--generated_terraform_file_name', type=str, help='Where the generated final terraform file should be saved')
parser.add_argument('--users_list_file_name', type=str, help='Name of the file with the lis tof users, for which we want to create metrics. One username a line')
parser.add_argument('--metric_name', type=str, help='Name of the metric on the cloudwatch to be use as a base for the alarm')
parser.add_argument('--namespace', type=str, help='Namespace of the metric on the cloudwatch to be use as a base for the alarm')
parser.add_argument('--alert_sns_queue_arn', type=str, help='Where the anomaly detection messages are to be sent - name of SNS topic')

args = parser.parse_args()
if args.template_file:
    TEMPLATE_FILE = args.template_file
if args.generated_terraform_file_name:
    GENERATED_TERRAFORM_FILE_NAME = args.generated_terraform_file_name
if args.users_list_file_name:
    USERS_LIST_FILE_NAME = args.users_list_file_name
if args.metric_name:
    METRIC_NAME = args.metric_name
if args.namespace:
    NAMESPACE = args.namespace
if args.alert_sns_queue_arn:
    ALERT_SNS_QUEUE_ARN = args.alert_sns_queue_arn


users = [i.strip() for i in open(USERS_LIST_FILE_NAME).readlines()]
fhin = open(TEMPLATE_FILE)
template = Template(fhin.read())
with open(GENERATED_TERRAFORM_FILE_NAME, 'w') as fhout:
    fhout.write(template.render(users=users, metric_name=METRIC_NAME, namespace=NAMESPACE, alert_sns_queue_arn=ALERT_SNS_QUEUE_ARN))
print('Terraform file generated, bye!')