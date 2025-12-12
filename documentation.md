# Just-In-Time (JIT) AWS Access Management System

## Complete Documentation

**Version:** 1.0  
**Last Updated:** December 2025  
**Portal URL:** https://d72cs5opijkjl.cloudfront.net

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Components](#components)
4. [User Guide - Engineers](#user-guide-engineers)
5. [User Guide - Managers](#user-guide-managers)
6. [Administrator Guide](#administrator-guide)
7. [Security & Compliance](#security-compliance)
8. [Troubleshooting](#troubleshooting)
9. [API Reference](#api-reference)
10. [Maintenance & Operations](#maintenance-operations)

---

## System Overview

### Purpose

The Just-In-Time (JIT) Access Management System provides temporary, time-bound access to AWS resources with automated approval workflows and comprehensive audit trails. This system reduces security risks by eliminating standing privileged access while maintaining operational efficiency.

### Key Features

- ✅ **Automated Access Provisioning** - Low-risk requests auto-approved in seconds
- ✅ **Approval Workflows** - High-risk requests require manager approval
- ✅ **Time-Limited Access** - All access automatically expires (1 hour maximum)
- ✅ **Email Notifications** - Users notified of all access events
- ✅ **Role-Based Access Control** - Engineers and Managers have different permissions
- ✅ **Manual Revocation** - Access can be revoked before expiration
- ✅ **Full Audit Trail** - All requests logged with timestamps and approvers
- ✅ **HTTPS Web Portal** - Secure CloudFront distribution with Cognito authentication

### Access Types

| Permission Set | Risk Level | Approval Required | Auto-Revocation |
|---------------|------------|-------------------|-----------------|
| S3 Full Access | Low | No | 1 hour |
| EC2 Full Access | Low | No | 1 hour |
| Emergency Admin | High | Yes | 1 hour |

---

## Architecture

### System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Users                                    │
│  (Engineers, Managers)                                           │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│              CloudFront Distribution (HTTPS)                     │
│              https://d72cs5opijkjl.cloudfront.net               │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                  S3 Static Website                               │
│          (index.html - Web Portal)                               │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│              AWS Cognito User Pool                               │
│         (Authentication + Role-Based Access)                     │
│              Groups: Engineers, Managers                         │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                  API Gateway (REST API)                          │
│                                                                  │
│  Endpoints:                                                      │
│  POST /requests  - Submit access request                         │
│  GET  /requests  - List user's requests                          │
│  POST /approvals - Approve/deny requests                         │
│  POST /revoke    - Manual revocation                             │
└──────────────────────────┬──────────────────────────────────────┘
                           │
           ┌───────────────┼───────────────┬──────────────┐
           ▼               ▼               ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   Lambda     │ │   Lambda     │ │   Lambda     │ │   Lambda     │
│   Request    │ │   Approval   │ │   Revoke     │ │   Manual     │
│   Handler    │ │   Handler    │ │   Access     │ │   Revoke     │
└──────┬───────┘ └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
       │                │                │                │
       └────────────────┼────────────────┼────────────────┘
                        ▼                ▼
              ┌─────────────────────────────┐
              │    AWS Identity Center      │
              │  (Permission Set Assignment)│
              └─────────────────────────────┘
                        │
                        ▼
              ┌─────────────────────────────┐
              │    AWS Accounts             │
              │  - Management               │
              │  - Log Archive              │
              │  - Audit                    │
              └─────────────────────────────┘

Supporting Services:
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  DynamoDB    │ │ EventBridge  │ │     SNS      │ │     SES      │
│  (Audit Log) │ │  (Auto-      │ │  (Approval   │ │   (Email     │
│              │ │  Revocation) │ │  Notifications)│ │  Notifications)│
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
```

### Data Flow

#### Request Submission Flow
```
1. User logs in via Cognito
2. User submits access request via web portal
3. API Gateway validates JWT token
4. Lambda checks risk level:
   - Low Risk → Auto-approve → Grant access → Schedule revocation
   - High Risk → Send SNS notification → Pending approval
5. User receives email notification
6. Access logged in DynamoDB
```

#### Approval Flow (High-Risk Requests)
```
1. Manager receives email notification
2. Manager logs into portal
3. Manager views pending approvals
4. Manager clicks Approve/Deny
5. Lambda grants/denies access
6. User receives email notification
7. If approved: Access granted → Schedule auto-revocation
```

#### Auto-Revocation Flow
```
1. EventBridge Rule triggers at expiration time
2. Revoke Lambda invoked
3. Identity Center assignment deleted
4. DynamoDB updated
5. User receives revocation email
```

---

## Components

### Backend Infrastructure

#### 1. Lambda Functions

**JIT-Request-Handler**
- **Purpose:** Process access requests and auto-approve low-risk requests
- **Trigger:** API Gateway POST /requests
- **Runtime:** Python 3.12
- **Timeout:** 3 minutes
- **Memory:** 256 MB
- **Key Functions:**
  - Validate user input
  - Check permission set risk level
  - Auto-grant low-risk access
  - Create DynamoDB records
  - Send email notifications
  - Schedule auto-revocation

**JIT-Approval-Handler**
- **Purpose:** Process manager approvals/denials
- **Trigger:** API Gateway POST /approvals
- **Runtime:** Python 3.12
- **Timeout:** 2 minutes
- **Memory:** 256 MB
- **Key Functions:**
  - Validate approval requests
  - Grant/deny access
  - Update DynamoDB
  - Send email notifications
  - Schedule auto-revocation

**JIT-Revoke-Access**
- **Purpose:** Automatically revoke expired access
- **Trigger:** EventBridge Rules (scheduled)
- **Runtime:** Python 3.12
- **Timeout:** 2 minutes
- **Memory:** 256 MB
- **Key Functions:**
  - Delete Identity Center assignments
  - Update DynamoDB status
  - Send revocation emails
  - Clean up schedules

**JIT-Manual-Revoke**
- **Purpose:** Manually revoke active access
- **Trigger:** API Gateway POST /revoke
- **Runtime:** Python 3.12
- **Timeout:** 2 minutes
- **Memory:** 256 MB
- **Key Functions:**
  - Revoke access on-demand
  - Cancel auto-revocation schedule
  - Update DynamoDB
  - Send email notifications

#### 2. DynamoDB Table

**Table Name:** JIT-Access-Requests

**Primary Key:**
- Partition Key: RequestId (String)

**Attributes:**
- RequestId (String) - Unique request identifier
- UserId (String) - Identity Center user ID
- UserEmail (String) - User's email address
- AccountId (String) - AWS account ID
- AccountName (String) - Account display name
- PermissionSet (String) - Permission set name
- PermissionSetArn (String) - Full ARN
- RiskLevel (String) - LOW | HIGH
- Status (String) - PENDING | ACTIVE | DENIED | REVOKED
- RequestTimestamp (Number) - Unix timestamp
- ExpirationTimestamp (Number) - Unix timestamp
- GrantedTimestamp (Number) - Unix timestamp
- RevokedTimestamp (Number) - Unix timestamp
- ApprovalTimestamp (Number) - Unix timestamp
- ApproverEmail (String) - Manager email
- ApprovalComments (String) - Approval/denial reason
- RevokedBy (String) - Who revoked (for manual revocation)
- RevocationType (String) - AUTO | MANUAL
- Reason (String) - Business justification
- DurationMinutes (Number) - Access duration
- RevocationScheduleArn (String) - EventBridge schedule ARN

**Global Secondary Indexes:**
- UserId-RequestTimestamp-index
- Status-RequestTimestamp-index

**Point-in-Time Recovery:** Enabled  
**DynamoDB Streams:** Enabled

#### 3. API Gateway

**API Name:** JIT-Access-API  
**Type:** REST API  
**Stage:** prod  
**Endpoint:** https://jghpu14cya.execute-api.us-east-1.amazonaws.com/prod

**Resources:**
- `/requests` (POST, GET) - Submit and list requests
- `/approvals` (POST) - Approve/deny requests
- `/revoke` (POST) - Manual revocation

**Authorization:** AWS Cognito User Pool Authorizer

**CORS:** Enabled for all endpoints

#### 4. AWS Cognito

**User Pool ID:** us-east-1_K0m5bnDVE  
**App Client ID:** 7i4gmqqpr3267jpejbpbb6rjpe

**Groups:**
- **Engineers** - Can submit access requests
- **Managers** - Can approve high-risk requests + submit requests

**Authentication Flow:** USER_PASSWORD_AUTH

**Password Policy:**
- Minimum length: 8 characters
- Require uppercase, lowercase, numbers, special characters

#### 5. Amazon SES

**Verified Email:** felixayo85@gmail.com  
**Region:** us-east-1  
**Status:** Sandbox (requires verified recipients)

**Note:** For production, request SES production access to send to any email address.

#### 6. EventBridge Rules

**Purpose:** Schedule automatic access revocation

**Rule Naming:** `revoke-{RequestId}`  
**Schedule Type:** One-time (cron expression)  
**Target:** JIT-Revoke-Access Lambda

**Example:**
```
Rule: revoke-abc123-def456
Schedule: cron(30 15 6 12 ? 2025)
Target: arn:aws:lambda:us-east-1:533267321107:function:JIT-Revoke-Access
```

#### 7. CloudFront Distribution

**Domain:** d72cs5opijkjl.cloudfront.net  
**Origin:** jit-access-portal-cognito-interface.s3-website-us-east-1.amazonaws.com  
**Protocol:** HTTP Only (origin), HTTPS (viewer)  
**SSL Certificate:** CloudFront default certificate  
**Default Root Object:** index.html

#### 8. S3 Bucket

**Bucket Name:** jit-access-portal-cognito-interface  
**Region:** us-east-1  
**Static Website Hosting:** Enabled  
**Index Document:** index.html  
**Public Access:** Enabled (for CloudFront)

---

## User Guide - Engineers

### Getting Started

#### Accessing the Portal

1. Navigate to: https://d72cs5opijkjl.cloudfront.net
2. Enter your email address and password
3. Click "Sign In"

<img width="1053" height="551" alt="image" src="https://github.com/user-attachments/assets/54983769-9b35-4116-a835-333e21c15ac8" />


#### First-Time Login

If this is your first login:
1. You'll be prompted to set a new password
2. Create a password meeting the requirements:
   - At least 8 characters
   - Include uppercase and lowercase letters
   - Include numbers
   - Include special characters
3. Click confirm
4. You'll be automatically logged in

### Requesting Access

#### Step 1: Navigate to New Request Tab

After logging in, you'll see three tabs:
- **New Request** - Submit new access requests
- **My Requests** - View your request history
- **Pending Approvals** - (Managers only)

<img width="1017" height="860" alt="image" src="https://github.com/user-attachments/assets/9d9ddac1-ce60-4c2e-859c-821f80cc50a0" />


#### Step 2: Fill Out Request Form

1. **AWS Account** - Select the account you need access to:
   - Management (533267321107)
   - Log Archive (269423819609)
   - Audit (329668418788)

2. **Permission Set** - Choose the level of access:
   - **S3 Full Access** (Auto-approved)
   - **EC2 Full Access** (Auto-approved)
   - **Emergency Admin** (Requires Approval)

3. **Business Justification** - Explain why you need access:
   - Be specific and detailed
   - Reference ticket numbers if applicable
   - Example: "Need to investigate S3 bucket permissions issue for TICKET-1234"

4. **Duration** - Select how long you need access (5-60 minutes)
   - Default: 60 minutes
   - Access will be automatically revoked after this time

<img width="1017" height="860" alt="image" src="https://github.com/user-attachments/assets/9aae9e03-ff37-4a10-8995-8e9e84fb69f3" />

#### Step 3: Submit Request

Click "Submit Request" button.

**For Low-Risk Requests (S3, EC2):**
- ✅ Access granted immediately
- ✅ Email notification sent
- ✅ Access will be available within 1-2 minutes in AWS Identity Center

**For High-Risk Requests (Admin):**
- ⏳ Request sent to managers for approval
- ✅ Email notification sent to you
- ⏳ You'll receive another email when approved/denied

### Viewing Your Requests

Click the "My Requests" tab to see:
- All your past and current requests
- Request status (ACTIVE, PENDING, DENIED, REVOKED)
- When access was granted and when it expires
- Who approved (for high-risk requests)

![My Requests Tab - INSERT SCREENSHOT HERE]

**Status Meanings:**
- **ACTIVE** 🟢 - Access is currently granted
- **PENDING** 🟡 - Awaiting manager approval
- **DENIED** 🔴 - Request was denied
- **REVOKED** ⚫ - Access has been revoked

### Manually Revoking Access

If you no longer need access before it expires:

1. Go to "My Requests" tab
2. Find the ACTIVE request
3. Click "🚫 Revoke Now" button
4. Confirm the revocation
5. Access will be immediately revoked
6. You'll receive an email confirmation

![Revoke Button - INSERT SCREENSHOT HERE]

**Why revoke early?**
- Security best practice
- Reduces your attack surface
- Shows good security hygiene

### Using Your AWS Access

Once access is granted:

#### Via AWS Console:
1. Go to your AWS SSO login URL
2. Log in with your credentials
3. You'll see the granted account and role
4. Click to access the AWS Console

#### Via AWS CLI:
```bash
aws sso login --profile jit-access
aws s3 ls --profile jit-access
```

### Email Notifications

You'll receive emails for:
- ✅ Access granted (low-risk auto-approval)
- ⏳ Request pending approval (high-risk)
- ✅ Request approved by manager
- ❌ Request denied by manager
- ⏱️ Access automatically revoked (after expiration)
- 🚫 Access manually revoked

**Email Example:**
```
Subject: ✓ JIT Access Granted - S3FullAccess

Your JIT access request has been APPROVED and access is now ACTIVE.

Account: Management
Permission Set: JIT-S3FullAccess
Expires: 2025-12-06 15:30:00 UTC
Duration: 60 minutes

Your access will be automatically revoked after 60 minutes.

Request ID: abc123-def456-ghi789
```

### Best Practices

1. **Request Minimum Required Access**
   - Use S3/EC2 access when possible
   - Only request Admin for true emergencies

2. **Provide Clear Justification**
   - Reference ticket numbers
   - Explain the specific task
   - Include relevant context

3. **Revoke When Done**
   - Don't wait for auto-revocation
   - Manually revoke as soon as you're finished
   - Reduces security risk

4. **Plan Ahead**
   - Admin access requires approval
   - Allow time for manager review
   - Don't wait until last minute

---

## User Guide - Managers

### Manager Responsibilities

As a manager, you are responsible for:
- Reviewing and approving/denying high-risk access requests
- Ensuring requests have valid business justification
- Maintaining security while enabling operational efficiency

### Accessing the Approval Interface

1. Log in to: https://d72cs5opijkjl.cloudfront.net
2. You'll see an additional tab: **Pending Approvals**
3. Click the "Pending Approvals" tab

![Manager Dashboard - INSERT SCREENSHOT HERE]

### Reviewing Pending Requests

The Pending Approvals tab shows:
- User requesting access
- Account requested
- Permission set (Admin, etc.)
- Business justification
- Request timestamp
- Duration requested

![Pending Approvals List - INSERT SCREENSHOT HERE]

### Approval Decision Criteria

**Consider approving when:**
- ✅ Valid business justification provided
- ✅ Requester has legitimate need
- ✅ Incident or emergency situation
- ✅ Ticket number referenced
- ✅ Appropriate duration requested

**Consider denying when:**
- ❌ Vague or missing justification
- ❌ Inappropriate access level
- ❌ No clear business need
- ❌ Excessive duration requested
- ❌ Lower access level would suffice

### Approving a Request

1. Review the request details
2. Click "✓ Approve" button
3. (Optional) Add comments explaining approval
4. Confirm approval

**Result:**
- ✅ Access granted immediately
- ✅ User notified via email
- ✅ Access will auto-revoke after duration
- ✅ Your decision recorded in audit log

![Approval Confirmation - INSERT SCREENSHOT HERE]

### Denying a Request

1. Review the request details
2. Click "✗ Deny" button
3. **Required:** Provide reason for denial
   - Be clear and constructive
   - Example: "Please use S3 Full Access instead of Admin for this task"
4. Confirm denial

**Result:**
- ❌ Access not granted
- ✅ User notified via email with your reason
- ✅ Decision recorded in audit log

![Denial Dialog - INSERT SCREENSHOT HERE]

### Email Notifications

Managers receive emails for:
- 🔔 New high-risk access request submitted
- 📧 Daily summary of pending approvals (if enabled)

**Email Example:**
```
Subject: JIT Access Approval Required - john.doe@company.com

Request ID: abc123-def456
User: john.doe@company.com
Account: Management
Permission Set: JIT-EmergencyAdmin
Reason: Emergency: Production database outage requiring immediate admin access

This is a HIGH RISK access request requiring approval.

To approve or deny, log in to: https://d72cs5opijkjl.cloudfront.net
```

### Best Practices for Managers

1. **Review Promptly**
   - Check for pending approvals regularly
   - Respond within 30 minutes during business hours
   - Set up email notifications

2. **Ask Questions**
   - If justification is unclear, ask for more details
   - Use Slack/Teams to clarify before approving
   - Better to delay than approve incorrectly

3. **Document Decisions**
   - Always add comments when approving/denying
   - Provide context for audit trail
   - Help engineers understand decisions

4. **Monitor Patterns**
   - Review approval history regularly
   - Identify frequently requested access
   - Consider permanent access for common patterns

5. **Emergency Protocols**
   - Establish clear emergency approval criteria
   - Document after-hours approval process
   - Have backup approvers designated

### Audit and Compliance

All approval decisions are logged with:
- Who requested access
- Who approved/denied
- When decision was made
- Comments provided
- IP address and user agent

This information is available in:
- DynamoDB table: JIT-Access-Requests
- CloudWatch Logs
- Audit reports (if configured)

---

## Administrator Guide

### System Administration

#### User Management

**Adding New Users:**

1. Navigate to: AWS Console → Cognito → User pools → JIT-Access-Portal → Users
2. Click "Create user"
3. Enter email address
4. Set temporary password: `TempPass123!`
5. Check "Mark email address as verified"
6. Click "Create user"

**Adding User to Identity Center:**

1. Navigate to: AWS IAM Identity Center → Users
2. Click "Add user"
3. Enter same email address
4. Add to "Engineers" group
5. Click "Create user"

**Assigning Groups:**

For regular engineers:
```
Cognito: Engineers group only
Result: Can submit requests, cannot approve
```

For managers:
```
Cognito: Managers group (+ Engineers optional)
Result: Can submit requests AND approve
```

**Removing Users:**

1. Cognito: Delete user from user pool
2. Identity Center: Disable or delete user
3. DynamoDB: User's requests remain for audit

#### Permission Set Management

**Current Permission Sets:**

| Name | ARN | Risk Level |
|------|-----|------------|
| JIT-S3FullAccess | ps-7223ce50e09c4ba5 | LOW |
| JIT-EC2FullAccess | ps-722330cfb38e1093 | LOW |
| JIT-EmergencyAdmin | ps-b9f47222e60d1c38 | HIGH |

**Adding New Permission Sets:**

1. Navigate to: IAM Identity Center → Permission sets
2. Click "Create permission set"
3. Select AWS managed policies or create custom
4. Name: `JIT-{ServiceName}-{AccessLevel}`
5. Set session duration: 1 hour
6. Add tags:
   - `RiskLevel`: `Low` or `High`
   - `RequiresApproval`: `true` or `false`

7. Update Lambda code to include new permission set:

```python
PERMISSION_SETS = {
    'NewPermissionSet': {
        'arn': 'arn:aws:sso:::permissionSet/ssoins-xxx/ps-xxx',
        'risk_level': 'LOW',  # or 'HIGH'
        'name': 'JIT-NewPermissionSet'
    }
}
```

8. Update portal HTML to add new option:
```html
<option value="NewPermissionSet">New Permission Set (Auto-approved)</option>
```

9. Redeploy Lambda and invalidate CloudFront cache

#### Account Management

**Current Accounts:**

| Name | Account ID | Purpose |
|------|-----------|---------|
| Management | 533267321107 | Organization management |
| Log Archive | 269423819609 | Centralized logging |
| Audit | 329668418788 | Security auditing |

**Adding New Accounts:**

1. Ensure account is in AWS Organization
2. Update Lambda environment variables:
```
NEW_ACCOUNT = 123456789012
```

3. Update Lambda code:
```python
ACCOUNTS = {
    'Management': os.environ['MANAGEMENT_ACCOUNT'],
    'LogArchive': os.environ['LOG_ARCHIVE_ACCOUNT'],
    'Audit': os.environ['AUDIT_ACCOUNT'],
    'NewAccount': os.environ['NEW_ACCOUNT']
}
```

4. Update portal HTML:
```html
<option value="NewAccount">New Account (123456789012)</option>
```

5. Provision permission sets to new account in Identity Center
6. Redeploy Lambda and invalidate CloudFront cache

#### Monitoring

**CloudWatch Dashboards:**

Create a dashboard to monitor:
- Request volume (requests per hour)
- Approval latency (time from request to approval)
- Revocation success rate
- Lambda errors and timeouts
- API Gateway 4xx/5xx errors

**Key Metrics to Track:**

```
Metric: RequestCount
Source: DynamoDB table scan
Frequency: Hourly

Metric: ApprovalTime
Calculation: ApprovalTimestamp - RequestTimestamp
Alert: > 1 hour for high-risk requests

Metric: LambdaErrors
Source: CloudWatch Logs
Alert: > 5 errors in 5 minutes

Metric: RevocationFailures
Source: CloudWatch Logs filter "Error revoking access"
Alert: Any failure
```

**Setting Up Alarms:**

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name JIT-Lambda-Errors \
  --alarm-description "Alert on Lambda errors" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1
```

#### Backup and Disaster Recovery

**DynamoDB Backups:**

Point-in-Time Recovery enabled:
- Automatic backups every 5 minutes
- Retention: 35 days
- Recovery: Any point in last 35 days

**Manual Backup:**
```bash
aws dynamodb create-backup \
  --table-name JIT-Access-Requests \
  --backup-name JIT-Access-Backup-$(date +%Y%m%d)
```

**Lambda Function Backups:**

Export Lambda code regularly:
```bash
aws lambda get-function --function-name JIT-Request-Handler \
  --query 'Code.Location' --output text | xargs curl -o JIT-Request-Handler.zip
```

**S3 Portal Backup:**
```bash
aws s3 sync s3://jit-access-portal-cognito-interface ./portal-backup/
```

**Recovery Procedures:**

1. **DynamoDB Table Loss:**
   - Restore from Point-in-Time Recovery
   - Validation: Check recent records exist

2. **Lambda Function Deletion:**
   - Recreate from CloudFormation or Terraform
   - Or manually recreate and upload backed-up code

3. **CloudFront Distribution Deletion:**
   - Recreate distribution with saved configuration
   - Update Cognito callback URLs
   - Invalidate cache

4. **Complete System Failure:**
   - Reference this documentation
   - Rebuild from scratch using configuration details
   - Restore DynamoDB from backup
   - Re-upload portal to S3

#### Log Management

**CloudWatch Log Groups:**

```
/aws/lambda/JIT-Request-Handler
/aws/lambda/JIT-Approval-Handler
/aws/lambda/JIT-Revoke-Access
/aws/lambda/JIT-Manual-Revoke
```

**Log Retention:**

Default: 30 days  
Recommendation: 90 days for compliance

Set retention:
```bash
aws logs put-retention-policy \
  --log-group-name /aws/lambda/JIT-Request-Handler \
  --retention-in-days 90
```

**Log Analysis:**

Search for failed requests:
```
filter @message like /ERROR/
| fields @timestamp, @message
| sort @timestamp desc
| limit 100
```

Search for specific user:
```
filter @message like /user@example.com/
| fields @timestamp, @message
| sort @timestamp desc
```

#### Cost Management

**Estimated Monthly Costs:**

| Service | Cost Driver | Est. Monthly Cost |
|---------|-------------|-------------------|
| Lambda | Requests + Duration | $5-20 |
| API Gateway | API Calls | $3-10 |
| DynamoDB | Storage + Reads/Writes | $2-5 |
| CloudFront | Data Transfer | $1-5 |
| Cognito | Active Users | Free (< 50,000) |
| SES | Emails Sent | $0.10 per 1,000 |
| EventBridge | Rules + Invocations | $1-3 |
| **Total** | | **$12-43/month** |

**Cost Optimization:**

1. Enable DynamoDB on-demand pricing (already enabled)
2. Set CloudWatch Logs retention to 90 days (not indefinite)
3. Use Lambda reserved concurrency if needed
4. Enable CloudFront compression
5. Clean up old DynamoDB records (> 1 year)

#### Security Hardening

**IAM Policies:**

Review and tighten:
```
Principle: Least privilege
Current: Policies allow * for some services
Improvement: Scope down to specific resources
```

**API Gateway:**

- ✅ Enable AWS WAF (optional, extra cost)
- ✅ Enable throttling: 1000 requests/second
- ✅ Enable API key for programmatic access
- ✅ Enable CloudWatch logging

**CloudFront:**

- ✅ Enable Origin Access Identity for S3
- ✅ Block country access (if needed)
- ✅ Enable AWS WAF rules
- ✅ Use custom domain with ACM certificate (future)

**Cognito:**

- ✅ Enable MFA for admin accounts
- ✅ Set password expiration: 90 days
- ✅ Enable advanced security features
- ✅ Configure account takeover protection

### Compliance and Auditing

#### Audit Log Access

**DynamoDB Query Examples:**

Get all requests by user:
```bash
aws dynamodb query \
  --table-name JIT-Access-Requests \
  --index-name UserId-RequestTimestamp-index \
  --key-condition-expression "UserId = :uid" \
  --expression-attribute-values '{":uid":{"S":"user-id-here"}}'
```

Get all pending requests:
```bash
aws dynamodb query \
  --table-name JIT-Access-Requests \
  --index-name Status-RequestTimestamp-index \
  --key-condition-expression "#status = :pending" \
  --expression-attribute-names '{"#status":"Status"}' \
  --expression-attribute-values '{":pending":{"S":"PENDING"}}'
```

#### Compliance Reports

**Monthly Access Report:**

```python
# Generate monthly summary
import boto3
from datetime import datetime, timedelta

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('JIT-Access-Requests')

# Last 30 days
start_time = int((datetime.now() - timedelta(days=30)).timestamp())

response = table.scan(
    FilterExpression='RequestTimestamp > :start',
    ExpressionAttributeValues={':start': start_time}
)

print(f"Total Requests: {len(response['Items'])}")
print(f"Auto-Approved: {sum(1 for i in response['Items'] if i['RiskLevel'] == 'LOW')}")
print(f"Requiring Approval: {sum(1 for i in response['Items
