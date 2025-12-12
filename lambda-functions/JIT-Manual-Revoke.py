import json
import boto3
import os
import time
from botocore.exceptions import ClientError

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
sso_admin = boto3.client('sso-admin')
scheduler = boto3.client('scheduler')
events = boto3.client('events')

# Environment variables
TABLE_NAME = os.environ['DYNAMODB_TABLE']
INSTANCE_ARN = os.environ['IDENTITY_CENTER_INSTANCE_ARN']
REGION = os.environ['REGION']

table = dynamodb.Table(TABLE_NAME)

def lambda_handler(event, context):
    """
    Manually revoke JIT access before expiration
    """
    
    try:
        # Check if this is an API Gateway request
        if 'body' in event and 'httpMethod' in event:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
            request_id = body.get('request_id')
            revoker_email = body.get('revoker_email')
        else:
            request_id = event.get('request_id')
            revoker_email = event.get('revoker_email', 'Manual')
        
        print(f"Manual revocation triggered for request: {request_id}")
        
        if not request_id:
            return api_response(400, {'error': 'Missing request_id'})
        
        # Get request details from DynamoDB
        response = table.get_item(Key={'RequestId': request_id})
        
        if 'Item' not in response:
            return api_response(404, {'error': f'Request {request_id} not found'})
        
        request_item = response['Item']
        current_status = request_item.get('Status')
        
        # Only revoke if access is currently active
        if current_status != 'ACTIVE':
            return api_response(400, {'error': f'Cannot revoke. Current status: {current_status}'})
        
        user_id = request_item.get('UserId')
        account_id = request_item.get('AccountId')
        permission_set_arn = request_item.get('PermissionSetArn')
        
        # Delete account assignment in Identity Center
        print(f"Revoking access for user {user_id} on account {account_id}")
        
        try:
            sso_response = sso_admin.delete_account_assignment(
                InstanceArn=INSTANCE_ARN,
                TargetId=account_id,
                TargetType='AWS_ACCOUNT',
                PermissionSetArn=permission_set_arn,
                PrincipalType='USER',
                PrincipalId=user_id
            )
            
            deletion_status = sso_response['AccountAssignmentDeletionStatus']['Status']
            print(f"Account assignment deletion initiated: {deletion_status}")
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ResourceNotFoundException':
                print(f"Assignment already deleted")
            else:
                raise
        
        # Update DynamoDB record
        current_timestamp = int(time.time())
        table.update_item(
            Key={'RequestId': request_id},
            UpdateExpression='SET #status = :status, RevokedTimestamp = :revoked, RevokedBy = :revoker, RevocationType = :type',
            ExpressionAttributeNames={
                '#status': 'Status'
            },
            ExpressionAttributeValues={
                ':status': 'REVOKED',
                ':revoked': current_timestamp,
                ':revoker': revoker_email,
                ':type': 'MANUAL'
            }
        )
        
        # Send revocation email
        email_subject = f"⏱ JIT Access REVOKED (Manual)"
        email_body = f"""
Your JIT access has been MANUALLY REVOKED.

Account: {request_item.get('AccountName')}
Permission Set: {request_item.get('PermissionSet')}
Revoked by: {revoker_email}

If you still need access, please submit a new request through the JIT Access Portal.

Request ID: {request_id}
"""
        send_user_notification(request_item.get('UserEmail'), email_subject, email_body)
        
        # Cancel the automatic revocation schedule
        schedule_arn = request_item.get('RevocationScheduleArn')
        if schedule_arn:
            try:
                if 'scheduler' in schedule_arn:
                    # EventBridge Scheduler
                    schedule_name = schedule_arn.split('/')[-1]
                    scheduler.delete_schedule(
                        Name=schedule_name,
                        GroupName='default'
                    )
                    print(f"Deleted scheduler: {schedule_name}")
                elif 'rule' in schedule_arn:
                    # EventBridge Rule
                    rule_name = schedule_arn.split('/')[-1]
                    events.remove_targets(Rule=rule_name, Ids=['1'])
                    events.delete_rule(Name=rule_name)
                    print(f"Deleted rule: {rule_name}")
            except Exception as e:
                print(f"Error deleting schedule: {str(e)}")
        
        return api_response(200, {
            'message': 'Access successfully revoked',
            'request_id': request_id,
            'user_email': request_item.get('UserEmail'),
            'account': request_item.get('AccountName'),
            'permission_set': request_item.get('PermissionSet'),
            'revoked_by': revoker_email
        })
        
    except Exception as e:
        print(f"Error revoking access: {str(e)}")
        import traceback
        traceback.print_exc()
        return api_response(500, {'error': f'Internal error: {str(e)}'})


def send_user_notification(user_email, subject, message):
    """Send email notification to user via SES"""
    try:
        ses = boto3.client('ses', region_name=REGION)
        
        ses.send_email(
            Source='felixayo85@gmail.com',
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


def api_response(status_code, body):
    """Helper function to return API Gateway formatted response"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
            'Access-Control-Allow-Methods': 'POST,OPTIONS'
        },
        'body': json.dumps(body)
    }
