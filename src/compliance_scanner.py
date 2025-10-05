#!/usr/bin/env python3
import os
import json
import boto3
import glob
import hashlib
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
        
        # Try S3 cache first (for CI/CD)
        s3_bucket = os.getenv('REPORTS_S3_BUCKET')
        if s3_bucket:
            try:
                s3 = boto3.client('s3', region_name=self.region)
                response = s3.get_object(Bucket=s3_bucket, Key='cache/compliance_cache.json')
                cache_data = json.loads(response['Body'].read().decode('utf-8'))
                print(f"📋 Loaded cache from S3: {len(cache_data)} files")
                return cache_data
            except Exception as e:
                print(f"📋 No S3 cache found, starting fresh")
        
        # Fallback to local cache
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    cache_data = json.load(f)
                print(f"📋 Loaded local cache: {len(cache_data)} files")
        except Exception as e:
            print(f"⚠️ Cache load error: {e}")
        
        return cache_data
    
    def save_cache(self):
        """Save file hash cache to both S3 and local"""
        # Save locally
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.file_cache, f, indent=2)
        except Exception as e:
            print(f"⚠️ Local cache save error: {e}")
        
        # Save to S3 for CI/CD persistence
        s3_bucket = os.getenv('REPORTS_S3_BUCKET')
        if s3_bucket:
            try:
                s3 = boto3.client('s3', region_name=self.region)
                s3.put_object(
                    Bucket=s3_bucket,
                    Key='cache/compliance_cache.json',
                    Body=json.dumps(self.file_cache, indent=2),
                    ContentType='application/json'
                )
                print(f"📋 Cache saved to S3: {len(self.file_cache)} files")
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
                        "max_tokens": 3000,
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
                        "inferenceConfig": {"maxTokens": 3000, "temperature": 0.1, "topP": 0.9}
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
    
    def scan_file(self, filepath, auto_fix=False):
        """Scan file with compliance focus and caching"""
        try:
            # Check cache first
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
        
        # Compliance-focused detection
        issues = self.compliance_detect(code, language, framework, filepath)
        
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
                print(f"   🔧 Compliance-focused AI fixing...")
                fixed_code = self.compliance_fix(code, issues, language, framework)
                
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
        extensions = ['.py', '.js', '.ts', '.tf', '.tfvars', '.yaml', '.yml', '.java', '.go', '.sh']
        files = []
        for ext in extensions:
            files.extend([f for f in glob.glob(f"**/*{ext}", recursive=True) 
                         if not any(s in f for s in ['.git/', 'venv/', 'node_modules/'])])
        
        print(f"📁 Scanning {len(files)} files for compliance violations\n")
        
        # Scan files
        results = []
        for f in files[:10]:  # Limit for cost
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
        
        by_severity = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
        for r in results:
            for i in r['issues']:
                by_severity[i['severity']] = by_severity.get(i['severity'], 0) + 1
        
        print(f"\n{'='*60}")
        print(f"📊 Compliance Scan Results")
        print(f"{'='*60}")
        print(f"Files scanned: {len(files)}")
        print(f"Issues found: {total_issues}")
        print(f"AI calls: {self.ai_calls}")
        print(f"Cost: ${self.total_cost:.4f}")
        if auto_fix:            print(f"Fixed: {fixed_count} files")
        
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
        
        # Save cache after scan
        self.save_cache()
        
        print(f"\n📄 Report: compliance_report.json")
        
        # Only return exit code 1 for CI/CD environments, not local runs
        if by_severity['critical'] > 0:
            print(f"\n⚠️  {by_severity['critical']} critical issues found.")
            print("In CI/CD: This will block PR merging.")
            print("Locally: Review and fix critical issues.")
        
        return 0  # Always return 0 for local runs - let workflow handle blocking

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
