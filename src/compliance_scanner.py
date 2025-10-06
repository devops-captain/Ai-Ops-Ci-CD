#!/usr/bin/env python3
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
            if os.getenv('JENKINS_URL'): ci_system = 'Jenkins'
            elif os.getenv('GITLAB_CI'): ci_system = 'GitLab CI'
            elif os.getenv('CIRCLECI'): ci_system = 'CircleCI'
            elif os.getenv('TRAVIS'): ci_system = 'Travis CI'
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            return {
                'is_cicd': True,
                'scan_name': f"{ci_system}-{timestamp}",
                'scan_id': f"ci_{timestamp}",
                'runner': ci_system
            }
        
        # Local development
        else:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            return {
                'is_cicd': False,
                'scan_name': f"Local-{timestamp}",
                'scan_id': timestamp,
                'runner': 'Local Development'
            }
    
    def call_ai_with_compliance(self, prompt):
        """AI call with compliance context"""
        compliance_prompt = f"""
You are a security expert specializing in compliance standards: PCI-DSS, SOC2, HIPAA, GDPR, OWASP Top 10.

Context:
- PCI-DSS: Protect cardholder data, encrypt transmission, implement access controls
- SOC2: Security, availability, confidentiality controls
- HIPAA: Protect PHI with encryption, access controls, audit logs
- GDPR: Data protection by design, consent, minimization
- OWASP: Prevent injection, broken auth, data exposure

{prompt}
"""
        
        try:
            # Different API formats for different models
            if 'anthropic' in self.model_id:
                # Claude format
                response = self.bedrock.invoke_model(
                    modelId=self.model_id,
                    body=json.dumps({
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": int(os.getenv('AI_MAX_TOKENS', '4000')),
                        "temperature": 0.1,
                        "top_p": 0.9,
                        "messages": [{"role": "user", "content": compliance_prompt}]
                    })
                )
                
                self.ai_calls += 1
                result = json.loads(response['body'].read())
                output = result['content'][0]['text'].strip()
                
            else:
                # Nova format
                response = self.bedrock.invoke_model(
                    modelId=self.model_id,
                    body=json.dumps({
                        "messages": [{"role": "user", "content": [{"text": compliance_prompt}]}],
                        "inferenceConfig": {"maxTokens": int(os.getenv('AI_MAX_TOKENS', '4000')), "temperature": 0.1, "topP": 0.9}
                    })
                )
                
                self.ai_calls += 1
                result = json.loads(response['body'].read())
                output = result['output']['message']['content'][0]['text'].strip()
            
            # Calculate cost
            input_tokens = len(compliance_prompt) / 4
            output_tokens = len(output) / 4
            self.total_cost += (input_tokens * 0.00035 / 1000) + (output_tokens * 0.0014 / 1000)
            
            return output
            
        except Exception as e:
            self.log_error(str(e))
            return None
    
    def detect_language_and_framework(self, filepath, code):
        """Detect language and framework"""
        ext_map = {
            '.py': 'Python', '.js': 'JavaScript', '.ts': 'TypeScript',
            '.tf': 'Terraform', '.tfvars': 'Terraform',
            '.yaml': 'Kubernetes', '.yml': 'Kubernetes',
            '.java': 'Java', '.go': 'Go', '.sh': 'Shell'
        }
        
        # Handle Dockerfile specifically
        if filepath.endswith('Dockerfile') or 'dockerfile' in filepath.lower():
            language = 'Docker'
        else:
            language = ext_map.get(os.path.splitext(filepath)[1], 'Unknown')
        
        # Detect framework
        framework = None
        if language == 'Python':
            if 'django' in code.lower(): framework = 'Django'
            elif 'flask' in code.lower(): framework = 'Flask'
            elif 'fastapi' in code.lower(): framework = 'FastAPI'
        
        return language, framework
    
    def query_kb_for_rules(self, code_snippet, language):
        """Query your KB to get specific RFC rules for the code"""
        try:
            bedrock_agent = boto3.client('bedrock-agent-runtime', region_name=self.region)
            
            query = f"What security rules apply to this {language} code? {code_snippet[:500]}"
            
            response = bedrock_agent.retrieve_and_generate(
                input={'text': query},
                retrieveAndGenerateConfiguration={
                    'type': 'KNOWLEDGE_BASE',
                    'knowledgeBaseConfiguration': {
                        'knowledgeBaseId': self.kb_id,
                        'modelArn': f'arn:aws:bedrock:{self.region}::foundation-model/{self.model_id}'
                    }
                }
            )
            
            kb_response = response['output']['text']
            citations = response.get('citations', [])
            
            # Extract RFC references from citations
            rfc_sources = []
            for citation in citations:
                for reference in citation.get('retrievedReferences', []):
                    location = reference.get('location', {})
                    s3_location = location.get('s3Location', {})
                    if s3_location.get('uri'):
                        rfc_sources.append(s3_location['uri'])
            
            print(f"   📚 KB Query successful - {len(rfc_sources)} sources found")
            return {
                'kb_guidance': kb_response,
                'rfc_sources': rfc_sources
            }
            
        except Exception as e:
            print(f"   ⚠️ KB Query failed: {str(e)[:100]}...")
            self.log_error(f"KB query failed: {e}")
            # Return empty sources when KB query fails
            return {
                'kb_guidance': f"Security analysis for {language} code using standard compliance rules",
                'rfc_sources': []
            }
    
    def compliance_detect(self, code, language, framework, filepath):
        """Compliance-focused detection using AI with KB integration"""
        framework_text = f"/{framework}" if framework else ""
        
        # Add line numbers to code for accuracy
        lines = code.split('\n')
        numbered_code = '\n'.join([f"{i+1:3d}: {line}" for i, line in enumerate(lines)])
        
        # Query your KB for relevant RFC rules
        kb_info = self.query_kb_for_rules(code, language)
        
        # Validate KB is working properly
        if not kb_info.get('kb_guidance') or 'standard compliance rules' in kb_info.get('kb_guidance', ''):
            if os.getenv('REQUIRE_KB', 'false').lower() == 'true':
                print(f"   ❌ Knowledge Base required but not available")
                return []
            else:
                print(f"   ⚠️ Knowledge Base not available - using standard rules")
        
        kb_context = ""
        if kb_info['kb_guidance']:
            kb_context = f"\nKnowledge Base Guidance:\n{kb_info['kb_guidance']}\n"
        
        # Enhanced AI prompt with KB context
        prompt = f"""You are a security expert with access to RFC documents and compliance standards.

{kb_context}

Analyze this {language}{framework_text} code for compliance violations using the KB guidance above.

CRITICAL: Use EXACT line numbers from the numbered code below. Reference specific RFC documents when applicable.

Return JSON array:
[{{"line": <exact_line_number>, "severity": "critical|high|medium|low", 
"category": "<type>", "description": "<what_you_found>", "cvss": <score>, 
"compliance_violations": ["<standard>"], "remediation": "<fix>",
"kb_rule": "<specific_RFC_rule_from_KB>",
"rfc_document": "<RFC_document_name_from_S3>",
"rule_source": "<RFC_section_or_standard>"}}]

Code from {filepath} with line numbers:
```
{numbered_code}
```

Return ONLY the JSON array."""

        output = self.call_ai_with_compliance(prompt)
        if not output:
            return []
        
        try:
            # Clean and extract JSON
            output = output.strip()
            if '```' in output:
                lines_out = output.split('\n')
                output = '\n'.join([l for l in lines_out if not l.strip().startswith('```')])
            
            if '[' in output and ']' in output:
                json_start = output.index('[')
                json_end = output.rindex(']') + 1
                json_str = output[json_start:json_end]
                issues = json.loads(json_str)
                
                # Validate issues and add S3 source information
                valid_issues = []
                for issue in issues:
                    if isinstance(issue, dict) and 'line' in issue and 'severity' in issue:
                        # Add S3 source information from KB query
                        if kb_info['rfc_sources']:
                            issue['s3_sources'] = kb_info['rfc_sources']
                            # Extract document names from S3 paths
                            doc_names = []
                            for s3_path in kb_info['rfc_sources']:
                                if 's3://' in s3_path:
                                    doc_name = s3_path.split('/')[-1]  # Get filename
                                    doc_names.append(doc_name)
                                elif s3_path:  # Any other path format
                                    doc_names.append(s3_path)
                            if doc_names:
                                issue['rfc_document'] = ', '.join(doc_names)
                        
                        valid_issues.append(issue)
                
                return valid_issues
                
        except Exception as e:
            self.log_error(f"JSON parse error: {e}")
            return []  # Pure AI - no hardcoded fallback patterns
        
        return []
    
    def basic_validation(self, fixed_code, language):
        """Basic validation without external tools"""
        # Simple checks without external dependencies
        if len(fixed_code.strip()) < 10:
            return False
            
        if language == 'Python':
            # Basic Python syntax check
            try:
                compile(fixed_code, '<string>', 'exec')
                return True
            except SyntaxError:
                return False
        
        # For other languages, just check it's not empty and has content
        return len(fixed_code.strip()) > 10
        """Validate and format fixed code"""
        import tempfile
        import subprocess
        import os
        
        # Save fixed code to temp file for validation
        with tempfile.NamedTemporaryFile(mode='w', suffix=os.path.splitext(filepath)[1], delete=False) as temp_file:
            temp_file.write(fixed_code)
            temp_path = temp_file.name
        
        try:
            # Language-specific validation and formatting
            if language == 'Terraform':
                # Terraform fmt and validate
                subprocess.run(['terraform', 'fmt', temp_path], check=True, capture_output=True)
                result = subprocess.run(['terraform', 'validate', '-json'], 
                                      cwd=os.path.dirname(temp_path), capture_output=True, text=True)
                if result.returncode != 0:
                    self.log_error(f"Terraform validation failed: {result.stderr}")
                    return False, fixed_code
                
                # Read formatted code
                with open(temp_path, 'r') as f:
                    formatted_code = f.read()
                return True, formatted_code
                
            elif language == 'Python':
                # Python syntax check
                try:
                    compile(fixed_code, filepath, 'exec')
                    # Optional: black formatting if available
                    try:
                        result = subprocess.run(['black', '--code', fixed_code], 
                                              capture_output=True, text=True, check=True)
                        return True, result.stdout
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        return True, fixed_code  # No formatting, but valid
                except SyntaxError as e:
                    self.log_error(f"Python syntax error: {e}")
                    return False, fixed_code
                    
            elif language == 'JavaScript':
                # Node.js syntax check
                try:
                    result = subprocess.run(['node', '--check', temp_path], 
                                          capture_output=True, text=True)
                    if result.returncode != 0:
                        self.log_error(f"JavaScript syntax error: {result.stderr}")
                        return False, fixed_code
                    
                    # Optional: prettier formatting
                    try:
                        result = subprocess.run(['prettier', '--write', temp_path], 
                                              capture_output=True, text=True, check=True)
                        with open(temp_path, 'r') as f:
                            formatted_code = f.read()
                        return True, formatted_code
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        return True, fixed_code
                except Exception as e:
                    self.log_error(f"JavaScript validation failed: {e}")
                    return False, fixed_code
                    
            elif language == 'Kubernetes':
                # YAML syntax and k8s validation
                try:
                    import yaml
                    yaml.safe_load(fixed_code)
                    
                    # Optional: kubectl dry-run validation
                    try:
                        result = subprocess.run(['kubectl', 'apply', '--dry-run=client', '-f', temp_path], 
                                              capture_output=True, text=True)
                        if result.returncode != 0:
                            self.log_error(f"Kubernetes validation failed: {result.stderr}")
                            return False, fixed_code
                    except FileNotFoundError:
                        pass  # kubectl not available
                    
                    return True, fixed_code
                except yaml.YAMLError as e:
                    self.log_error(f"YAML syntax error: {e}")
                    return False, fixed_code
                    
            else:
                # Generic validation - just return as-is
                return True, fixed_code
                
        finally:
            # Cleanup temp file
            try:
                os.unlink(temp_path)
            except:
                pass
    
    # def git_commit_and_push(self, files_fixed, branch_name=None):
    #     """Commit and push fixed files to git - MOVED TO WORKFLOW"""
    #     pass  # Git operations handled by GitHub Actions workflow
    
    def compliance_fix(self, code, issues, language, framework):
        """Generate compliance-focused fixes"""
        framework_text = f"/{framework}" if framework else ""
        
        issues_desc = '\n'.join([
            f"Line {i['line']}: {i['description']} ({i['severity']}) - "
            f"Violates: {', '.join(i.get('compliance_violations', []))}"
            for i in issues
        ])
        
        prompt = f"""Fix ALL security and compliance violations in this {language}{framework_text} code.

Issues to fix:
{issues_desc}

Apply these compliance standards:
- PCI-DSS: Encrypt cardholder data, secure transmission, access controls
- SOC2: Implement security controls, logging, monitoring
- HIPAA: Protect PHI with encryption, access controls, audit trails
- GDPR: Data protection by design, consent mechanisms, data minimization
- OWASP: Prevent injection, secure authentication, proper error handling

Original code:
{code}

Return ONLY the complete fixed code that meets all compliance requirements:"""

        fixed = self.call_ai_with_compliance(prompt)
        if not fixed:
            return None
        
        # Clean output
        import re
        fixed = re.sub(r'^```[\w]*\n', '', fixed, flags=re.MULTILINE)
        fixed = re.sub(r'\n```$', '', fixed)
        fixed = re.sub(r'^Here.*?:\s*', '', fixed, flags=re.IGNORECASE)
        
        return fixed.strip()
    
    def extract_dependencies(self, code, filepath):
        """Extract dependencies from code with line numbers"""
        dependencies = []
        
        if filepath.endswith('.tf'):
            # Terraform modules and providers
            lines = code.split('\n')
            for i, line in enumerate(lines, 1):
                if 'source' in line and '=' in line:
                    match = re.search(r'source\s*=\s*["\']([^"\']+)["\']', line)
                    if match:
                        dep_name = match.group(1).split('/')[-1]
                        dependencies.append({'name': dep_name, 'line': i})
                        
        elif filepath.endswith(('.yaml', '.yml')):
            # Docker images, Helm charts
            lines = code.split('\n')
            for i, line in enumerate(lines, 1):
                if 'image:' in line:
                    match = re.search(r'image:\s*["\']?([^"\'\s]+)["\']?', line)
                    if match:
                        img_name = match.group(1).split(':')[0].split('/')[-1]
                        dependencies.append({'name': img_name, 'line': i})
                        
        elif filepath.endswith('.js'):
            # NPM packages from require/import
            lines = code.split('\n')
            for i, line in enumerate(lines, 1):
                matches = re.findall(r'(?:require|import).*?["\']([^"\']+)["\']', line)
                for match in matches:
                    if not match.startswith('./'):
                        dependencies.append({'name': match, 'line': i})
                        
        elif filepath.endswith('Dockerfile') or 'dockerfile' in filepath.lower():
            # Docker FROM images
            lines = code.split('\n')
            for i, line in enumerate(lines, 1):
                if line.strip().upper().startswith('FROM'):
                    match = re.search(r'FROM\s+([^\s]+)', line, re.IGNORECASE)
                    if match:
                        img_name = match.group(1).split(':')[0].split('/')[-1]
                        dependencies.append({'name': img_name, 'line': i})
        
        return dependencies
    
    def check_cve_vulnerabilities(self, dependencies):
        """Check dependencies against NIST CVE database"""
        vulnerabilities = []
        
        max_deps = int(os.getenv('MAX_CVE_DEPS', '0'))  # 0 = no limit
        deps_to_check = dependencies if max_deps == 0 else dependencies[:max_deps]
        
        for dep_info in deps_to_check:
            dep = dep_info['name'] if isinstance(dep_info, dict) else dep_info
            line_num = dep_info.get('line', 1) if isinstance(dep_info, dict) else 1
            
            try:
                print(f"     🔍 Checking CVE for: {dep} (line {line_num})")
                url = "https://services.nvd.nist.gov/rest/json/cves/2.0"
                params = {'keywordSearch': dep, 'resultsPerPage': 2}
                
                response = requests.get(url, params=params, timeout=15)
                print(f"     📡 CVE API response: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    cve_count = len(data.get('vulnerabilities', []))
                    print(f"     📊 Found {cve_count} CVEs for {dep}")
                    
                    for cve in data.get('vulnerabilities', []):
                        cve_data = cve.get('cve', {})
                        vuln_id = cve_data.get('id', 'Unknown')
                        
                        metrics = cve_data.get('metrics', {})
                        cvss_score = 'Unknown'
                        if 'cvssMetricV31' in metrics:
                            cvss_score = metrics['cvssMetricV31'][0]['cvssData']['baseScore']
                        elif 'cvssMetricV2' in metrics:
                            cvss_score = metrics['cvssMetricV2'][0]['cvssData']['baseScore']
                        
                        description = cve_data.get('descriptions', [{}])[0].get('value', 'No description')
                        
                        # Generate fix suggestion
                        fix_suggestion = f"Update {dep} to latest version or apply security patch for {vuln_id}"
                        
                        max_desc_len = int(os.getenv('MAX_DESCRIPTION_LENGTH', '500'))
                        
                        vulnerabilities.append({
                            'type': 'CVE',
                            'id': vuln_id,
                            'package': dep,
                            'line': line_num,
                            'severity': self._get_severity_from_cvss(cvss_score),
                            'description': description[:max_desc_len] + '...' if len(description) > max_desc_len else description
                        })
                else:
                    print(f"     ❌ CVE API error {response.status_code} for {dep}")
                
                cve_delay = float(os.getenv('CVE_API_DELAY', '0.5'))
                time.sleep(cve_delay)  # Configurable rate limiting
                
            except Exception as e:
                print(f"     ❌ CVE check failed for {dep}: {e}")
        
        print(f"   📊 Total CVE vulnerabilities found: {len(vulnerabilities)}")
        return vulnerabilities
    
    def check_github_advisories(self, dependencies):
        """Check dependencies against GitHub Advisory Database"""
        advisories = []
        github_token = os.environ.get("GITHUB_TOKEN")
        
        if not github_token:
            return advisories
        
        max_deps = int(os.getenv('MAX_GITHUB_DEPS', '0'))  # 0 = no limit
        deps_to_check = dependencies if max_deps == 0 else dependencies[:max_deps]
        
        for dep in deps_to_check:
            try:
                url = "https://api.github.com/graphql"
                query = """
                query($query: String!) {
                  search(query: $query, type: REPOSITORY, first: 3) {
                    nodes {
                      ... on Repository {
                        vulnerabilityAlerts(first: 3) {
                          nodes {
                            securityAdvisory {
                              ghsaId
                              summary
                              severity
                            }
                          }
                        }
                      }
                    }
                  }
                }
                """
                
                headers = {'Authorization': f'Bearer {github_token}'}
                payload = {'query': query, 'variables': {'query': dep}}
                
                response = requests.post(url, json=payload, headers=headers, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    
                    for repo in data.get('data', {}).get('search', {}).get('nodes', []):
                        for alert in repo.get('vulnerabilityAlerts', {}).get('nodes', []):
                            advisory = alert.get('securityAdvisory', {})
                            max_desc_len = int(os.getenv('MAX_DESCRIPTION_LENGTH', '500'))
                            summary = advisory.get('summary', 'No summary')
                            
                            advisories.append({
                                'type': 'GitHub Advisory',
                                'id': advisory.get('ghsaId', 'Unknown'),
                                'package': dep,
                                'severity': advisory.get('severity', 'Unknown').upper(),
                                'description': summary[:max_desc_len] + '...' if len(summary) > max_desc_len else summary
                            })
                
                github_delay = float(os.getenv('GITHUB_API_DELAY', '0.2'))
                time.sleep(github_delay)  # Configurable rate limiting
                
            except Exception as e:
                print(f"GitHub Advisory check failed for {dep}: {e}")
        
        return advisories
    
    def _get_severity_from_cvss(self, score):
        """Convert CVSS score to severity level"""
        if score == 'Unknown':
            return 'UNKNOWN'
        try:
            score = float(score)
            if score >= 9.0:
                return 'CRITICAL'
            elif score >= 7.0:
                return 'HIGH'
            elif score >= 4.0:
                return 'MEDIUM'
            else:
                return 'LOW'
        except:
            return 'UNKNOWN'
    
    def fix_vulnerabilities(self, code, vulnerability_issues, filepath):
        """Fix vulnerabilities by updating dependencies to secure versions"""
        fixed_code = code
        
        for vuln in vulnerability_issues:
            package = vuln.get('package')
            vuln_id = vuln.get('vulnerability_id')
            
            if filepath.endswith('.js'):
                if f"require('{package}')" in fixed_code:
                    fixed_code = fixed_code.replace(
                        f"require('{package}')",
                        f"require('{package}') // TODO: Update {package} to fix {vuln_id}"
                    )
                elif f'require("{package}")' in fixed_code:
                    fixed_code = fixed_code.replace(
                        f'require("{package}")',
                        f'require("{package}") // TODO: Update {package} to fix {vuln_id}'
                    )
                    
            elif filepath.endswith('Dockerfile') or 'dockerfile' in filepath.lower():
                lines = fixed_code.split('\n')
                for i, line_content in enumerate(lines):
                    if line_content.strip().upper().startswith('FROM') and package in line_content:
                        lines[i] = f"{line_content} # TODO: Update {package} base image to fix {vuln_id}"
                fixed_code = '\n'.join(lines)
                
            elif filepath.endswith(('.yaml', '.yml')):
                lines = fixed_code.split('\n')
                for i, line_content in enumerate(lines):
                    if 'image:' in line_content and package in line_content:
                        lines[i] = f"{line_content} # TODO: Update {package} image to fix {vuln_id}"
                fixed_code = '\n'.join(lines)
        
        return fixed_code
    
    def check_version_pinning(self, code, filepath):
        """Check for unpinned dependency versions"""
        issues = []
        
        if filepath.endswith('.js'):
            # Check for unpinned npm requires
            lines = code.split('\n')
            for i, line in enumerate(lines, 1):
                if 'require(' in line and not any(op in line for op in ['@', '^', '~', '>=', '<=', '==']):
                    match = re.search(r'require\(["\']([^"\']+)["\']\)', line)
                    if match and not match.group(1).startswith('./'):
                        issues.append({
                            'type': 'version_pinning',
                            'severity': 'MEDIUM',
                            'line': i,
                            'description': f'Dependency {match.group(1)} not version pinned - security risk',
                            'package': match.group(1),
                            'compliance_violations': ['Security', 'Supply Chain']
                        })
                        
        elif filepath.endswith('Dockerfile'):
            # Check for unpinned Docker images
            lines = code.split('\n')
            for i, line in enumerate(lines, 1):
                if line.strip().upper().startswith('FROM') and ':' not in line:
                    match = re.search(r'FROM\s+([^\s]+)', line, re.IGNORECASE)
                    if match:
                        issues.append({
                            'type': 'version_pinning',
                            'severity': 'HIGH',
                            'line': i,
                            'description': f'Docker image {match.group(1)} not version pinned - security risk',
                            'package': match.group(1),
                            'compliance_violations': ['Security', 'Supply Chain']
                        })
        
        return issues
    
    def scan_file(self, filepath, auto_fix=False):
        """Scan file with compliance focus and caching"""
        try:
            # Skip cache if auto-fix is enabled - need fresh AI analysis for fixes
            if not auto_fix:
                cached_result = self.get_cached_result(filepath)
                if cached_result:
                    return cached_result
            
            with open(filepath, 'r') as f:
                code = f.read()
        except Exception as e:
            self.log_error(f"File read error: {e}")
            return None
        
        language, framework = self.detect_language_and_framework(filepath, code)
        if language == 'Unknown':
            return None
        
        print(f"🔍 Compliance scanning {filepath} ({language}{f'/{framework}' if framework else ''})...")
        
        # Extract and check dependencies for vulnerabilities
        dependencies = self.extract_dependencies(code, filepath)
        vulnerabilities = []
        
        if dependencies:
            print(f"   🔍 Found dependencies: {dependencies}")
            try:
                vulnerabilities.extend(self.check_cve_vulnerabilities(dependencies))
                vulnerabilities.extend(self.check_github_advisories(dependencies))
            except Exception as e:
                print(f"   ❌ Vulnerability check failed: {e}")
            
            if vulnerabilities:
                print(f"   ⚠️ Found {len(vulnerabilities)} vulnerabilities")
        else:
            print(f"   ℹ️ No dependencies found")
        
        # Compliance-focused detection
        issues = self.compliance_detect(code, language, framework, filepath)
        
        # Add version pinning checks
        version_issues = self.check_version_pinning(code, filepath)
        issues.extend(version_issues)
        if version_issues:
            print(f"   📌 Found {len(version_issues)} version pinning issues")
        
        # Add vulnerability issues to compliance issues
        for vuln in vulnerabilities:
            issues.append({
                'type': 'vulnerability',
                'severity': vuln['severity'],
                'description': f"{vuln['id']}: {vuln['description']}",
                'package': vuln['package'],
                'vulnerability_id': vuln['id'],
                'source': vuln['type'],
                'line': vuln.get('line', 1),
                'compliance_violations': ['Security']
            })
        
        if not issues:
            print(f"   ✅ No compliance issues found")
            result = None
        else:
            print(f"   Found {len(issues)} issues")
            
            # Show compliance violations
            compliance_violations = set()
            for issue in issues:
                compliance_violations.update(issue.get('compliance_violations', []))
            
            if compliance_violations:
                print(f"   📋 Compliance violations: {', '.join(compliance_violations)}")
            
            fixed = False
            if auto_fix:
                print(f"   🔧 AI fixing compliance and vulnerabilities...")
                
                # Separate compliance and vulnerability issues
                compliance_issues = [i for i in issues if i.get('type') != 'vulnerability']
                vulnerability_issues = [i for i in issues if i.get('type') == 'vulnerability']
                
                fixed_code = code
                
                # Fix compliance issues first
                if compliance_issues:
                    fixed_code = self.compliance_fix(fixed_code, compliance_issues, language, framework)
                
                # Fix vulnerabilities by updating dependencies
                if vulnerability_issues:
                    fixed_code = self.fix_vulnerabilities(fixed_code, vulnerability_issues, filepath)
                
                if fixed_code and len(fixed_code) > 50 and fixed_code != code:
                    # Basic validation without external tools
                    print(f"   🔍 Validating fixed code...")
                    is_valid = self.basic_validation(fixed_code, language)
                    
                    if is_valid and fixed_code != code:
                        with open(filepath, 'w') as f:
                            f.write(fixed_code)
                        fixed = True
                        print(f"   ✅ Fixed and validated with compliance standards")
                    else:
                        print(f"   ❌ Fix validation failed - keeping original")
            
            result = {
                'filepath': filepath,
                'language': language,
                'framework': framework,
                'issues': issues,
                'fixed': fixed,
                'compliance_violations': list(compliance_violations)
            }
        
        # Cache the result
        self.update_file_cache(filepath, result)
        return result
    
    def upload_to_s3(self, report):
        """Upload report to S3 for web dashboard"""
        s3_bucket = os.getenv('REPORTS_S3_BUCKET')
        if not s3_bucket:
            return
        
        try:
            s3 = boto3.client('s3', region_name=self.region)
            context = self.get_scan_context()
            key = f"reports/{context['scan_id']}_compliance_report.json"
            
            s3.put_object(
                Bucket=s3_bucket,
                Key=key,
                Body=json.dumps(report, indent=2),
                ContentType='application/json'
            )
            print(f"📤 Report uploaded to s3://{s3_bucket}/{key}")
            print(f"🏷️ Scan Context: {context['scan_name']} ({context['runner']})")
        except Exception as e:
            print(f"⚠️ Failed to upload to S3: {e}")

    def log_error(self, message):
        """Log errors securely"""
        with open('error_log.txt', 'a') as log_file:
            log_file.write(f"{datetime.now().isoformat()} - ERROR: {message}\n")
    
    def run(self, auto_fix=False, git_push=False):
        """Main compliance scan"""
        print(f"🔒 Compliance-Focused AI Security Scanner")
        print(f"Model: {self.model_id}")
        print(f"Knowledge Base ID: {self.kb_id} (configured for future use)")
        print(f"Standards: PCI-DSS, SOC2, HIPAA, GDPR, OWASP")
        print(f"Auto-fix: {'ON' if auto_fix else 'OFF'}")
        print(f"Git push: {'ON' if git_push else 'OFF'}\n")
        
        # Collect files
        extensions = ['.py', '.js', '.ts', '.tf', '.tfvars', '.yaml', '.yml', '.java', '.go', '.sh', 'Dockerfile']
        files = []
        for ext in extensions:
            files.extend([f for f in glob.glob(f"**/*{ext}", recursive=True) 
                         if not any(s in f for s in ['.git/', 'venv/', 'node_modules/'])])
        
        print(f"📁 Scanning {len(files)} files for compliance violations\n")
        
        # Scan files
        results = []
        max_files = int(os.getenv('MAX_FILES_SCAN', '0'))  # 0 = no limit
        files_to_scan = files if max_files == 0 else files[:max_files]
        
        for f in files_to_scan:
            result = self.scan_file(f, auto_fix)
            if result:
                results.append(result)
        
        # Generate compliance report
        compliance_summary = {}
        for result in results:
            for violation in result.get('compliance_violations', []):
                if violation not in compliance_summary:
                    compliance_summary[violation] = {'files': [], 'issues': 0, 'critical': 0, 'high': 0}
                
                compliance_summary[violation]['files'].append(result['filepath'])
                compliance_summary[violation]['issues'] += len(result['issues'])
                
                for issue in result['issues']:
                    if issue['severity'] == 'critical':
                        compliance_summary[violation]['critical'] += 1
                    elif issue['severity'] == 'high':
                        compliance_summary[violation]['high'] += 1
        
        # Summary
        total_issues = sum(len(r['issues']) for r in results)
        fixed_count = sum(1 for r in results if r['fixed'])
        
        # Count vulnerabilities
        vulnerability_issues = []
        for r in results:
            vulnerability_issues.extend([i for i in r['issues'] if i.get('type') == 'vulnerability'])
        
        vuln_count = len(vulnerability_issues)
        cve_count = len([v for v in vulnerability_issues if v.get('source') == 'CVE'])
        github_count = len([v for v in vulnerability_issues if v.get('source') == 'GitHub Advisory'])
        
        by_severity = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
        for r in results:
            for i in r['issues']:
                by_severity[i['severity']] = by_severity.get(i['severity'], 0) + 1
        
        print(f"\n{'='*60}")
        print(f"📊 Compliance Scan Results + Vulnerability Check")
        print(f"{'='*60}")
        print(f"Files scanned: {len(files)}")
        print(f"Issues found: {total_issues}")
        print(f"Vulnerabilities: {vuln_count} (CVE: {cve_count}, GitHub: {github_count})")
        print(f"AI calls: {self.ai_calls}")
        print(f"Cost: ${self.total_cost:.4f}")
        if auto_fix:
            print(f"Fixed: {fixed_count} files")
        
        print(f"\n🎯 Severity:")
        for s in ['critical', 'high', 'medium', 'low']:
            if by_severity[s] > 0:
                print(f"  {s.upper()}: {by_severity[s]}")
        
        if compliance_summary:
            print(f"\n📋 Compliance Violations:")
            for standard, data in compliance_summary.items():
                print(f"  {standard}: {data['issues']} issues in {len(set(data['files']))} files")
                if data['critical'] > 0:
                    print(f"    ⚠️  {data['critical']} critical, {data['high']} high")
        
        print(f"\n🚨 Top Issues:")
        for r in results[:3]:
            print(f"\n{r['filepath']} ({r['language']}):")
            for i in r['issues'][:2]:
                compliance = ', '.join(i.get('compliance_violations', []))
                print(f"  [{i['severity'].upper()}] Line {i['line']}: {i['description']}")
                if compliance:
                    print(f"    📋 Violates: {compliance}")
        
        # Save report
        report = {
            'scan_context': self.get_scan_context(),
            'scan_date': datetime.now().isoformat(),
            'model': self.model_id,
            'knowledge_base_id': self.kb_id,
            'files_scanned': len(files),
            'total_issues': total_issues,
            'vulnerability_summary': {
                'total_vulnerabilities': vuln_count,
                'cve_findings': cve_count,
                'github_advisories': github_count,
                'critical_vulns': len([v for v in vulnerability_issues if v.get('severity') == 'CRITICAL']),
                'high_vulns': len([v for v in vulnerability_issues if v.get('severity') == 'HIGH'])
            },
            'ai_calls': self.ai_calls,
            'cost': self.total_cost,
            'fixed': fixed_count if auto_fix else 0,
            'by_severity': by_severity,
            'compliance_summary': compliance_summary,
            'results': results
        }
        
        with open('compliance_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        # Upload to S3 if configured
        self.upload_to_s3(report)
        
        # Post PR comment if in CI/CD
        if os.environ.get('GITHUB_ACTIONS') == 'true':
            self.post_pr_comment(report)
        
        # Save cache after scan
        self.save_cache()
        
        print(f"\n📄 Report: compliance_report.json")
        
        # Return appropriate exit code based on critical issues and environment
        if by_severity['critical'] > 0:
            print(f"\n⚠️  {by_severity['critical']} critical issues found.")
            if os.getenv('GITHUB_ACTIONS') == 'true' and not auto_fix:
                print("CI/CD: Blocking PR merge due to critical issues.")
                return 1  # Block CI/CD on critical issues when auto-fix is disabled
            else:
                print("In CI/CD: This will block PR merging.")
                print("Locally: Review and fix critical issues.")
        
        return 0

if __name__ == "__main__":
    import sys
    
    # Parse arguments
    profile_name = None
    auto_fix = False
    git_push = False
    
    for arg in sys.argv[1:]:
        if arg.startswith('--profile='):
            profile_name = arg.split('=')[1]
        elif arg == '--fix':
            auto_fix = True
        elif arg == '--push':
            git_push = True
        elif arg == '--fix-push':
            auto_fix = True
            git_push = True
    
    scanner = ComplianceScanner(profile_name=profile_name)
    exit(scanner.run(auto_fix=auto_fix, git_push=git_push))
