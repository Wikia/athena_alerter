SHELL := /bin/bash

zip_lambda:
	pushd bin && zip -r ../lambda.zip . && popd

upload_lambda: zip_lambda
	aws s3 cp lambda.zip "s3://$(LAMBDA_BUCKET)/$(LAMBDA_KEY)"

run_cloudformation: upload_lambda
	aws cloudformation create-stack --capabilities CAPABILITY_IAM --stack-name AthenaAlerter --template-body file://cloudformation/cf.yaml --parameters ParameterKey=CloudtrailBucket,ParameterValue=$(CLOUDTRAIL_BUCKET) ParameterKey=LambdaS3Bucket,ParameterValue=$(LAMBDA_BUCKET) ParameterKey=LambdaS3Key,ParameterValue=$(LAMBDA_KEY) ParameterKey=DynamoDBTableName,ParameterValue=$(DYNAMODB_TABLE_NAME) ParameterKey=SQSQueueName,ParameterValue=$(SQS_QUEUE_NAME) ParameterKey=SNSAnomalyDetectionTopicName,ParameterValue=$(SNS_ANOMALY_DETECTION_TOPIC_NAME) ParameterKey=RequestsLayer,ParameterValue=$(REQUESTS_LAYER)
