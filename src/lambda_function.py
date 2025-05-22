import logging
import os
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    region = os.environ.get('AWS_REGION', 'us-east-1')
    ec2 = boto3.resource('ec2', region_name=region)

    logger.info(f"Searching for running instances tagged 'Environment:Dev' in region {region}")

    try:
        instances = ec2.instances.filter(
            Filters=[
                {'Name': 'instance-state-name', 'Values': ['running']},
                {'Name': 'tag:Environment', 'Values': ['Dev']}
            ]
        )

        # Convert iterator to list to get the count and allow iteration
        instance_list = list(instances)
        logger.info(f"Found {len(instance_list)} instances matching criteria.")

    except botocore.exceptions.ClientError as e:
        logger.error(f"AWS SDK error filtering instances: {str(e)}")
        return {
            'statusCode': 500,
            'body': f"AWS SDK error filtering instances: {str(e)}"
        }
    except Exception as e: # Catch any other unexpected errors during filtering
        logger.error(f"Unexpected error filtering instances: {str(e)}")
        return {
            'statusCode': 500,
            'body': f"Unexpected error filtering instances: {str(e)}"
        }

    stopped_instances_ids = []
    failed_to_stop_ids = []

    if not instance_list:
        logger.info("No instances to stop.")
        return {
            'statusCode': 200,
            'body': "No instances found to stop."
        }

    for instance in instance_list:
        try:
            instance.stop()
            stopped_instances_ids.append(instance.id)
            logger.info(f"Successfully initiated stop for instance: {instance.id}")
        except Exception as e:
            logger.error(f"Error stopping instance {instance.id}: {str(e)}")
            failed_to_stop_ids.append(instance.id)

    summary_message_parts = []
    if stopped_instances_ids:
        summary_message_parts.append(f"Successfully initiated stop for {len(stopped_instances_ids)} instances: {', '.join(stopped_instances_ids)}")
    if failed_to_stop_ids:
        summary_message_parts.append(f"Failed to initiate stop for {len(failed_to_stop_ids)} instances: {', '.join(failed_to_stop_ids)}")

    response_body = ". ".join(summary_message_parts)
    if not response_body:
        response_body = "No action taken on instances."


    if failed_to_stop_ids:
        return {
            'statusCode': 207, # Multi-Status
            'body': response_body
        }
    
    return {
        'statusCode': 200,
        'body': response_body
    }
