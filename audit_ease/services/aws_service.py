"""
AWS Service for Security Audits

Provides a secure interface to AWS accounts for compliance checking.
Handles S3, IAM, and CloudTrail audits with proper error handling.

All credentials are decrypted from Integration storage via encryption_manager.
No keys are logged or exposed in error messages.
"""

import logging
import boto3
from typing import Dict, List, Any, Tuple
from botocore.exceptions import ClientError, BotoCoreError

logger = logging.getLogger(__name__)


class AwsServiceError(Exception):
    """Base exception for AWS service errors."""
    pass


class AwsAuthenticationError(AwsServiceError):
    """Raised when AWS authentication fails."""
    pass


class AwsService:
    """
    Production-ready AWS API client for compliance auditing.
    
    Performs real security checks against AWS accounts:
    - S3 bucket public access configuration
    - IAM root account MFA enablement
    - CloudTrail multi-region trail setup
    """

    def __init__(self, access_key: str, secret_key: str, region: str = 'us-east-1'):
        """
        Initialize AWS service with encrypted credentials.
        
        Args:
            access_key: AWS Access Key ID (decrypted from Integration)
            secret_key: AWS Secret Access Key (decrypted from Integration)
            region: AWS region for API calls (default: us-east-1)
        
        Raises:
            AwsAuthenticationError: If credentials are invalid or missing
        """
        if not access_key or not secret_key:
            raise AwsAuthenticationError("AWS credentials are missing or empty")
        
        self.region = region
        
        # Test authentication immediately (use local variables only, never store credentials)
        try:
            self.session = self.get_session(access_key, secret_key, region)
            self._verify_authentication()
        except Exception as e:
            logger.error(f"AWS authentication failed: {type(e).__name__}")
            raise AwsAuthenticationError(f"Failed to authenticate with AWS: {str(e)}")

    def get_session(self, access_key: str, secret_key: str, region: str) -> boto3.Session:
        """
        Create and return a boto3 session with the provided credentials.
        
        Args:
            access_key: AWS Access Key ID
            secret_key: AWS Secret Access Key
            region: AWS region
        
        Returns:
            boto3.Session: Authenticated session
        """
        try:
            session = boto3.Session(
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name=region
            )
            return session
        except Exception as e:
            logger.error(f"Failed to create AWS session: {type(e).__name__}")
            raise AwsAuthenticationError(f"Failed to create session: {str(e)}")

    def _verify_authentication(self) -> None:
        """
        Verify AWS credentials are valid by making a test call.
        Uses STS GetCallerIdentity (least privileged check).
        """
        try:
            sts = self.session.client('sts')
            sts.get_caller_identity()
            logger.info("AWS authentication verified")
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code in ['InvalidClientTokenId', 'SignatureDoesNotMatch']:
                raise AwsAuthenticationError("Invalid AWS credentials")
            raise AwsAuthenticationError(f"AWS authentication failed: {error_code}")
        except Exception as e:
            raise AwsAuthenticationError(f"AWS authentication check failed: {type(e).__name__}")

    def audit_s3_buckets(self) -> Dict[str, Any]:
        """
        Audit S3 buckets for public access block compliance.
        
        CRITICAL CHECK: Ensures buckets are not publicly accessible.
        Uses GetPublicAccessBlock to verify bucket-level settings.
        
        Returns:
            {
                'status': 'PASS' | 'FAIL',
                'compliant_buckets': [...],
                'non_compliant_buckets': [...],
                'total_buckets': int,
                'message': str,
                'raw_data': {...}
            }
        """
        try:
            s3 = self.session.client('s3')
            
            # List all buckets
            response = s3.list_buckets()
            buckets = response.get('Buckets', [])
            
            if not buckets:
                return {
                    'status': 'PASS',
                    'compliant_buckets': [],
                    'non_compliant_buckets': [],
                    'total_buckets': 0,
                    'message': 'No S3 buckets found',
                    'raw_data': {'bucket_count': 0}
                }
            
            compliant = []
            non_compliant = []
            
            # Check each bucket for public access block
            for bucket in buckets:
                bucket_name = bucket['Name']
                try:
                    pab_response = s3.get_public_access_block(Bucket=bucket_name)
                    pab_config = pab_response.get('PublicAccessBlockConfiguration', {})
                    
                    # Compliant if ALL are True
                    is_compliant = (
                        pab_config.get('BlockPublicAcls', False) and
                        pab_config.get('IgnorePublicAcls', False) and
                        pab_config.get('BlockPublicPolicy', False) and
                        pab_config.get('RestrictPublicBuckets', False)
                    )
                    
                    bucket_info = {
                        'name': bucket_name,
                        'public_access_block': pab_config,
                        'created_date': str(bucket['CreationDate'])
                    }
                    
                    if is_compliant:
                        compliant.append(bucket_info)
                    else:
                        non_compliant.append(bucket_info)
                
                except ClientError as e:
                    error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                    if error_code == 'NoSuchPublicAccessBlockConfiguration':
                        # No block set = non-compliant
                        non_compliant.append({
                            'name': bucket_name,
                            'issue': 'No public access block configured',
                            'created_date': str(bucket['CreationDate'])
                        })
                    else:
                        logger.warning(f"Could not check bucket {bucket_name}: {error_code}")
                        non_compliant.append({
                            'name': bucket_name,
                            'issue': f'Could not verify: {error_code}',
                            'created_date': str(bucket['CreationDate'])
                        })
            
            # Determine overall status
            all_compliant = len(non_compliant) == 0
            status = 'PASS' if all_compliant else 'FAIL'
            
            return {
                'status': status,
                'compliant_buckets': compliant,
                'non_compliant_buckets': non_compliant,
                'total_buckets': len(buckets),
                'compliant_count': len(compliant),
                'non_compliant_count': len(non_compliant),
                'message': f"S3 Audit: {len(compliant)}/{len(buckets)} buckets are compliant",
                'raw_data': {
                    'total': len(buckets),
                    'compliant': len(compliant),
                    'non_compliant': len(non_compliant)
                }
            }
        
        except Exception as e:
            logger.error(f"S3 audit failed: {type(e).__name__}: {str(e)}")
            return {
                'status': 'ERROR',
                'compliant_buckets': [],
                'non_compliant_buckets': [],
                'total_buckets': 0,
                'message': f"S3 audit error: {type(e).__name__}",
                'raw_data': {'error': type(e).__name__}
            }

    def audit_iam_root(self) -> Dict[str, Any]:
        """
        Audit IAM root account for MFA enablement.
        
        CRITICAL CHECK: Root account must have MFA enabled.
        Uses credential report to verify root access key usage and MFA.
        
        Returns:
            {
                'status': 'PASS' | 'FAIL',
                'root_mfa_enabled': bool,
                'message': str,
                'raw_data': {...}
            }
        """
        try:
            iam = self.session.client('iam')
            
            # Get account summary
            summary = iam.get_account_summary()
            summary_data = summary.get('SummaryMap', {})
            
            # Get credential report (requires AccountAccessKeysPresent check)
            try:
                # Request new credential report
                iam.generate_credential_report()
                
                # Get the report
                import time
                report_response = iam.get_credential_report()
                
                # Parse CSV report
                import csv
                import io
                
                report_csv = report_response['Content'].decode('utf-8')
                reader = csv.DictReader(io.StringIO(report_csv))
                
                root_entry = None
                for row in reader:
                    if row['user'] == '<root_account>':
                        root_entry = row
                        break
                
                if not root_entry:
                    return {
                        'status': 'FAIL',
                        'root_mfa_enabled': False,
                        'message': 'Could not determine root account MFA status',
                        'raw_data': {'error': 'Root account not found in credential report'}
                    }
                
                # Check MFA - column is "mfa_active"
                mfa_enabled = root_entry.get('mfa_active', 'false').lower() == 'true'
                
                # Also check access key status
                access_key_1_active = root_entry.get('access_key_1_active', 'false').lower() == 'true'
                access_key_2_active = root_entry.get('access_key_2_active', 'false').lower() == 'true'
                
                status = 'PASS' if mfa_enabled else 'FAIL'
                
                return {
                    'status': status,
                    'root_mfa_enabled': mfa_enabled,
                    'root_has_access_keys': access_key_1_active or access_key_2_active,
                    'message': (
                        f"Root account MFA: {'Enabled' if mfa_enabled else 'NOT ENABLED'}"
                    ),
                    'raw_data': {
                        'mfa_active': mfa_enabled,
                        'access_key_1_active': access_key_1_active,
                        'access_key_2_active': access_key_2_active,
                        'password_enabled': root_entry.get('password_enabled', 'unknown')
                    }
                }
            
            except Exception as e:
                logger.warning(f"Could not retrieve credential report: {type(e).__name__}")
                # Fallback: Use account summary data
                return {
                    'status': 'UNKNOWN',
                    'root_mfa_enabled': False,
                    'message': f"Could not verify root MFA status: {type(e).__name__}",
                    'raw_data': {'error': type(e).__name__}
                }
        
        except Exception as e:
            logger.error(f"IAM root audit failed: {type(e).__name__}")
            return {
                'status': 'ERROR',
                'root_mfa_enabled': False,
                'message': f"IAM audit error: {type(e).__name__}",
                'raw_data': {'error': type(e).__name__}
            }

    def audit_rds_encryption(self) -> Dict[str, Any]:
        """
        Audit RDS instances for encryption at rest.
        
        CRITICAL CHECK: All RDS instances must have StorageEncrypted = True.
        Ensures database data is encrypted.
        
        Returns:
            {
                'status': 'PASS' | 'FAIL',
                'encrypted_instances': [...],
                'unencrypted_instances': [...],
                'message': str,
                'raw_data': {...}
            }
        """
        try:
            rds = self.session.client('rds')
            
            # List all RDS instances across regions
            response = rds.describe_db_instances()
            instances = response.get('DBInstances', [])
            
            if not instances:
                return {
                    'status': 'PASS',
                    'encrypted_instances': [],
                    'unencrypted_instances': [],
                    'total_instances': 0,
                    'message': 'No RDS instances found',
                    'raw_data': {'instance_count': 0}
                }
            
            encrypted = []
            unencrypted = []
            
            for instance in instances:
                instance_info = {
                    'identifier': instance.get('DBInstanceIdentifier'),
                    'engine': instance.get('Engine'),
                    'storage_encrypted': instance.get('StorageEncrypted', False),
                    'kms_key_id': instance.get('KmsKeyId', 'N/A'),
                    'availability_zone': instance.get('AvailabilityZone')
                }
                
                if instance.get('StorageEncrypted', False):
                    encrypted.append(instance_info)
                else:
                    unencrypted.append(instance_info)
            
            all_encrypted = len(unencrypted) == 0
            status = 'PASS' if all_encrypted else 'FAIL'
            
            return {
                'status': status,
                'encrypted_instances': encrypted,
                'unencrypted_instances': unencrypted,
                'total_instances': len(instances),
                'encrypted_count': len(encrypted),
                'unencrypted_count': len(unencrypted),
                'message': f"RDS Encryption: {len(encrypted)}/{len(instances)} instances are encrypted",
                'raw_data': {
                    'total': len(instances),
                    'encrypted': len(encrypted),
                    'unencrypted': len(unencrypted)
                }
            }
        
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            logger.error(f"RDS audit failed with error: {error_code}")
            return {
                'status': 'ERROR',
                'encrypted_instances': [],
                'unencrypted_instances': [],
                'total_instances': 0,
                'message': f"RDS audit error: {error_code}",
                'raw_data': {'error': error_code}
            }
        except Exception as e:
            logger.error(f"RDS audit failed: {type(e).__name__}")
            return {
                'status': 'ERROR',
                'encrypted_instances': [],
                'unencrypted_instances': [],
                'total_instances': 0,
                'message': f"RDS audit error: {type(e).__name__}",
                'raw_data': {'error': type(e).__name__}
            }

    def audit_iam_mfa(self) -> Dict[str, Any]:
        """
        Audit all console-access IAM users for MFA enablement.
        
        CRITICAL CHECK: All users with console access must have MFA enabled.
        Also checks root account MFA separately.
        
        Returns:
            {
                'status': 'PASS' | 'FAIL',
                'root_mfa_enabled': bool,
                'users_with_mfa': [...],
                'users_without_mfa': [...],
                'message': str,
                'raw_data': {...}
            }
        """
        try:
            iam = self.session.client('iam')
            
            # Generate credential report
            try:
                iam.generate_credential_report()
                
                # Polling loop: credential report generation is asynchronous
                # We must poll get_credential_report() until it succeeds
                import time
                max_retries = 10
                retry_count = 0
                report_response = None
                
                while retry_count < max_retries:
                    try:
                        report_response = iam.get_credential_report()
                        break  # Successfully retrieved
                    except ClientError as e:
                        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                        if error_code == 'ReportInProgress':
                            # Report still being generated, wait and retry
                            retry_count += 1
                            if retry_count < max_retries:
                                time.sleep(1)
                            continue
                        else:
                            # Different error, propagate it
                            raise
                
                # Check if we timed out
                if report_response is None:
                    return {
                        'status': 'UNKNOWN',
                        'root_mfa_enabled': False,
                        'users_with_mfa': [],
                        'users_without_mfa': [],
                        'message': 'Credential report generation timed out after 10 attempts',
                        'raw_data': {'error': 'Report timeout'}
                    }
                
                import csv
                import io
                
                report_csv = report_response['Content'].decode('utf-8')
                reader = csv.DictReader(io.StringIO(report_csv))
                
                root_mfa = False
                users_with_mfa = []
                users_without_mfa = []
                
                for row in reader:
                    user_name = row.get('user', '')
                    
                    # Root account
                    if user_name == '<root_account>':
                        root_mfa = row.get('mfa_active', 'false').lower() == 'true'
                        continue
                    
                    # Check if user has password (console access)
                    password_enabled = row.get('password_enabled', 'false').lower() == 'true'
                    
                    if not password_enabled:
                        continue  # Skip programmatic-only users
                    
                    # Check MFA status
                    mfa_active = row.get('mfa_active', 'false').lower() == 'true'
                    
                    user_info = {
                        'username': user_name,
                        'password_enabled': password_enabled,
                        'mfa_active': mfa_active,
                        'password_last_used': row.get('password_last_used', 'N/A')
                    }
                    
                    if mfa_active:
                        users_with_mfa.append(user_info)
                    else:
                        users_without_mfa.append(user_info)
                
                # Status is FAIL if root or any console user lacks MFA
                all_compliant = root_mfa and len(users_without_mfa) == 0
                status = 'PASS' if all_compliant else 'FAIL'
                
                return {
                    'status': status,
                    'root_mfa_enabled': root_mfa,
                    'users_with_mfa': users_with_mfa,
                    'users_without_mfa': users_without_mfa,
                    'message': (
                        f"IAM MFA: Root MFA {'enabled' if root_mfa else 'DISABLED'}, "
                        f"{len(users_with_mfa)} users with MFA, {len(users_without_mfa)} without"
                    ),
                    'raw_data': {
                        'root_mfa_enabled': root_mfa,
                        'users_with_mfa_count': len(users_with_mfa),
                        'users_without_mfa_count': len(users_without_mfa)
                    }
                }
            
            except ClientError as e:
                logger.warning(f"Could not retrieve credential report: {e}")
                return {
                    'status': 'UNKNOWN',
                    'root_mfa_enabled': False,
                    'users_with_mfa': [],
                    'users_without_mfa': [],
                    'message': f"Could not verify IAM MFA status: {e.response.get('Error', {}).get('Code', 'Unknown')}",
                    'raw_data': {'error': 'Credential report unavailable'}
                }
        
        except Exception as e:
            logger.error(f"IAM MFA audit failed: {type(e).__name__}")
            return {
                'status': 'ERROR',
                'root_mfa_enabled': False,
                'users_with_mfa': [],
                'users_without_mfa': [],
                'message': f"IAM MFA audit error: {type(e).__name__}",
                'raw_data': {'error': type(e).__name__}
            }

    def audit_security_groups(self) -> Dict[str, Any]:
        """
        Audit EC2 security groups for dangerous open ports.
        
        CRITICAL CHECK: Flag any group allowing 0.0.0.0/0 on port 22 (SSH) or 3389 (RDP).
        
        Returns:
            {
                'status': 'PASS' | 'FAIL',
                'compliant_groups': [...],
                'non_compliant_groups': [...],
                'message': str,
                'raw_data': {...}
            }
        """
        try:
            ec2 = self.session.client('ec2')
            
            # Describe all security groups
            response = ec2.describe_security_groups()
            groups = response.get('SecurityGroups', [])
            
            if not groups:
                return {
                    'status': 'PASS',
                    'compliant_groups': [],
                    'non_compliant_groups': [],
                    'total_groups': 0,
                    'message': 'No security groups found',
                    'raw_data': {'group_count': 0}
                }
            
            compliant = []
            non_compliant = []
            
            for group in groups:
                group_info = {
                    'group_id': group.get('GroupId'),
                    'group_name': group.get('GroupName'),
                    'vpc_id': group.get('VpcId'),
                    'dangerous_rules': []
                }
                
                has_dangerous_rule = False
                
                # Check inbound rules
                for rule in group.get('IpPermissions', []):
                    from_port = rule.get('FromPort', 0)
                    to_port = rule.get('ToPort', 65535)
                    
                    # Check for ports 22 and 3389
                    dangerous_ports = [22, 3389]
                    
                    for ip_range in rule.get('IpRanges', []):
                        cidr = ip_range.get('CidrIp', '')
                        
                        if cidr == '0.0.0.0/0':
                            # Check if port is in range
                            if (from_port <= 22 <= to_port or from_port <= 3389 <= to_port):
                                protocol = rule.get('IpProtocol', 'tcp')
                                dangerous_rule = {
                                    'protocol': protocol,
                                    'port_range': f"{from_port}-{to_port}",
                                    'open_to': cidr,
                                    'description': ip_range.get('Description', 'N/A')
                                }
                                group_info['dangerous_rules'].append(dangerous_rule)
                                has_dangerous_rule = True
                
                if has_dangerous_rule:
                    non_compliant.append(group_info)
                else:
                    compliant.append(group_info)
            
            all_compliant = len(non_compliant) == 0
            status = 'PASS' if all_compliant else 'FAIL'
            
            return {
                'status': status,
                'compliant_groups': compliant,
                'non_compliant_groups': non_compliant,
                'total_groups': len(groups),
                'compliant_count': len(compliant),
                'non_compliant_count': len(non_compliant),
                'message': f"Security Groups: {len(compliant)}/{len(groups)} groups are compliant",
                'raw_data': {
                    'total': len(groups),
                    'compliant': len(compliant),
                    'non_compliant': len(non_compliant)
                }
            }
        
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            logger.error(f"Security Groups audit failed: {error_code}")
            return {
                'status': 'ERROR',
                'compliant_groups': [],
                'non_compliant_groups': [],
                'total_groups': 0,
                'message': f"Security Groups audit error: {error_code}",
                'raw_data': {'error': error_code}
            }
        except Exception as e:
            logger.error(f"Security Groups audit failed: {type(e).__name__}")
            return {
                'status': 'ERROR',
                'compliant_groups': [],
                'non_compliant_groups': [],
                'total_groups': 0,
                'message': f"Security Groups audit error: {type(e).__name__}",
                'raw_data': {'error': type(e).__name__}
            }

    def audit_unused_iam_users(self) -> Dict[str, Any]:
        """
        Audit IAM users for unused credentials (90+ days without password use).
        
        CRITICAL CHECK: Flag users whose passwords haven't been used in 90+ days.
        
        Returns:
            {
                'status': 'PASS' | 'FAIL',
                'active_users': [...],
                'stale_users': [...],
                'message': str,
                'raw_data': {...}
            }
        """
        try:
            iam = self.session.client('iam')
            from datetime import datetime, timedelta
            
            try:
                # Generate credential report
                iam.generate_credential_report()
                import time
                time.sleep(2)
                report_response = iam.get_credential_report()
                
                import csv
                import io
                
                report_csv = report_response['Content'].decode('utf-8')
                reader = csv.DictReader(io.StringIO(report_csv))
                
                active_users = []
                stale_users = []
                
                ninety_days_ago = datetime.utcnow() - timedelta(days=90)
                
                for row in reader:
                    user_name = row.get('user', '')
                    
                    if user_name == '<root_account>':
                        continue  # Root handled separately
                    
                    password_enabled = row.get('password_enabled', 'false').lower() == 'true'
                    
                    if not password_enabled:
                        continue  # Skip programmatic-only users
                    
                    password_last_used = row.get('password_last_used', 'N/A')
                    
                    user_info = {
                        'username': user_name,
                        'password_enabled': password_enabled,
                        'password_last_used': password_last_used,
                        'created': row.get('arn', '').split(':')[5].split('/')[1] if ':' in row.get('arn', '') else 'N/A'
                    }
                    
                    # Parse password_last_used if available
                    if password_last_used != 'N/A' and password_last_used != 'never':
                        try:
                            last_used_date = datetime.fromisoformat(password_last_used.replace('Z', '+00:00'))
                            if last_used_date < ninety_days_ago:
                                stale_users.append(user_info)
                            else:
                                active_users.append(user_info)
                        except ValueError:
                            # Could not parse date, treat as stale
                            stale_users.append(user_info)
                    else:
                        # Never used or N/A
                        stale_users.append(user_info)
                
                all_active = len(stale_users) == 0
                status = 'PASS' if all_active else 'FAIL'
                
                return {
                    'status': status,
                    'active_users': active_users,
                    'stale_users': stale_users,
                    'message': f"IAM Users: {len(active_users)} active, {len(stale_users)} stale (90+ days)",
                    'raw_data': {
                        'active_count': len(active_users),
                        'stale_count': len(stale_users),
                        'threshold_days': 90
                    }
                }
            
            except ClientError as e:
                logger.warning(f"Could not retrieve credential report: {e}")
                return {
                    'status': 'UNKNOWN',
                    'active_users': [],
                    'stale_users': [],
                    'message': f"Could not verify IAM user activity: {e.response.get('Error', {}).get('Code', 'Unknown')}",
                    'raw_data': {'error': 'Credential report unavailable'}
                }
        
        except Exception as e:
            logger.error(f"IAM unused users audit failed: {type(e).__name__}")
            return {
                'status': 'ERROR',
                'active_users': [],
                'stale_users': [],
                'message': f"IAM users audit error: {type(e).__name__}",
                'raw_data': {'error': type(e).__name__}
            }

    def audit_cloudtrail(self) -> Dict[str, Any]:
        """
        Audit CloudTrail configuration for multi-region logging.
        
        CRITICAL CHECK: At least one multi-region trail must be active.
        Ensures comprehensive API logging across all AWS regions.
        
        Returns:
            {
                'status': 'PASS' | 'FAIL',
                'multi_region_trails': [...],
                'single_region_trails': [...],
                'message': str,
                'raw_data': {...}
            }
        """
        try:
            cloudtrail = self.session.client('cloudtrail')
            
            # Describe all trails
            response = cloudtrail.describe_trails()
            trails = response.get('trailList', [])
            
            if not trails:
                return {
                    'status': 'FAIL',
                    'multi_region_trails': [],
                    'single_region_trails': [],
                    'message': 'No CloudTrail trails configured',
                    'raw_data': {'trail_count': 0}
                }
            
            multi_region = []
            single_region = []
            
            # Check each trail
            for trail in trails:
                trail_info = {
                    'name': trail.get('Name'),
                    'is_multi_region': trail.get('IsMultiRegionTrail', False),
                    's3_bucket': trail.get('S3BucketName'),
                    'home_region': trail.get('HomeRegion')
                }
                
                # Get trail status
                try:
                    status_response = cloudtrail.get_trail_status(Name=trail['TrailARN'])
                    is_logging = status_response.get('IsLogging', False)
                    trail_info['is_logging'] = is_logging
                except ClientError:
                    trail_info['is_logging'] = False
                
                if trail.get('IsMultiRegionTrail', False):
                    multi_region.append(trail_info)
                else:
                    single_region.append(trail_info)
            
            # Compliant if at least one multi-region trail is active
            has_active_multi_region = any(
                t.get('is_logging', False) for t in multi_region
            )
            
            status = 'PASS' if has_active_multi_region else 'FAIL'
            
            return {
                'status': status,
                'multi_region_trails': multi_region,
                'single_region_trails': single_region,
                'active_multi_region_count': sum(
                    1 for t in multi_region if t.get('is_logging', False)
                ),
                'message': (
                    f"CloudTrail: {len(multi_region)} multi-region trail(s) configured, "
                    f"{sum(1 for t in multi_region if t.get('is_logging', False))} active"
                ),
                'raw_data': {
                    'total_trails': len(trails),
                    'multi_region_count': len(multi_region),
                    'single_region_count': len(single_region),
                    'has_active_multi_region': has_active_multi_region
                }
            }
        
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            logger.error(f"CloudTrail audit failed: {error_code}")
            return {
                'status': 'ERROR',
                'multi_region_trails': [],
                'single_region_trails': [],
                'message': f"CloudTrail audit error: {error_code}",
                'raw_data': {'error': error_code}
            }
        except Exception as e:
            logger.error(f"CloudTrail audit failed: {type(e).__name__}")
            return {
                'status': 'ERROR',
                'multi_region_trails': [],
                'single_region_trails': [],
                'message': f"CloudTrail audit error: {type(e).__name__}",
                'raw_data': {'error': type(e).__name__}
            }
