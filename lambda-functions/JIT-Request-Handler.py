import json
import boto3
import os
import time
import uuid
from datetime import datetime, timedelta
import datetime as dt
from botocore.exceptions import ClientError
from decimal import Decimal

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

# Permission Set Mapping
PERMISSION_SETS = {
    'S3FullAccess': {
        'arn': os.environ['PS_S3_FULL_ACCESS'],
        'risk_level': 'LOW',
        'name': 'JIT-S3FullAccess'
    },
    'EC2FullAccess': {
        'arn': os.environ['PS_EC2_FULL_ACCESS'],
        'risk_level': 'LOW',
        'name': 'JIT-EC2FullAccess'
    },
    'EmergencyAdmin': {
        'arn': os.environ['PS_EMERGENCY_ADMIN'],
        'risk_level': 'HIGH',
        'name': 'JIT-EmergencyAdmin'
    }
}

# Account Mapping
ACCOUNTS = {
    'Management': os.environ['MANAGEMENT_ACCOUNT'],
    'LogArchive': os.environ['LOG_ARCHIVE_ACCOUNT'],
    'Audit': os.environ['AUDIT_ACCOUNT']
}

table = dynamodb.Table(TABLE_NAME)

def lambda_handler(event, context):
    """
    Main handler for JIT access requests
    Supports both API Gateway and direct invocation
    """
    
    try:
        # Check if this is an API Gateway request
        if 'body' in event and 'httpMethod' in event:
            # API Gateway request
            http_method = event['httpMethod']
            
            if http_method == 'POST':
                # Parse the JSON body
                body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
                user_email = body.get('user_email')
                account_name = body.get('account_name')
                permission_set_name = body.get('permission_set')
                reason = body.get('reason')
                duration_minutes = body.get('duration_minutes', 60)
                
            elif http_method == 'GET':
                # List all requests
                response = table.scan()
                requests_list = response.get('Items', [])
                
                # Convert Decimal to regular numbers for JSON
                import decimal
                def decimal_default(obj):
                    if isinstance(obj, decimal.Decimal):
                        return int(obj) if obj % 1 == 0 else float(obj)
                    raise TypeError
                
                requests_json = json.loads(json.dumps(requests_list, default=decimal_default))
                
                return api_response(200, {
                    'requests': requests_json,
                    'count': len(requests_json)
                })
            else:
                return api_response(405, {'error': 'Method not allowed'})
        else:
            # Direct invocation (for testing)
            user_email = event.get('user_email')
            account_name = event.get('account_name')
            permission_set_name = event.get('permission_set')
            reason = event.get('reason')
            duration_minutes = event.get('duration_minutes', 60)
        
        # Validation
        if not all([user_email, account_name, permission_set_name, reason]):
            return api_response(400, {'error': 'Missing required fields: user_email, account_name, permission_set, reason'})
        
        if account_name not in ACCOUNTS:
            return api_response(400, {'error': f'Invalid account. Must be one of: {list(ACCOUNTS.keys())}'})
        
        if permission_set_name not in PERMISSION_SETS:
            return api_response(400, {'error': f'Invalid permission set. Must be one of: {list(PERMISSION_SETS.keys())}'})
        
        if duration_minutes > 60:
            return api_response(400, {'error': 'Duration cannot exceed 60 minutes'})
        
        # Get account ID and permission set details
        account_id = ACCOUNTS[account_name]
        permission_set = PERMISSION_SETS[permission_set_name]
        risk_level = permission_set['risk_level']
        
        # Get user details from Identity Center
        user_info = get_user_by_email(user_email)
        if not user_info:
            return api_response(404, {'error': f'User {user_email} not found in Identity Center'})
        
        user_id = user_info['UserId']
        
        # Generate request ID
        request_id = str(uuid.uuid4())
        current_timestamp = int(time.time())
        expiration_timestamp = current_timestamp + (duration_minutes * 60)
        
        # Create request record
        request_item = {
            'RequestId': request_id,
            'UserId': user_id,
            'UserEmail': user_email,
            'AccountId': account_id,
            'AccountName': account_name,
            'PermissionSet': permission_set['name'],
            'PermissionSetArn': permission_set['arn'],
            'RiskLevel': risk_level,
            'Status': 'PENDING',
            'RequestTimestamp': current_timestamp,
            'ExpirationTimestamp': expiration_timestamp,
            'DurationMinutes': duration_minutes,
            'Reason': reason
        }
        
        # Store request in DynamoDB
        table.put_item(Item=request_item)
        
        print(f"Request created: {request_id} for user {user_email}")
        
        # Determine if auto-approval or manual approval needed
        if risk_level == 'LOW':
            # Auto-approve and grant access immediately
            result = grant_access(request_id, user_id, account_id, permission_set['arn'], expiration_timestamp)

            # Send confirmation email
            email_subject = f"✓ JIT Access Granted - {permission_set_name}"
            email_body = f"""
Your JIT access request has been APPROVED and access is now ACTIVE.

Account: {account_name}
Permission Set: {permission_set_name}
Expires: {datetime.fromtimestamp(expiration_timestamp).strftime('%Y-%m-%d %H:%M:%S UTC')}
Duration: {duration_minutes} minutes

Your access will be automatically revoked after {duration_minutes} minutes.

Request ID: {request_id}
"""
            send_user_notification(user_email, email_subject, email_body)
            
            return api_response(200, {
                'message': 'Access granted automatically (low risk)',
                'request_id': request_id,
                'status': 'ACTIVE',
                'expires_at': datetime.fromtimestamp(expiration_timestamp).isoformat(),
                'account': account_name,
                'permission_set': permission_set_name
            })
        else:
            # High risk - requires approval
            send_approval_notification(request_id, user_email, account_name, permission_set_name, reason)
            
            return api_response(202, {
                'message': 'Access request pending approval (high risk)',
                'request_id': request_id,
                'status': 'PENDING',
                'account': account_name,
                'permission_set': permission_set_name,
                'note': 'Manager approval required. You will be notified when approved.'
            })
    
    except Exception as e:
        print(f"Error processing request: {str(e)}")
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
            'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
        },
        'body': json.dumps(body)
    }


def get_user_by_email(email_or_username):
    """Get user ID from Identity Center by email or username"""
    try:
        # List all users
        response = identitystore.list_users(
            IdentityStoreId=IDENTITY_STORE_ID
        )
        
        # Search through users for matching email or username
        for user in response.get('Users', []):
            # Check if email matches
            user_emails = user.get('Emails', [])
            for email_obj in user_emails:
                if email_obj.get('Value', '').lower() == email_or_username.lower():
                    return user
            
            # Check if username matches
            if user.get('UserName', '').lower() == email_or_username.lower():
                return user
        
        # Pagination if needed
        while response.get('NextToken'):
            response = identitystore.list_users(
                IdentityStoreId=IDENTITY_STORE_ID,
                NextToken=response['NextToken']
            )
            
            for user in response.get('Users', []):
                user_emails = user.get('Emails', [])
                for email_obj in user_emails:
                    if email_obj.get('Value', '').lower() == email_or_username.lower():
                        return user
                
                if user.get('UserName', '').lower() == email_or_username.lower():
                    return user
        
        return None
        
    except Exception as e:
        print(f"Error fetching user: {str(e)}")
        return None


def grant_access(request_id, user_id, account_id, permission_set_arn, expiration_timestamp):
    """Grant access by creating account assignment with status polling"""
    try:
        print(f"Creating account assignment for user {user_id} on account {account_id}")
        print(f"Permission set: {permission_set_arn}")
        
        # Create account assignment in Identity Center
        response = sso_admin.create_account_assignment(
            InstanceArn=INSTANCE_ARN,
            TargetId=account_id,
            TargetType='AWS_ACCOUNT',
            PermissionSetArn=permission_set_arn,
            PrincipalType='USER',
            PrincipalId=user_id
        )
        
        assignment_request_id = response['AccountAssignmentCreationStatus']['RequestId']
        assignment_status = response['AccountAssignmentCreationStatus']['Status']
        
        print(f"✓ Account assignment request created: {assignment_request_id}")
        print(f"✓ Initial status: {assignment_status}")
        
        # Poll for completion
        max_attempts = 30  # 60 seconds max
        attempt = 0
        
        while attempt < max_attempts:
            try:
                status_response = sso_admin.describe_account_assignment_creation_status(
                    InstanceArn=INSTANCE_ARN,
                    AccountAssignmentCreationRequestId=assignment_request_id
                )
                
                status = status_response['AccountAssignmentCreationStatus']['Status']
                print(f"✓ Assignment status check {attempt + 1}/{max_attempts}: {status}")
                
                if status == 'SUCCEEDED':
                    print(f"✓✓✓ Account assignment SUCCEEDED!")
                    break
                elif status == 'FAILED':
                    failure_reason = status_response['AccountAssignmentCreationStatus'].get('FailureReason', 'Unknown')
                    error_msg = f"Account assignment FAILED: {failure_reason}"
                    print(f"✗✗✗ {error_msg}")
                    raise Exception(error_msg)
                elif status in ['IN_PROGRESS']:
                    time.sleep(2)
                    attempt += 1
                else:
                    print(f"Unknown status: {status}, continuing...")
                    break
                    
            except ClientError as e:
                print(f"Error checking status: {str(e)}")
                break
        
        if attempt >= max_attempts:
            print(f"⚠ Warning: Status check timed out after {max_attempts} attempts")
        
        # Update DynamoDB record
        current_timestamp = int(time.time())
        table.update_item(
            Key={'RequestId': request_id},
            UpdateExpression='SET #status = :status, GrantedTimestamp = :granted, ApprovalTimestamp = :approved, AssignmentRequestId = :assign_req_id',
            ExpressionAttributeNames={
                '#status': 'Status'
            },
            ExpressionAttributeValues={
                ':status': 'ACTIVE',
                ':granted': current_timestamp,
                ':approved': current_timestamp,
                ':assign_req_id': assignment_request_id
            }
        )
        
        print(f"✓ DynamoDB updated with ACTIVE status")
        
        # Schedule auto-revocation
        schedule_revocation(request_id, user_id, account_id, permission_set_arn, expiration_timestamp)
        
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_msg = e.response['Error']['Message']
        print(f"✗ ClientError: {error_code} - {error_msg}")
        
        if error_code == 'ConflictException':
            print(f"⚠ Assignment already exists, treating as success")
            current_timestamp = int(time.time())
            table.update_item(
                Key={'RequestId': request_id},
                UpdateExpression='SET #status = :status, GrantedTimestamp = :granted',
                ExpressionAttributeNames={'#status': 'Status'},
                ExpressionAttributeValues={':status': 'ACTIVE', ':granted': current_timestamp}
            )
            return True
        else:
            raise
    except Exception as e:
        print(f"✗ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


def schedule_revocation(request_id, user_id, account_id, permission_set_arn, expiration_timestamp):
    """Schedule automatic revocation using EventBridge Rule (cron-based)"""
    try:
        # Convert Decimal to int if needed
        if isinstance(expiration_timestamp, Decimal):
            expiration_timestamp = int(expiration_timestamp)
        
        if isinstance(expiration_timestamp, str):
            expiration_timestamp = int(float(expiration_timestamp))
        
        schedule_time = datetime.fromtimestamp(expiration_timestamp, tz=dt.timezone.utc)
        
        # EventBridge uses cron expressions - create a one-time rule
        rule_name = f"revoke-{request_id}"
        
        # Cron format: minute hour day month day-of-week year
        cron_expression = f"cron({schedule_time.minute} {schedule_time.hour} {schedule_time.day} {schedule_time.month} ? {schedule_time.year})"
        
        print(f"Scheduling revocation: {rule_name} with cron: {cron_expression}")
        
        events = boto3.client('events')
        
        # Create EventBridge rule
        events.put_rule(
            Name=rule_name,
            ScheduleExpression=cron_expression,
            State='ENABLED',
            Description=f'Auto-revoke JIT access for request {request_id}'
        )
        
        # Add Lambda as target
        events.put_targets(
            Rule=rule_name,
            Targets=[
                {
                    'Id': '1',
                    'Arn': f'arn:aws:lambda:{REGION}:533267321107:function:JIT-Revoke-Access',
                    'Input': json.dumps({
                        'request_id': request_id,
                        'user_id': user_id,
                        'account_id': account_id,
                        'permission_set_arn': permission_set_arn
                    })
                }
            ]
        )
        
        print(f"✓ Revocation scheduled successfully using EventBridge Rule")
        
        # Update DynamoDB
        table.update_item(
            Key={'RequestId': request_id},
            UpdateExpression='SET RevocationScheduleArn = :arn',
            ExpressionAttributeValues={
                ':arn': f'arn:aws:events:{REGION}:533267321107:rule/{rule_name}'
            }
        )
        
    except Exception as e:
        print(f"⚠ Error scheduling revocation: {str(e)}")
        import traceback
        traceback.print_exc()


def send_approval_notification(request_id, user_email, account_name, permission_set, reason):
    """Send SNS notification for approval request"""
    try:
        sns = boto3.client('sns')
        topic_arn = os.environ.get('SNS_APPROVAL_TOPIC_ARN')
        
        if not topic_arn:
            print("SNS_APPROVAL_TOPIC_ARN not configured, skipping notification")
            return
        
        message = f"""
JIT Access Approval Required

Request ID: {request_id}
User: {user_email}
Account: {account_name}
Permission Set: {permission_set}
Reason: {reason}

This is a HIGH RISK access request requiring approval.
        """
        
        sns.publish(
            TopicArn=topic_arn,
            Subject=f'JIT Access Approval Required - {user_email}',
            Message=message
        )
        
        print(f"✓ Approval notification sent")
        
    except Exception as e:
        print(f"⚠ Error sending notification: {str(e)}")


def error_response(message):
    """Return standardized error response"""
    return {
        'statusCode': 400,
        'body': json.dumps({
            'error': message
        })
    }
