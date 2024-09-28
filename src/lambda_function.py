import logging

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    ec2 = boto3.resource('ec2')

    instances = ec2.instances.filter(
        Filters=[
            {'Name': 'instance-state-name', 'Values': ['running']},
            {'Name': 'tag:Environment', 'Values': ['Dev']}
        ]
    )

    stopped_instances = []

    for instance in instances:
        instance.stop()
        stopped_instances.append(instance.id)
        logger.info(f"Stopped instance: {instance.id}")

    return {
        'statusCode': 200,
        'body': f"Stopped {len(stopped_instances)} instances: {', '.join(stopped_instances)}"
    }
