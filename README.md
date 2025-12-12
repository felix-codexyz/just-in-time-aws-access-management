# Just-In-Time (JIT) AWS Access Management System

## 📋 Complete Documentation

**Version:** 1.0.0  
**Last Updated:** December 2025  
**Portal URL:** https://d72cs5opijkjl.cloudfront.net  
**GitHub Repository:** [Your Repository URL Here]

---

## 🎯 Quick Links

- [System Overview](#system-overview)
- [Getting Started](#getting-started)
- [User Guides](#user-guides)
- [Administrator Guide](./docs/ADMIN_GUIDE.md)
- [API Reference](./docs/API_REFERENCE.md)
- [Troubleshooting](./docs/TROUBLESHOOTING.md)
- [Architecture](./docs/ARCHITECTURE.md)

---

## 📖 System Overview

### What is JIT Access?

The Just-In-Time (JIT) Access Management System provides **temporary, time-bound access** to AWS resources with automated approval workflows and comprehensive audit trails. This system eliminates standing privileged access while maintaining operational efficiency.

### ✨ Key Features

#### 🚀 **Core Capabilities**
- ✅ **Automated Access Provisioning** - Low-risk requests auto-approved in seconds
- ✅ **Approval Workflows** - High-risk requests require manager approval
- ✅ **Time-Limited Access** - All access automatically expires (1 hour maximum)
- ✅ **Manual Revocation** - Revoke access anytime before expiration
- ✅ **Role-Based Access Control** - Engineers and Managers have different permissions

#### 📧 **Notifications**
- ✅ **Email Notifications** - Users notified of all access events
- ✅ **Manager Alerts** - Instant notification for approval requests
- ✅ **Revocation Notices** - Automatic alerts when access expires

#### 🔒 **Security & Compliance**
- ✅ **Full Audit Trail** - All requests logged with timestamps and approvers
- ✅ **CloudWatch Logging** - Detailed operational logs
- ✅ **HTTPS Web Portal** - Secure CloudFront distribution
- ✅ **AWS Cognito Authentication** - Enterprise-grade identity management

### 🎭 User Roles

| Role | Permissions | Use Cases |
|------|------------|-----------|
| **Engineer** | Submit access requests, View own requests, Manual revocation | Day-to-day operational access |
| **Manager** | Everything Engineers can + Approve/deny high-risk requests | Emergency access approval, Oversight |
| **Administrator** | System configuration, User management, Monitoring | System maintenance, Troubleshooting |

### 🔐 Access Types

| Permission Set | Risk Level | Approval | Auto-Revocation | Use Case |
|---------------|------------|----------|-----------------|----------|
| **S3 Full Access** | 🟢 Low | Auto-Approved | 1 hour | S3 bucket management, troubleshooting |
| **EC2 Full Access** | 🟢 Low | Auto-Approved | 1 hour | EC2 instance management, debugging |
| **Emergency Admin** | 🔴 High | Manager Required | 1 hour | Production incidents, Critical fixes |

---

## 🏗️ System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Users                                    │
│              (Engineers, Managers)                               │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTPS
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│              CloudFront Distribution (CDN)                       │
│              d72cs5opijkjl.cloudfront.net                       │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                  S3 Static Website                               │
│          jit-access-portal-cognito-interface                     │
│                  (React SPA)                                     │
└──────────────────────────┬──────────────────────────────────────┘
                           │ Authentication
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│              AWS Cognito User Pool                               │
│         us-east-1_K0m5bnDVE                                     │
│         Groups: Engineers, Managers                              │
└──────────────────────────┬──────────────────────────────────────┘
                           │ JWT Token
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                  API Gateway (REST API)                          │
│         jghpu14cya.execute-api.us-east-1.amazonaws.com          │
│                                                                  │
│  📍 POST /requests  - Submit access request                      │
│  📍 GET  /requests  - List user's requests                       │
│  📍 POST /approvals - Approve/deny requests                      │
│  📍 POST /revoke    - Manual revocation                          │
└──────────────────────────┬──────────────────────────────────────┘
                           │
           ┌───────────────┼───────────────┬──────────────┐
           ▼               ▼               ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   Lambda     │ │   Lambda     │ │   Lambda     │ │   Lambda     │
│   Request    │ │   Approval   │ │   Revoke     │ │   Manual     │
│   Handler    │ │   Handler    │ │   Access     │ │   Revoke     │
│              │ │              │ │              │ │              │
│  Python 3.12 │ │  Python 3.12 │ │  Python 3.12 │ │  Python 3.12 │
└──────┬───────┘ └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
       │                │                │                │
       └────────────────┼────────────────┼────────────────┘
                        ▼                ▼
              ┌─────────────────────────────┐
              │    AWS Identity Center      │
              │  ssoins-72236b71d9fcf9d2   │
              │  (Permission Assignment)    │
              └─────────────────────────────┘
                        │
                        ▼
              ┌─────────────────────────────┐
              │    Target AWS Accounts      │
              │  • Management (533267321107)│
              │  • Log Archive (269423819609)│
              │  • Audit (329668418788)     │
              └─────────────────────────────┘

📊 Supporting Services:
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  DynamoDB    │ │ EventBridge  │ │     SNS      │ │     SES      │
│  (Audit Log) │ │  Rules       │ │  (Approval   │ │   (Email     │
│  JIT-Access  │ │  (Auto-      │ │  Notifications)│ │  Notifications)│
│  -Requests   │ │  Revocation) │ │              │ │              │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
```

### 🔄 Data Flow

#### Request Submission Flow (Low-Risk)
```
1. 👤 User logs in via Cognito
2. 📝 User submits S3/EC2 access request
3. 🔐 API Gateway validates JWT token
4. ⚡ Lambda auto-approves (low risk)
5. ✅ Access granted in Identity Center
6. 📧 Email sent to user
7. ⏰ EventBridge schedules auto-revocation (1 hour)
8. 📊 Request logged in DynamoDB
```

#### Approval Flow (High-Risk)
```
1. 👤 User submits Emergency Admin request
2. 🔐 API Gateway validates JWT token
3. ⏸️ Lambda marks as PENDING
4. 📧 SNS notifies managers
5. 👔 Manager reviews in portal
6. ✅/❌ Manager approves or denies
7. 📧 User notified of decision
8. If approved: Access granted → Auto-revocation scheduled
9. 📊 Decision logged with approver details
```

#### Auto-Revocation Flow
```
1. ⏰ EventBridge Rule triggers at expiration
2. 🔄 Revoke Lambda invoked
3. 🗑️ Identity Center assignment deleted
4. 📊 DynamoDB updated to REVOKED
5. 📧 User notified via email
6. 🧹 EventBridge schedule cleaned up
```

---

## 🚀 Getting Started

### For Engineers

#### 1. Access the Portal
Navigate to: **https://d72cs5opijkjl.cloudfront.net**

<img width="1053" height="551" alt="image" src="https://github.com/user-attachments/assets/49599c7a-276a-433e-a53a-30525e4b2a20" />

*Portal login page*

#### 2. First-Time Login
- Enter your email and temporary password
- Set a new password when prompted
- Password must meet complexity requirements

#### 3. Request Access
1. Click **"New Request"** tab
2. Select AWS Account
3. Choose Permission Set
4. Provide business justification
5. Click **"Submit Request"**

<img width="1017" height="860" alt="image" src="https://github.com/user-attachments/assets/7ddc8a50-3d3f-496b-ab0f-2e0a7d2c7bb6" />

*Access request form*

#### 4. Access Your AWS Resources
- Check your email for confirmation
- Log in to AWS SSO portal
- Your temporary role will be available

### For Managers

#### 1. Log In
Same portal: **https://d72cs5opijkjl.cloudfront.net**

#### 2. View Pending Approvals
- You'll see an additional **"Pending Approvals"** tab
- Review requests from your team

<img width="1046" height="1191" alt="image" src="https://github.com/user-attachments/assets/cacbf6d7-6762-42d6-9840-53d2033774fb" />
*Manager approval interface*

#### 3. Approve or Deny
- Click ✓ Approve or ✗ Deny
- Add comments (optional for approve, required for deny)
- User receives immediate notification

---

## 📚 User Guides

### 📘 Engineer Guide

#### Requesting Access

**Step 1: Choose Your Account**
Select from available accounts:
- **Management** - Organization management account
- **Log Archive** - Centralized logging
- **Audit** - Security auditing

**Step 2: Select Permission Level**

| Permission Set | When to Use | Approval Time |
|---------------|-------------|---------------|
| S3 Full Access | S3 bucket work, logs, backups | Instant |
| EC2 Full Access | Instance management, troubleshooting | Instant |
| Emergency Admin | Production incidents only | Requires approval |

**Step 3: Provide Justification**

✅ **Good Examples:**
```
"Investigating S3 replication failure for TICKET-1234"
"Need to restart EC2 instances for deployment RELEASE-567"
"Emergency: Production database outage - need admin access for recovery"
```

❌ **Poor Examples:**
```
"Testing"
"Need access"
"Admin stuff"
```

**Step 4: Submit**
- Low-risk: Access granted in 1-2 minutes
- High-risk: Wait for manager approval (typically < 30 minutes)

#### Viewing Request History

Click **"My Requests"** to see:
- ✅ **ACTIVE** - Access currently granted
- ⏳ **PENDING** - Awaiting approval
- ❌ **DENIED** - Request was denied
- ⚫ **REVOKED** - Access has been revoked

<img width="1027" height="1160" alt="image" src="https://github.com/user-attachments/assets/bd29615b-b6b7-4fa7-aaf7-6d754a86c784" />

*Request history view*

#### Manual Revocation

For active requests:
1. Find the request in "My Requests"
2. Click **"🚫 Revoke Now"**
3. Confirm revocation
4. Access removed immediately

**Why revoke early?**
- ✅ Security best practice
- ✅ Reduces attack surface
- ✅ Shows good security hygiene
- ✅ Frees up monitoring alerts

#### Email Notifications

You receive emails for:
| Event | Subject Line | When |
|-------|-------------|------|
| Access Granted | ✓ JIT Access Granted | Low-risk approval |
| Pending Approval | ⏳ Access Request Submitted | High-risk request |
| Request Approved | ✓ Request Approved | Manager approval |
| Request Denied | ✗ Request Denied | Manager denial |
| Access Revoked | ⏱ Access Revoked | Auto or manual revocation |

### 📗 Manager Guide

#### Approval Responsibilities

As a manager, you review high-risk access requests. Consider:

**✅ Approve When:**
- Valid business justification
- Referenced ticket/incident number
- Appropriate permission level
- Requester has legitimate need
- Emergency or time-sensitive

**❌ Deny When:**
- Vague justification
- No clear business need
- Lower access level would suffice
- Missing incident details
- Excessive duration

#### Approval Process

1. **Check Email**
   - You receive instant notification
   - Email contains request details

2. **Review in Portal**
   - Log in to portal
   - Click "Pending Approvals" tab
   - Review requester, justification, timestamp

3. **Make Decision**
   - Click ✓ Approve or ✗ Deny
   - Add comments (helps with audit trail)
   - Confirm action

4. **User Notified**
   - User receives email immediately
   - If approved: Access granted in 1-2 minutes
   - If denied: User sees your reason

<img width="1046" height="1191" alt="image" src="https://github.com/user-attachments/assets/cacbf6d7-6762-42d6-9840-53d2033774fb" />

*Manager approval interface with pending requests*

#### Best Practices

**⚡ Respond Quickly**
- Target: < 30 minutes during business hours
- Enable mobile notifications
- Delegate backup approvers for PTO

**📝 Document Decisions**
- Always add comments
- Reference tickets/incidents
- Explain denial reasons clearly

**🔍 Monitor Patterns**
- Review approval history monthly
- Identify frequently requested access
- Consider permanent access for common needs

**🚨 Emergency Protocols**
- Establish clear emergency criteria
- Document after-hours process
- Have backup approvers identified

---

## 🛠️ Administrator Guide

### System Configuration

#### AWS Accounts Configured
| Account Name | Account ID | Purpose |
|-------------|-----------|---------|
| Management | 533267321107 | Organization management |
| Log Archive | 269423819609 | Centralized logging |
| Audit | 329668418788 | Security auditing |

#### Permission Sets
| Name | ARN Suffix | Risk Level | Auto-Approve |
|------|-----------|------------|--------------|
| JIT-S3FullAccess | ps-7223ce50e09c4ba5 | Low | Yes |
| JIT-EC2FullAccess | ps-722330cfb38e1093 | Low | Yes |
| JIT-EmergencyAdmin | ps-b9f47222e60d1c38 | High | No |

### User Management

#### Adding New Users

**1. Create in Cognito:**
```bash
AWS Console → Cognito → User pools → JIT-Access-Portal → Users → Create user

Settings:
- Email: user@company.com
- Temporary password: TempPass123!
- ✓ Mark email as verified
```

**2. Add to Identity Center:**
```bash
AWS Console → IAM Identity Center → Users → Add user

Settings:
- Username: user@company.com (same as Cognito)
- Email: user@company.com
- Groups: Engineers
```

**3. Assign Group in Cognito:**
```bash
Cognito → Users → [Select user] → Add user to group

For Engineers: Engineers group
For Managers: Managers group (+ Engineers optional)
```

#### User Roles

**Engineers Only:**
- Cognito Groups: `Engineers`
- Portal Access: ✅ New Request, ✅ My Requests, ❌ Pending Approvals

**Managers:**
- Cognito Groups: `Managers` (optionally also `Engineers`)
- Portal Access: ✅ New Request, ✅ My Requests, ✅ Pending Approvals

#### Removing Users

1. **Cognito:** Delete from user pool
2. **Identity Center:** Disable or delete user
3. **Note:** Historical requests remain in DynamoDB for audit

### Monitoring

#### Key Metrics to Track

| Metric | Source | Alert Threshold |
|--------|--------|----------------|
| Request Volume | DynamoDB | > 100/hour unusual |
| Lambda Errors | CloudWatch | > 5 in 5 minutes |
| Approval Latency | DynamoDB | > 1 hour for high-risk |
| Revocation Failures | CloudWatch Logs | Any failure |
| API 4xx/5xx Errors | API Gateway | > 10 in 5 minutes |

#### CloudWatch Log Groups
```
/aws/lambda/JIT-Request-Handler
/aws/lambda/JIT-Approval-Handler  
/aws/lambda/JIT-Revoke-Access
/aws/lambda/JIT-Manual-Revoke
```

**Log Retention:** 90 days (recommended for compliance)

#### Setting Up Alarms

**Lambda Error Alarm:**
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name JIT-Lambda-Errors \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold
```

**API Gateway Error Alarm:**
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name JIT-API-5xx-Errors \
  --metric-name 5XXError \
  --namespace AWS/ApiGateway \
  --dimensions Name=ApiName,Value=JIT-Access-API \
  --statistic Sum \
  --period 300 \
  --threshold 10
```

### Backup & Recovery

#### DynamoDB Backups
- ✅ **Point-in-Time Recovery**: Enabled (35 days)
- ✅ **Automated Backups**: Every 5 minutes
- 📅 **Manual Backups**: Recommended monthly

**Create Manual Backup:**
```bash
aws dynamodb create-backup \
  --table-name JIT-Access-Requests \
  --backup-name JIT-Backup-$(date +%Y%m%d)
```

#### Lambda Backups

**Export Lambda Code:**
```bash
# Request Handler
aws lambda get-function --function-name JIT-Request-Handler \
  --query 'Code.Location' --output text | xargs curl -o JIT-Request-Handler.zip

# Approval Handler  
aws lambda get-function --function-name JIT-Approval-Handler \
  --query 'Code.Location' --output text | xargs curl -o JIT-Approval-Handler.zip

# Revoke Access
aws lambda get-function --function-name JIT-Revoke-Access \
  --query 'Code.Location' --output text | xargs curl -o JIT-Revoke-Access.zip

# Manual Revoke
aws lambda get-function --function-name JIT-Manual-Revoke \
  --query 'Code.Location' --output text | xargs curl -o JIT-Manual-Revoke.zip
```

#### Portal Backup

**Backup S3 Website:**
```bash
aws s3 sync s3://jit-access-portal-cognito-interface ./portal-backup/
```

#### Recovery Procedures

**Scenario 1: DynamoDB Table Deleted**
```bash
# Restore from Point-in-Time Recovery
aws dynamodb restore-table-to-point-in-time \
  --source-table-name JIT-Access-Requests \
  --target-table-name JIT-Access-Requests \
  --restore-date-time $(date -u +"%Y-%m-%dT%H:%M:%SZ" -d "1 hour ago")
```

**Scenario 2: Lambda Function Deleted**
- Recreate function with same name
- Upload backed-up code
- Reconfigure environment variables
- Reattach IAM role

**Scenario 3: Complete System Failure**
- Use this documentation to rebuild
- Restore DynamoDB from backup
- Re-upload portal to S3
- Recreate CloudFront distribution
- Update Cognito callback URLs

### Cost Management

#### Estimated Monthly Costs

| Service | Usage | Est. Cost |
|---------|-------|-----------|
| Lambda | ~10,000 requests | $5-10 |
| API Gateway | ~10,000 calls | $3-5 |
| DynamoDB | On-demand | $2-5 |
| CloudFront | Data transfer | $1-3 |
| Cognito | < 50k MAU | Free |
| SES | 1,000 emails | $0.10 |
| EventBridge | Rules + invocations | $1-2 |
| **Total** | | **~$12-25/month** |

#### Cost Optimization Tips

1. ✅ **DynamoDB**: On-demand pricing (already enabled)
2. ✅ **CloudWatch Logs**: 90-day retention (not indefinite)
3. ✅ **Lambda**: Right-sized memory (256 MB sufficient)
4. ✅ **CloudFront**: Enable compression
5. ✅ **Data Cleanup**: Archive old DynamoDB records (> 1 year)

### Security Hardening

#### IAM Policy Review

**Current IAM Role:** `JIT-Automation-Role`

**Attached Policies:**
- `JIT-Automation-Policy` (custom)

**Permissions Granted:**
- ✅ Identity Center management
- ✅ DynamoDB read/write
- ✅ SNS publish
- ✅ SES send email
- ✅ EventBridge scheduler
- ✅ CloudWatch logging

**Security Recommendations:**
1. Review policy quarterly
2. Remove unused permissions
3. Enable CloudTrail for API calls
4. Set up SCPs in AWS Organizations

#### API Gateway Security

**Current Configuration:**
- ✅ Cognito authorizer enabled
- ✅ CORS configured
- ✅ Throttling: 1000 req/sec (default)

**Recommendations:**
- Consider AWS WAF ($5-10/month)
- Enable API keys for programmatic access
- Set up request validation
- Monitor for suspicious patterns

#### Cognito Security

**Current Settings:**
- ✅ Password complexity required
- ✅ Email verification
- ✅ JWT token expiration: 1 hour

**Recommendations:**
- Enable MFA for admin accounts
- Set password expiration: 90 days
- Enable advanced security features
- Configure account takeover protection

---

## 🔧 Troubleshooting

### Common Issues

#### Issue: User Can't Log In

**Symptoms:**
- "Incorrect username or password"
- "User does not exist"

**Solutions:**
1. Verify user exists in Cognito
2. Check if email is verified
3. Reset password if needed
4. Ensure user is in correct group

**Steps:**
```bash
1. AWS Console → Cognito → User pools → JIT-Access-Portal
2. Search for user email
3. If not found: Create user
4. If found: Click user → Reset password
5. Check Groups tab → Add to Engineers/Managers
```

#### Issue: Approval Tab Not Visible

**Symptoms:**
- Manager can't see "Pending Approvals" tab
- Tab disappears after login

**Solutions:**
1. Verify user is in Managers group (Cognito)
2. Clear browser cache
3. Logout and login again (refresh JWT token)
4. Check browser console for errors

**Steps:**
```bash
1. Cognito → Users → [Select user]
2. Check Group memberships
3. If not in Managers: Add user to group
4. User must logout and login to refresh token
5. Clear CloudFront cache if needed
```

#### Issue: Access Request Fails

**Symptoms:**
- "Request failed" error
- No email received
- Request doesn't appear in history

**Solutions:**
1. Check CloudWatch Logs for errors
2. Verify Lambda permissions
3. Check Identity Center connectivity
4. Verify DynamoDB table exists

**Debugging:**
```bash
1. CloudWatch → Log groups → /aws/lambda/JIT-Request-Handler
2. Find most recent log stream
3. Look for ERROR messages
4. Common errors:
   - "User not found in Identity Center"
   - "Permission denied"
   - "DynamoDB access denied"
```

#### Issue: Auto-Revocation Doesn't Work

**Symptoms:**
- Access still active after 1 hour
- No revocation email received
- EventBridge schedule exists but didn't fire

**Solutions:**
1. Check EventBridge Rule status
2. Verify Lambda permissions
3. Check CloudWatch Logs for revocation Lambda
4. Manually revoke if needed

**Steps:**
```bash
1. EventBridge → Rules
2. Find rule: revoke-{request-id}
3. Check if Enabled
4. Check Last execution time
5. If failed: Check CloudWatch Logs
6. Manual revocation: Portal → My Requests → Revoke Now
```

#### Issue: Email Notifications Not Received

**Symptoms:**
- No emails for approved requests
- No approval notification emails

**Solutions:**
1. Check SES sandbox status
2. Verify email is verified in SES
3. Check spam folder
4. Review Lambda logs for SES errors

**Steps:**
```bash
1. SES → Verified identities
2. Ensure felixayo85@gmail.com is Verified
3. Check SES sending quotas
4. Review CloudWatch Logs for "SES" errors
5. For production: Request SES production access
```

#### Issue: Portal Shows 504 Error

**Symptoms:**
- CloudFront shows "Gateway Timeout"
- Portal loads on S3 but not CloudFront

**Solutions:**
1. Check CloudFront origin configuration
2. Verify origin protocol is HTTP Only
3. Invalidate CloudFront cache
4. Check S3 website hosting is enabled

**Steps:**
```bash
1. CloudFront → Distributions → [Your distribution]
2. Origins tab → Click origin
3. Verify Protocol: HTTP only
4. Invalidations tab → Create invalidation → /*
5. Wait 2-3 minutes
6. Try accessing portal again
```

### Error Messages

| Error Message | Meaning | Solution |
|--------------|---------|----------|
| "User not found in Identity Center" | Email doesn't exist in Identity Center | Add user to Identity Center |
| "Request failed" | Lambda execution error | Check CloudWatch Logs |
| "Not authorized" | JWT token invalid/expired | Logout and login again |
| "Access denied" | IAM permissions issue | Review JIT-Automation-Role policy |
| "Network error" | CORS or API Gateway issue | Check API Gateway CORS configuration |

### Getting Help

**1. Check CloudWatch Logs**
- Most issues are logged here
- Look for ERROR or WARN messages
- Note the Request ID for correlation

**2. Review DynamoDB**
- Check request status
- Verify timestamps are correct
- Look for error messages in records

**3. Test Components Individually**
- Test Lambda functions directly
- Test API endpoints with Postman
- Verify Identity Center manually

**4. Contact Support**
When reporting issues, provide:
- Request ID (from DynamoDB or logs)
- User email
- Timestamp of issue
- Error message
- Screenshots
- CloudWatch Log excerpts

---

## 📊 API Reference

### Authentication

All API endpoints require JWT authentication via AWS Cognito.

**Headers Required:**
```http
Authorization: <JWT_TOKEN>
Content-Type: application/json
```

### Endpoints

#### POST /requests

Submit a new access request.

**Request Body:**
```json
{
  "user_email": "engineer@company.com",
  "account_name": "Management",
  "permission_set": "S3FullAccess",
  "reason": "Investigating S3 issue TICKET-1234",
  "duration_minutes": 60
}
```

**Response (Low-Risk Auto-Approved):**
```json
{
  "message": "Access granted automatically (low risk)",
  "request_id": "abc123-def456",
  "status": "ACTIVE",
  "expires_at": "2025-12-06T15:30:00",
  "account": "Management",
  "permission_set": "S3FullAccess"
}
```

**Response (High-Risk Pending):**
```json
{
  "message": "Access request pending approval (high risk)",
  "request_id": "xyz789-uvw012",
  "status": "PENDING",
  "account": "Management",
  "permission_set": "EmergencyAdmin",
  "note": "Manager approval required"
}
```

#### GET /requests

List all requests for the authenticated user.

**Response:**
```json
{
  "requests": [
    {
      "RequestId": "abc123",
      "UserEmail": "engineer@company.com",
      "AccountName": "Management",
      "PermissionSet": "JIT-S3FullAccess",
      "Status": "ACTIVE",
      "RequestTimestamp": 1733500800,
      "ExpirationTimestamp": 1733504400,
      "Reason": "S3 troubleshooting"
    }
  ],
  "count": 1
}
```

#### POST /approvals

Approve or deny a pending request (Managers only).

**Request Body (Approve):**
```json
{
  "request_id": "xyz789",
  "action": "APPROVE",
  "approver_email": "manager@company.com",
  "comments": "Approved for incident INC-5678"
}
```

**Request Body (Deny):**
```json
{
  "request_id": "xyz789",
  "action": "DENY",
  "approver_email": "manager@company.com",
  "comments": "Use S3 access instead of Admin"
}
```

**Response:**
```json
{
  "message": "Request approved and access granted",
  "request_id": "xyz789",
  "status": "ACTIVE",
  "approver": "manager@company.com",
  "user_email": "engineer@company.com",
  "expires_at": "2025-12-06T16:00:00"
}
```

#### POST /revoke

Manually revoke active access.

**Request Body:**
```json
{
  "request_id": "abc123",
  "revoker_email": "engineer@company.com"
}
```

**Response:**
```json
{
  "message": "Access successfully revoked",
  "request_id": "abc123",
  "user_email": "engineer@company.com",
  "account": "Management",
  "permission_set": "JIT-S3FullAccess",
  "revoked_by": "engineer@company.com"
}
```

---

## 📈 Operational Metrics

### Key Performance Indicators

| Metric | Target | Measurement |
|--------|--------|-------------|
| Request Processing Time | < 5 seconds | Lambda execution time |
| Approval Latency | < 30 minutes | Time from request to approval |
| Auto-Revocation Success Rate | > 99% | Successful revocations / total |
| Portal Uptime | > 99.9% | CloudFront availability |
| Lambda Error Rate | < 0.1% | Errors /
