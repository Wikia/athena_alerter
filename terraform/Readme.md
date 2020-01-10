Anomaly detection terraform
================

In this directory there are some resources for generating anomaly detection alerts on Cloudwatch using metrics submitted to Cloudwatch by Athena Alerter.

## Metrics

The metrics, which we want to use, need to have athena_user dimension and scanned bytes counts as values.
They need to be submitted to the cloudwatch, e.g. by usage_updater script.

## Terraform file

We need to create a separate anomaly detection alert per user (athena_user is the dimension in the metric).
Terraform 11 does not support loops, so we generate the final terraform file using python and Jinja2 template.
In file anomaly_detection.template you can find a Jinja2 template with appropriate instructions, including loop over submitted users list.

The template is filled using `generate_metrics_for_multiple_users.py`.
The users list is read from `users.lst` file.
If users.lst file is up to date, all you need to do is to run `generate_metrics_for_multiple_users.py` script, which will generate the final terraform file.
The script has several parameters, which have default values, but may also be overwritten as cmd params.
The explanation of these params is stored in the script. 
Use --help switch to see the available params.


Later, you just need to apply the terraform in a regular way: 

```
terraform plan
terraform apply
```

This should create all the necessary alerts in terraform. 
Please note that for some time (days, maybe even weeks) these alerts may be inactive due to insufficient data (see cloudwatch alerts console to see the status of different alerts).
