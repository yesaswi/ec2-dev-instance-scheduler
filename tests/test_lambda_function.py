import os
import boto3
import pytest
from moto import mock_aws
from src.lambda_function import lambda_handler

# Define the default region for tests
TEST_REGION = 'us-east-1'

@pytest.fixture(autouse=True)
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_REGION'] = TEST_REGION # For lambda_handler
    os.environ['AWS_DEFAULT_REGION'] = TEST_REGION # For boto3 client in tests

@pytest.fixture
def ec2_client():
    """Yield a mock EC2 client."""
    with mock_aws():
        client = boto3.client('ec2', region_name=TEST_REGION)
        yield client

def create_instance(ec2_client, tags=None, state='running', image_id='ami-12345678', instance_type='t2.micro'):
    """Helper function to create an EC2 instance with specific tags and state."""
    if tags is None:
        tags = []

    tag_spec = [{'ResourceType': 'instance', 'Tags': tags}]
    
    instance = ec2_client.run_instances(
        ImageId=image_id,
        MinCount=1,
        MaxCount=1,
        InstanceType=instance_type,
        TagSpecifications=tag_spec
    )['Instances'][0]
    instance_id = instance['InstanceId']

    if state != 'running':
        if state == 'stopped':
            ec2_client.stop_instances(InstanceIds=[instance_id])
        elif state == 'terminated':
            ec2_client.terminate_instances(InstanceIds=[instance_id])
        # Add other states if needed
    return instance_id

def get_instance_state(ec2_client, instance_id):
    """Helper function to get the state of an instance."""
    response = ec2_client.describe_instances(InstanceIds=[instance_id])
    return response['Reservations'][0]['Instances'][0]['State']['Name']

# --- Test Cases ---

def test_lambda_handler_stops_single_dev_instance(ec2_client):
    """Test the happy path: a single running 'Dev' instance is stopped."""
    dev_instance_id = create_instance(ec2_client, tags=[{'Key': 'Environment', 'Value': 'Dev'}])
    
    result = lambda_handler({}, {})
    
    assert get_instance_state(ec2_client, dev_instance_id) == 'stopped'
    assert result['statusCode'] == 200
    assert f"Successfully initiated stop for 1 instances: {dev_instance_id}" in result['body']

def test_lambda_handler_no_instances_to_stop(ec2_client):
    """Test behavior when no instances match the criteria."""
    # Create a non-Dev instance to ensure the filter is the reason none are stopped
    create_instance(ec2_client, tags=[{'Key': 'Environment', 'Value': 'Prod'}])
    
    result = lambda_handler({}, {})
    
    assert result['statusCode'] == 200
    assert "No instances found to stop" in result['body'] # Adjusted based on lambda output

def test_lambda_handler_ignores_non_dev_instances(ec2_client):
    """Test that instances without the 'Dev' tag are not stopped."""
    dev_instance_id = create_instance(ec2_client, tags=[{'Key': 'Environment', 'Value': 'Dev'}])
    prod_instance_id = create_instance(ec2_client, tags=[{'Key': 'Environment', 'Value': 'Prod'}])
    
    result = lambda_handler({}, {})
    
    assert get_instance_state(ec2_client, dev_instance_id) == 'stopped'
    assert get_instance_state(ec2_client, prod_instance_id) == 'running'
    assert result['statusCode'] == 200
    assert f"Successfully initiated stop for 1 instances: {dev_instance_id}" in result['body']

def test_lambda_handler_ignores_dev_instances_not_running(ec2_client):
    """Test that 'Dev' instances not in a 'running' state are ignored."""
    stopped_dev_instance_id = create_instance(ec2_client, tags=[{'Key': 'Environment', 'Value': 'Dev'}], state='stopped')
    
    result = lambda_handler({}, {})
    
    assert get_instance_state(ec2_client, stopped_dev_instance_id) == 'stopped'
    assert result['statusCode'] == 200
    assert "No instances found to stop" in result['body'] # Or specific message from lambda

def test_lambda_handler_stops_multiple_dev_instances(ec2_client):
    """Test stopping multiple 'Dev' instances."""
    dev_instance_id1 = create_instance(ec2_client, tags=[{'Key': 'Environment', 'Value': 'Dev'}])
    dev_instance_id2 = create_instance(ec2_client, tags=[{'Key': 'Environment', 'Value': 'Dev'}])
    prod_instance_id = create_instance(ec2_client, tags=[{'Key': 'Environment', 'Value': 'Prod'}])
    
    result = lambda_handler({}, {})
    
    assert get_instance_state(ec2_client, dev_instance_id1) == 'stopped'
    assert get_instance_state(ec2_client, dev_instance_id2) == 'stopped'
    assert get_instance_state(ec2_client, prod_instance_id) == 'running'
    assert result['statusCode'] == 200
    
    # Check that both instances are mentioned in the body. Order might vary.
    assert f"Successfully initiated stop for 2 instances" in result['body']
    assert dev_instance_id1 in result['body']
    assert dev_instance_id2 in result['body']

def test_lambda_handler_case_sensitive_dev_tag(ec2_client):
    """Test that 'Dev' tag matching is case-sensitive."""
    dev_lower_id = create_instance(ec2_client, tags=[{'Key': 'Environment', 'Value': 'dev'}])
    dev_upper_id = create_instance(ec2_client, tags=[{'Key': 'Environment', 'Value': 'DEV'}])
    
    result = lambda_handler({}, {})
    
    assert get_instance_state(ec2_client, dev_lower_id) == 'running'
    assert get_instance_state(ec2_client, dev_upper_id) == 'running'
    assert result['statusCode'] == 200
    assert "No instances found to stop" in result['body']

# Future test for error handling (requires more advanced mocking if instance.stop() fails)
# def test_lambda_handler_handles_instance_stop_failure(ec2_client, monkeypatch):
#     """Test graceful handling when an instance fails to stop."""
#     dev_instance_id1 = create_instance(ec2_client, tags=[{'Key': 'Environment', 'Value': 'Dev'}])
#     dev_instance_id2 = create_instance(ec2_client, tags=[{'Key': 'Environment', 'Value': 'Dev'}])

#     # Mock boto3's EC2 resource and instance stop method for one instance
#     # This is complex with moto and might need direct patching of the lambda's boto3 usage
#     # For now, this is a placeholder for a more advanced test.

#     # result = lambda_handler({}, {})
#     # assert result['statusCode'] == 207 # Multi-Status
#     # assert f"Successfully initiated stop for 1 instances: {dev_instance_id1}" in result['body'] # Or id2
#     # assert f"Failed to initiate stop for 1 instances: {dev_instance_id2}" in result['body'] # Or id1
#     pass # Placeholder
