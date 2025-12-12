import json
import boto3
import os
import time
import uuid
from datetime import datetime
from decimal import Decimal
from botocore.exceptions import ClientError

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
sso_admin = boto3.client('sso-admin')
identitystore = boto3.client('identitystore')
scheduler = boto3.client('scheduler')

# Environment variables
TABLE_NAME = os.environ['DYNAMODB_TABLE']
INSTANCE_ARN = os.environ['IDENTITY_CENTER_INSTANCE_ARN']
IDENTITY_STORE_ID = os.environ['IDENTITY_STORE_ID']
REGION = os.environ['REGION']

table = dynamodb.Table(TABLE_NAME)

def lambda_handler(event, context):
    """
    Handle approval or denial of JIT access requests
    Supports both API Gateway and direct invocation
    """
    
    try:
        # Check if this is an API Gateway request
        if 'body' in event and 'httpMethod' in event:
            # API Gateway request - parse JSON body
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
            request_id = body.get('request_id')
            action = body.get('action', '').upper()
            approver_email = body.get('approver_email')
            comments = body.get('comments', '')
        else:
            # Direct invocation
            request_id = event.get('request_id')
            action = event.get('action', '').upper()
            approver_email = event.get('approver_email')
            comments = event.get('comments', '')
        
        print(f"Approval handler triggered: request_id={request_id}, action={action}")
        
        # Validation
        if not request_id:
            return api_response(400, {'error': 'Missing request_id'})
        
        if action not in ['APPROVE', 'DENY']:
            return api_response(400, {'error': 'Action must be APPROVE or DENY'})
        
        if not approver_email:
            return api_response(400, {'error': 'Missing approver_email'})
        
        # Get request details from DynamoDB
        response = table.get_item(Key={'RequestId': request_id})
        
        if 'Item' not in response:
            return api_response(404, {'error': f'Request {request_id} not found'})
        
        request_item = response['Item']
        current_status = request_item.get('Status')
        
        # Verify request is in PENDING status
        if current_status != 'PENDING':
            return api_response(400, {'error': f'Request is not pending. Current status: {current_status}'})
        
        current_timestamp = int(time.time())
        
        if action == 'DENY':
            # Update status to DENIED
            table.update_item(
                Key={'RequestId': request_id},
                UpdateExpression='SET #status = :status, ApproverEmail = :approver, ApprovalTimestamp = :timestamp, ApprovalComments = :comments',
                ExpressionAttributeNames={
                    '#status': 'Status'
                },
                ExpressionAttributeValues={
                    ':status': 'DENIED',
                    ':approver': approver_email,
                    ':timestamp': current_timestamp,
                    ':comments': comments
                }
            )
            
            print(f"Request {request_id} denied by {approver_email}")

            # Send denial email
            email_subject = f"✗ JIT Access Request DENIED"
            email_body = f"""
Your JIT access request has been DENIED.

Account: {request_item.get('AccountName')}
Permission Set: {request_item.get('PermissionSet')}
Approver: {approver_email}
Reason: {comments}

Request ID: {request_id}
"""
            send_user_notification(request_item.get('UserEmail'), email_subject, email_body)
            
            return api_response(200, {
                'message': 'Request denied',
                'request_id': request_id,
                'status': 'DENIED',
                'approver': approver_email,
                'user_email': request_item.get('UserEmail'),
                'account': request_item.get('AccountName'),
                'permission_set': request_item.get('PermissionSet')
            })
        
        else:  # APPROVE
            # Extract request details
            user_id = request_item.get('UserId')
            account_id = request_item.get('AccountId')
            permission_set_arn = request_item.get('PermissionSetArn')
            expiration_timestamp = int(request_item.get('ExpirationTimestamp'))
            
            # Grant access
            print(f"Granting access for request {request_id}")
            
            try:
                # Create account assignment in Identity Center
                sso_response = sso_admin.create_account_assignment(
                    InstanceArn=INSTANCE_ARN,
                    TargetId=account_id,
                    TargetType='AWS_ACCOUNT',
                    PermissionSetArn=permission_set_arn,
                    PrincipalType='USER',
                    PrincipalId=user_id
                )
                
                assignment_status = sso_response['AccountAssignmentCreationStatus']['Status']
                print(f"Account assignment initiated: {assignment_status}")
                
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code == 'ConflictException':
                    print(f"Assignment already exists")
                else:
                    raise
            
            # Update DynamoDB record
            table.update_item(
                Key={'RequestId': request_id},
                UpdateExpression='SET #status = :status, ApproverEmail = :approver, ApprovalTimestamp = :approval_ts, GrantedTimestamp = :granted_ts, ApprovalComments = :comments',
                ExpressionAttributeNames={
                    '#status': 'Status'
                },
                ExpressionAttributeValues={
                    ':status': 'ACTIVE',
                    ':approver': approver_email,
                    ':approval_ts': current_timestamp,
                    ':granted_ts': current_timestamp,
                    ':comments': comments
                }
            )
            
            # Schedule auto-revocation
            schedule_revocation(request_id, user_id, account_id, permission_set_arn, expiration_timestamp)
            
            print(f"Request {request_id} approved by {approver_email}")

            # Send approval email
            email_subject = f"✓ JIT Access Request APPROVED"
            email_body = f"""
Your JIT access request has been APPROVED and access is now ACTIVE.

Account: {request_item.get('AccountName')}
Permission Set: {request_item.get('PermissionSet')}
Approver: {approver_email}
Comments: {comments}
Expires: {datetime.fromtimestamp(expiration_timestamp).strftime('%Y-%m-%d %H:%M:%S UTC')}

Your access will be automatically revoked at the expiration time.

Request ID: {request_id}
"""
            send_user_notification(request_item.get('UserEmail'), email_subject, email_body)
            
            return api_response(200, {
                'message': 'Request approved and access granted',
                'request_id': request_id,
                'status': 'ACTIVE',
                'approver': approver_email,
                'user_email': request_item.get('UserEmail'),
                'account': request_item.get('AccountName'),
                'permission_set': request_item.get('PermissionSet'),
                'expires_at': datetime.fromtimestamp(expiration_timestamp).isoformat()
            })
    
    except Exception as e:
        print(f"Error processing approval: {str(e)}")
        import traceback
        traceback.print_exc()
        return api_response(500, {'error': f'Internal error: {str(e)}'})

def send_user_notification(user_email, subject, message):
    """Send email notification to user via SES"""
    try:
        ses = boto3.client('ses', region_name=REGION)
        
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


def schedule_revocation(request_id, user_id, account_id, permission_set_arn, expiration_timestamp):
    """Schedule automatic revocation using EventBridge Scheduler"""
    try:
        schedule_name = f"revoke-{request_id}"
        schedule_time = datetime.fromtimestamp(expiration_timestamp)
        
        # Create EventBridge schedule to invoke revocation Lambda
        scheduler.create_schedule(
            Name=schedule_name,
            GroupName='default',
            ScheduleExpression=f"at({schedule_time.strftime('%Y-%m-%dT%H:%M:%S')})",
            ScheduleExpressionTimezone='UTC',
            FlexibleTimeWindow={'Mode': 'OFF'},
            Target={
                'Arn': f'arn:aws:lambda:{REGION}:533267321107:function:JIT-Revoke-Access',
                'RoleArn': f'arn:aws:iam::533267321107:role/JIT-Automation-Role',
                'Input': json.dumps({
                    'request_id': request_id,
                    'user_id': user_id,
                    'account_id': account_id,
                    'permission_set_arn': permission_set_arn
                })
            },
            State='ENABLED'
        )
        
        print(f"Revocation scheduled: {schedule_name} at {schedule_time}")
        
        # Update DynamoDB with schedule ARN
        table.update_item(
            Key={'RequestId': request_id},
            UpdateExpression='SET RevocationScheduleArn = :arn',
            ExpressionAttributeValues={
                ':arn': f'arn:aws:scheduler:{REGION}:533267321107:schedule/default/{schedule_name}'
            }
        )
        
    except Exception as e:
        print(f"Error scheduling revocation: {str(e)}")
        # Non-fatal - access can still be manually revoked


def error_response(message):
    """Return standardized error response"""
    return {
        'statusCode': 400,
        'body': json.dumps({
            'error': message
        })
    }
