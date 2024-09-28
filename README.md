# EC2 Dev Instance Scheduler

This project automatically stops EC2 instances tagged with "Dev" at a specified time each day to reduce costs associated with unused development resources.

## Setup and Deployment

1. Clone the repository:

   ```
   git clone https://github.com/yesaswi/ec2-dev-instance-scheduler.git
   cd ec2-dev-instance-scheduler
   ```

2. Create a virtual environment and install dependencies:

   ```
   python -m venv .venv
   source .venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   pip install -r requirements.txt
   ```

3. Set up AWS CLI and configure your credentials:

   ```
   aws configure
   ```

4. Create the IAM role for the Lambda function:

   ```
   aws iam create-role --role-name EC2DevInstanceSchedulerRole --assume-role-policy-document file://iam/lambda_role_policy.json
   ```

5. Create the Lambda function:

   ```
   zip -j deployment.zip src/lambda_function.py
   aws lambda create-function --function-name EC2DevInstanceScheduler --runtime python3.11 --role arn:aws:iam::ACCOUNT_ID:role/EC2DevInstanceSchedulerRole --handler lambda_function.lambda_handler --zip-file fileb://deployment.zip
   ```

6. Create the EventBridge rule:

   ```
   aws events put-rule --cli-input-json file://eventbridge/schedule_rule.json
   ```

7. Add permission for EventBridge to invoke the Lambda function:
   ```
   aws lambda add-permission --function-name EC2DevInstanceScheduler --statement-id EventBridgeInvoke --action lambda:InvokeFunction --principal events.amazonaws.com --source-arn arn:aws:events:REGION:ACCOUNT_ID:rule/EC2DevInstanceScheduler
   ```

## Testing

1. Run unit tests:

   ```
   pytest tests/
   ```

2. For manual testing, you can invoke the Lambda function directly:

   ```
   aws lambda invoke --function-name EC2DevInstanceScheduler output.txt
   ```

3. Check the CloudWatch Logs for the Lambda function to verify its execution and results.

## Monitoring and Maintenance

- Review CloudWatch Logs for the Lambda function regularly.
- Check CloudTrail for API call history related to EC2 instance stops.
- Periodically review the list of stopped instances and validate cost savings.

## Security Considerations

- The IAM role follows the principle of least privilege.
- The Lambda function is restricted to specific EC2 actions.
- All activities are logged in CloudWatch Logs for auditing purposes.

## Future Enhancements

- Add support for multiple tags or regions.
- Implement a start-up scheduler for morning hours.
- Create SNS notifications for stopped instances.
