import json
import boto3
import os
import time
from botocore.exceptions import ClientError

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
sso_admin = boto3.client('sso-admin')
scheduler = boto3.client('scheduler')

# Environment variables
TABLE_NAME = os.environ['DYNAMODB_TABLE']
INSTANCE_ARN = os.environ['IDENTITY_CENTER_INSTANCE_ARN']
REGION = os.environ['REGION']

table = dynamodb.Table(TABLE_NAME)

def lambda_handler(event, context):
    """
    Revoke JIT access by deleting Identity Center account assignment
    Expected event format (from EventBridge Scheduler):
    {
        "request_id": "uuid",
        "user_id": "user-id-from-identity-center",
        "account_id": "123456789012",
        "permission_set_arn": "arn:aws:sso:::permissionSet/..."
    }
    """
    
    try:
        print(f"Revocation triggered: {json.dumps(event)}")
        
        # Extract parameters
        request_id = event.get('request_id')
        user_id = event.get('user_id')
        account_id = event.get('account_id')
        permission_set_arn = event.get('permission_set_arn')
        
        # Validation
        if not all([request_id, user_id, account_id, permission_set_arn]):
            return error_response('Missing required parameters')
        
        # Get request details from DynamoDB
        response = table.get_item(Key={'RequestId': request_id})
        
        if 'Item' not in response:
            return error_response(f'Request {request_id} not found')
        
        request_item = response['Item']
        current_status = request_item.get('Status')
        
        # Only revoke if access is currently active
        if current_status != 'ACTIVE':
            print(f"Request {request_id} status is {current_status}, skipping revocation")
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': f'No revocation needed, status is {current_status}',
                    'request_id': request_id
                })
            }
        
        # Delete account assignment in Identity Center
        print(f"Revoking access for user {user_id} on account {account_id}")
        
        try:
            response = sso_admin.delete_account_assignment(
                InstanceArn=INSTANCE_ARN,
                TargetId=account_id,
                TargetType='AWS_ACCOUNT',
                PermissionSetArn=permission_set_arn,
                PrincipalType='USER',
                PrincipalId=user_id
            )
            
            deletion_status = response['AccountAssignmentDeletionStatus']['Status']
            print(f"Account assignment deletion initiated: {deletion_status}")
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ResourceNotFoundException':
                print(f"Assignment already deleted for user {user_id}")
            else:
                raise
        
        # Update DynamoDB record
        current_timestamp = int(time.time())
        table.update_item(
            Key={'RequestId': request_id},
            UpdateExpression='SET #status = :status, RevokedTimestamp = :revoked',
            ExpressionAttributeNames={
                '#status': 'Status'
            },
            ExpressionAttributeValues={
                ':status': 'REVOKED',
                ':revoked': current_timestamp
            }
        )

        # Update DynamoDB record
        current_timestamp = int(time.time())
        table.update_item(
            Key={'RequestId': request_id},
            UpdateExpression='SET #status = :status, RevokedTimestamp = :revoked',
            ExpressionAttributeNames={
                '#status': 'Status'
            },
            ExpressionAttributeValues={
                ':status': 'REVOKED',
                ':revoked': current_timestamp
            }
        )
        
        # Send revocation email
        email_subject = f"⏱ JIT Access REVOKED - {request_item.get('PermissionSet')}"
        email_body = f"""
Your JIT access has been automatically REVOKED as the time limit has expired.

Account: {request_item.get('AccountName')}
Permission Set: {request_item.get('PermissionSet')}
Access Duration: {request_item.get('DurationMinutes')} minutes

If you still need access, please submit a new request through the JIT Access Portal.

Request ID: {request_id}
"""
        send_user_notification(request_item.get('UserEmail'), email_subject, email_body)
        
        # Clean up EventBridge schedule
        schedule_arn = request_item.get('RevocationScheduleArn')
        if schedule_arn:
            schedule_name = schedule_arn.split('/')[-1]
            try:
                scheduler.delete_schedule(
                    Name=schedule_name,
                    GroupName='default'
                )
                print(f"Deleted schedule: {schedule_name}")
            except Exception as e:
                print(f"Error deleting schedule: {str(e)}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Access successfully revoked',
                'request_id': request_id,
                'user_email': request_item.get('UserEmail'),
                'account': request_item.get('AccountName'),
                'permission_set': request_item.get('PermissionSet'),
                'revoked_at': current_timestamp
            })
        }
        
    except Exception as e:
        print(f"Error revoking access: {str(e)}")
        
        # Update DynamoDB to mark as error
        try:
            table.update_item(
                Key={'RequestId': request_id},
                UpdateExpression='SET #status = :status, ErrorMessage = :error',
                ExpressionAttributeNames={
                    '#status': 'Status'
                },
                ExpressionAttributeValues={
                    ':status': 'ERROR',
                    ':error': str(e)
                }
            )
        except:
            pass
        
        return error_response(f'Revocation failed: {str(e)}')

        # Send revocation email
        email_subject = f"⏱ JIT Access REVOKED - {request_item.get('PermissionSet')}"
        email_body = f"""
Your JIT access has been automatically REVOKED as the time limit has expired.

Account: {request_item.get('AccountName')}
Permission Set: {request_item.get('PermissionSet')}
Access Duration: {request_item.get('DurationMinutes')} minutes

If you still need access, please submit a new request through the JIT Access Portal.

Request ID: {request_id}
"""
        send_user_notification(request_item.get('UserEmail'), email_subject, email_body)


def send_user_notification(user_email, subject, message):
    """Send email notification to user via SES"""
    try:
        ses = boto3.client('ses', region_name='us-east-1')
        
        ses.send_email(
            Source='felixayo85@gmail.com',  # Must be a verified email in SES
            Destination={
                'ToAddresses': [user_email]
            },
            Message={
                'Subject': {
                    'Data': subject,
                    'Charset': 'UTF-8'
                },
                'Body': {
                    'Text': {
                        'Data': message,
                        'Charset': 'UTF-8'
                    }
                }
            }
        )
        
        print(f"✓ Email sent to {user_email}: {subject}")
        
    except Exception as e:
        print(f"⚠ Error sending email: {str(e)}")        


def error_response(message):
    """Return standardized error response"""
    return {
        'statusCode': 400,
        'body': json.dumps({
            'error': message
        })
    }
