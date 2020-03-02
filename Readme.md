# Overview

Athena Alerter is a tool which notifies users when they run an athena query which scans more than X bytes of data.

It's intended to keep your athena usage/bill in check and build awareness among users how efficient queries they are writing.

Currently slack notifications are supported. These are sent to a channel and optionally as direct messages. However, given the very modular nature of this project you can easly adjust it to provide different types of alerts. Information about finished queries is sent to a SQS queue, so you may build a custom consumer which sends this information e.g. via e-mail or pushes to some (No)SQL storage.

In future, we are planning to provide aggregated mothly user stats visualized on our open source dashboard [discreETLy](https://github.com/Wikia/discreETLy)

## Costs
Athena alerter uses AWS infrastructure which you have to pay for. However, only serverless components are used and the actual amount of processed data is small, unless you are executing thousands of athena queries a minute. In typical use cases, the cost of each component should not exceed a few dollars a month. Componenets include:
- Three lambda functions. One invoked once a minute, one for every cloudtrail log file, one for each finished athena query,
- S3 storage of cloudtrail logs,
- A single SQS queue - one event per finished query,
- One DynamoDB table for queries.

Enabling all features, enabling cloudtrail (not counting s3 log storage) and using cloudformation does not introduce additional costs.

## Prerequisites

- Athena Alerter uses cloudtrail, which requires "All features" to be enabled on your AWS account. More on that can be found in AWS documentation - [Enabling all features](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_org_support-all-features.html),
- You should create a s3 bucket to store the lambda code,
- Host your own Lambda Layer with python3's `requests` or e.g. use communities' from your region: https://github.com/keithrozario/Klayers/tree/master/deployments/python3.7/arns
- Your user account needs to have permissions to create all the resources used by athena alerter. If you're missing some, stack creation will fail and you'll see which permission you're lacking in the cloudformation console.

## Deployment

Creation of all components required for Athena Alerter to function is done automatically via cloudformation. However, you need to provide a settings.py configuration file and corresponding input parameters for the makefile.

To deploy Athena Alerter:
- Create settings.py based on settings.py.template
- Run make run_cloudformation. You need to provide the following parameters:
    - LAMBDA_BUCKET - name of s3 bucket in which you want to store the lambda function code. The bucket needs to already exist,
    - LAMBDA_KEY - key under the LAMBDA_BUCKET where the ziped lambda code should be stored,
    - CLOUDTRAIL_BUCKET - name of s3 bucket in which to store cloudtrail logs. This bucket should not exist and will be created for you,
    - DYNAMODB_TABLE_NAME - name of dynamodb table which will be used for storing query data. The table should not exist and will be created for you. The name needs to match the QUERIES_TABLE parameter from settings.py,
    - SQS_QUEUE_NAME - name of sqs queue used for query finished events. The queue should not exists and will be created for you. The name needs to match the SQS_QUEUE_URL parameter from settings.py.
    - REQUESTS_LAYER - ARN address to Lambda Layer containing `requests`
    
Note that S3 bucket names need to be globally unique (that means for all aws accounts).
    
Sample deployment:
```
cp bin/settings.py.template bin/settings.py
vi settings.py # Or use any other editor and provide configuration
make LAMBDA_BUCKET=myorg-code-bucket LAMBDA_KEY=lambda/athena_alerter.zip CLOUDTRAIL_BUCKET=myorg-cloudtrail DYNAMODB_TABLE_NAME=athena_queries SQS_QUEUE_NAME=athena_queries run_cloudformation 

```

Once executed you can track progress and see any potential errors occured during stack creation in the cloudformation console https://console.aws.amazon.com/cloudformation

## Testing
To run the provided unit tests you need to install requirements listed in requirements.txt. Ideally create a virtualenv for that. After that simply run unittest. i.e.

```
cd athena_alerter/bin
virtualenv -p python3.7 venv
pip install -r ./../requirements.txt
python -m unittest discover
```

## Architecture

The tool consist of three lambda functions:
- cloudtrail_handler - this function processes cloudtrail logs and adds entries to the DynamoDB table. At this stage we provide query, executing user, start time and execution id.
- usage_update - this function runs every minute, takes queries that are in "Running" state and updates information about amount of scanned data. Note that athena api does not provide information about executing user, hence we rely on cloudtrail for that. When a query execution finishes a SQS event is generated
- notification - this function runs for each sqs event, checks whether the amount of data scanned exceeded the notification threshold and if so, generates a slack message. If you want to process the data scanned information differently, this function can be easily replaced with your own implementation.

Note that because of the nature of cloudtrail log processing, notifications arrive a few minutes after the actual query has started.
