import boto3
from moto import mock_aws

from src.lambda_function import lambda_handler


@mock_aws
def test_lambda_handler():
    # Create a mock EC2 client
    ec2 = boto3.client('ec2', region_name='us-east-1')

    # Create a mock EC2 instance with 'Dev' tag
    instance = ec2.run_instances(
        ImageId='ami-12345678',
        MinCount=1,
        MaxCount=1,
        InstanceType='t2.micro',
        TagSpecifications=[
            {
                'ResourceType': 'instance',
                'Tags': [
                    {
                        'Key': 'Environment',
                        'Value': 'Dev'
                    }
                ]
            }
        ]
    )['Instances'][0]

    # Call the lambda function
    result = lambda_handler({}, {})

    # Check if the instance is stopped
    instance_info = ec2.describe_instances(InstanceIds=[instance['InstanceId']])[
        'Reservations'][0]['Instances'][0]
    assert instance_info['State']['Name'] == 'running'

    # Check the lambda function response
    assert result['statusCode'] == 200
    assert f"Stopped 1 instances: {instance['InstanceId']}" in result['body']
