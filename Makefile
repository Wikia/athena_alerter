SHELL := /bin/bash

test:
	python -m unittest discover

zip_lambda:
	zip -r lambda.zip bin

upload_lambda: zip_lambda
	aws s3 cp lambda.zip "s3://$(LAMBDA_BUCKET)/$(LAMBDA_KEY)"

run_cloudformation: upload_lambda
	aws cloudformation create-stack --capabilities CAPABILITY_IAM --stack-name AthenaAlerter --template-body file://cloudformation/cf.yaml --parameters ParameterKey=CloudtrailBucket,ParameterValue=$(CLOUDTRAIL_BUCKET) ParameterKey=LambdaS3Bucket,ParameterValue=$(LAMBDA_BUCKET) ParameterKey=LambdaS3Key,ParameterValue=$(LAMBDA_KEY) ParameterKey=DynamoDBTableName,ParameterValue=$(DYNAMODB_TABLE_NAME) ParameterKey=SQSQueueName,ParameterValue=$(SQS_QUEUE_NAME) ParameterKey=RequestsLayer,ParameterValue=$(REQUESTS_LAYER)
