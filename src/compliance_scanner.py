import os
import json
import boto3
import glob
import hashlib
import requests
import time
import re
from datetime import datetime

class ComplianceScanner:
    def __init__(self, profile_name=None):
        # Use AWS profile for local development, OIDC for GitHub Actions
        session = boto3.Session(profile_name=profile_name)
        self.region = os.getenv('AWS_REGION', 'us-east-1')
        self.bedrock = session.client('bedrock-runtime', region_name=self.region)
        self.kb_id = os.getenv('BEDROCK_KB_ID', '6OFPQYR1JK')
        self.model_id = os.getenv('BEDROCK_MODEL_ID', 'anthropic.claude-3-haiku-20240307-v1:0')
        self.ai_calls = 0
        self.total_cost = 0
        self.cache_file = '.compliance_cache.json'
        self.file_cache = self.load_cache()
        
        # Compliance-focused prompts
        self.compliance_context = {
            'PCI-DSS': 'PCI-DSS requires encryption of cardholder data, secure transmission, access controls, and regular security testing.',
            'SOC2': 'SOC2 Type II requires security controls for confidentiality, availability, processing integrity, and privacy.',
            'HIPAA': 'HIPAA requires safeguards for PHI including encryption, access controls, audit logs, and breach notification.',
            'GDPR': 'GDPR requires data protection by design, consent management, data minimization, and breach notification.',
            'OWASP': 'OWASP Top 10 covers injection, broken authentication, sensitive data exposure, and security misconfigurations.'
        }
    
    def load_cache(self):
        """Load file hash cache from S3 in CI/CD or local file"""
        cache_data = {}
        
        # Try S3 global cache first (for CI/CD)
        s3_bucket = os.getenv('REPORTS_S3_BUCKET')
        if s3_bucket:
            try:
                s3 = boto3.client('s3', region_name=self.region)
                response = s3.get_object(Bucket=s3_bucket, Key='cache/global_compliance_cache.json')
                cache_data = json.loads(response['Body'].read().decode('utf-8'))
                print(f"📋 Loaded global cache from S3: {len(cache_data)} files")
                return cache_data
            except Exception as e:
                print(f"📋 No S3 global cache found, starting fresh")
        
        # Fallback to local cache
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    cache_data = json.load(f)
                print(f"📋 Loaded local cache: {len(cache_data)} files")
        except Exception as e:
            print(f"⚠️ Cache load error: {e}")
        
        return cache_data
    
    def post_pr_comment(self, report):
        """Post comprehensive PR comment with vulnerability and compliance details"""
        github_token = os.environ.get('GITHUB_TOKEN')
        repo = os.environ.get('GITHUB_REPOSITORY')  # format: owner/repo
        pr_number = os.environ.get('GITHUB_PR_NUMBER')
        
        if not all([github_token, repo, pr_number]):
            print("⚠️ Missing GitHub environment variables for PR commenting")
            return
        
        # Generate comment content
        vuln_summary = report.get('vulnerability_summary', {})
        total_issues = report.get('total_issues', 0)
        total_vulns = vuln_summary.get('total_vulnerabilities', 0)
        critical_vulns = vuln_summary.get('critical_vulns', 0)
        high_vulns = vuln_summary.get('high_vulns', 0)
        
        # Build comment
        comment = f"""## 🔍 ThreatLens Security Scan Results

### 📊 Summary
- **Total Issues**: {total_issues}
- **Vulnerabilities**: {total_vulns} (Critical: {critical_vulns}, High: {high_vulns})
- **CVE Findings**: {vuln_summary.get('cve_findings', 0)}
- **GitHub Advisories**: {vuln_summary.get('github_advisories', 0)}
- **Files Scanned**: {report.get('files_scanned', 0)}

### 🚨 Vulnerabilities Found
"""
        
        # Add vulnerability details (all severities)
        vulnerabilities_found = False
        for result in report.get('results', []):
            for issue in result.get('issues', []):
                if issue.get('type') == 'vulnerability':
                    vulnerabilities_found = True
                    severity_emoji = {'CRITICAL': '🔴', 'HIGH': '🟠', 'MEDIUM': '🟡', 'LOW': '🟢'}.get(issue.get('severity'), '⚪')
                    comment += f"- {severity_emoji} **{issue.get('vulnerability_id')}** in `{result.get('filepath')}` (Package: {issue.get('package')})\n"
                    comment += f"  - Severity: {issue.get('severity')} | Source: {issue.get('source')}\n"
        
        if not vulnerabilities_found:
            comment += "✅ No vulnerabilities found\n"
        
        comment += f"""
### 📋 Compliance Violations
"""
        
        # Add compliance summary
        compliance_summary = report.get('compliance_summary', {})
        if compliance_summary:
            for standard, data in list(compliance_summary.items())[:5]:  # Top 5
                comment += f"- **{standard}**: {data.get('issues', 0)} issues"
                if data.get('critical', 0) > 0:
                    comment += f" (⚠️ {data.get('critical', 0)} critical)"
                comment += "\n"
        
        comment += f"""
### 🛠️ Next Steps
"""
        
        if critical_vulns > 0 or report.get('by_severity', {}).get('critical', 0) > 0:
            comment += "❌ **PR BLOCKED** - Critical issues must be resolved before merging\n"
            comment += "1. Review critical vulnerabilities above\n"
            comment += "2. Update dependencies or apply patches\n"
            comment += "3. Re-run scan after fixes\n"
        else:
            comment += "✅ No critical issues blocking merge\n"
            comment += "1. Review high/medium severity findings\n"
            comment += "2. Consider addressing before production deployment\n"
        
        # Post comment
        try:
            url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
            headers = {
                'Authorization': f'Bearer {github_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            payload = {'body': comment}
            
            response = requests.post(url, json=payload, headers=headers)
            if response.status_code == 201:
                print(f"✅ Posted PR comment to #{pr_number}")
            else:
                print(f"⚠️ Failed to post PR comment: {response.status_code}")
                
        except Exception as e:
            print(f"❌ PR comment error: {e}")

    def save_cache(self):
        """Save file hash cache to both S3 and local"""
        # Save locally
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.file_cache, f, indent=2)
        except Exception as e:
            print(f"⚠️ Local cache save error: {e}")
        
        # Save to S3 for CI/CD persistence (global cache, not PR-specific)
        s3_bucket = os.getenv('REPORTS_S3_BUCKET')
        if s3_bucket:
            try:
                s3 = boto3.client('s3', region_name=self.region)
                s3.put_object(
                    Bucket=s3_bucket,
                    Key='cache/global_compliance_cache.json',  # Global cache for all PRs/branches
                    Body=json.dumps(self.file_cache, indent=2),
                    ContentType='application/json'
                )
                print(f"📋 Global cache saved to S3: {len(self.file_cache)} files")
            except Exception as e:
                print(f"⚠️ S3 cache save error: {e}")
    
    def get_file_hash(self, filepath):
        """Get SHA256 hash of file content"""
        try:
            with open(filepath, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception:
            return None
    
    def is_file_changed(self, filepath):
        """Check if file has changed since last scan"""
        current_hash = self.get_file_hash(filepath)
        if not current_hash:
            return True
        
        cached_data = self.file_cache.get(filepath, {})
        return cached_data.get('hash') != current_hash
    
    def update_file_cache(self, filepath, scan_result):
        """Update cache with new scan result"""
        file_hash = self.get_file_hash(filepath)
        if file_hash:
            self.file_cache[filepath] = {
                'hash': file_hash,
                'result': scan_result,
                'timestamp': datetime.now().isoformat()
            }
    
    def get_cached_result(self, filepath):
        """Get cached scan result if file unchanged"""
        if not self.is_file_changed(filepath):
            cached_data = self.file_cache.get(filepath, {})
            if 'result' in cached_data:
                print(f"   📋 Using cached result (file unchanged)")
                return cached_data['result']
        return None
    
    def get_scan_context(self):
        """Get scan context - CI/CD info or local timestamp"""
        # Check if running in GitHub Actions
        if os.getenv('GITHUB_ACTIONS'):
            repo_name = os.getenv('GITHUB_REPOSITORY', 'unknown-repo')
            branch_name = os.getenv('GITHUB_REF_NAME', 'unknown-branch')
            pr_number = os.getenv('GITHUB_EVENT_NUMBER') or os.getenv('GITHUB_PR_NUMBER')
            
            if pr_number:
                scan_name = f"{repo_name}/PR-{pr_number}"
                scan_id = f"{repo_name.replace('/', '_')}_PR_{pr_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            else:
                scan_name = f"{repo_name}/{branch_name}"
                scan_id = f"{repo_name.replace('/', '_')}_{branch_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            return {
                'is_cicd': True,
                'scan_name': scan_name,
                'scan_id': scan_id,
                'repo_name': repo_name,
                'branch_name': branch_name,
                'pr_number': pr_number,
                'runner': 'GitHub Actions'
            }
        
        # Check for other CI/CD systems
        elif os.getenv('CI'):
            ci_system = 'Unknown CI'
            if os.getenv('JENKINS_URL'): ci_system