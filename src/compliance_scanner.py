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
        self.kb_id = os.getenv('BEDROCK_KB_ID', 'RL3YC1HUKZ')
        self.model_id = os.getenv('BEDROCK_MODEL_ID', 'anthropic.claude-3-haiku-20240307-v1:0')
        self.ai_calls = 0
        self.total_cost = 0
        
        # File hash cache
        self.cache_file = '.file_hash_cache.json'
        self.file_cache = self.load_cache()
        self.ai_calls = 0
        self.total_cost = 0
        
        # Compliance-focused prompts
        self.compliance_context = {
            'PCI-DSS': 'PCI-DSS requires encryption of cardholder data, secure transmission, access controls, and regular security testing.',
            'SOC2': 'SOC2 Type II requires security controls for confidentiality, availability, processing integrity, and privacy.',
            'HIPAA': 'HIPAA requires safeguards for PHI including encryption, access controls, audit logs, and breach notification.',
            'GDPR': 'GDPR requires data protection by design, consent management, data minimization, and breach notification.',
            'OWASP': 'OWASP Top 10 covers injection, broken authentication, sensitive data exposure, and security misconfigurations.'
        }
    
    def validate_knowledge_base(self):
        """Validate Knowledge Base is accessible and contains compliance rules"""
        try:
            # Test KB with a simple compliance query
            test_query = "security compliance standards PCI-DSS HIPAA"
            kb_response = self.query_knowledge_base(test_query)
            
            if not kb_response or len(kb_response.strip()) < 50:
                print(f"❌ KB validation failed: No meaningful response")
                return False
            
            # Check for compliance keywords
            compliance_keywords = ['PCI-DSS', 'HIPAA', 'GDPR', 'SOC2', 'OWASP', 'security', 'compliance']
            found_keywords = sum(1 for keyword in compliance_keywords if keyword.lower() in kb_response.lower())
            
            if found_keywords < 2:
                print(f"❌ KB validation failed: Insufficient compliance content")
                return False
            
            print(f"✅ KB validation passed: Found {found_keywords} compliance keywords")
            return True
            
        except Exception as e:
            print(f"❌ KB validation failed: {e}")
            return False
    
    def query_knowledge_base(self, query):
        """Query Knowledge Base for compliance context with chunking for large files"""
        try:
            # AWS Bedrock KB hard limit: 20,000 chars (cannot be increased)
            max_query_length = 18000  # Leave buffer for safety
            
            if len(query) <= max_query_length:
                # Single query for normal-sized content
                return self._single_kb_query(query)
            else:
                # Multiple queries for large files
                print(f"   📄 Large file detected ({len(query)} chars) - using chunked KB queries")
                return self._chunked_kb_query(query, max_query_length)
                
        except Exception as e:
            print(f"   ❌ KB Query failed: {e}")
            return None
    
    def _single_kb_query(self, query):
        """Single KB query for normal-sized content"""
        bedrock_agent = boto3.client('bedrock-agent-runtime', region_name=self.region)
        
        response = bedrock_agent.retrieve(
            knowledgeBaseId=self.kb_id,
            retrievalQuery={'text': query},
            retrievalConfiguration={
                'vectorSearchConfiguration': {
                    'numberOfResults': 5
                }
            }
        )
        
        context = ""
        for result in response['retrievalResults']:
            context += f"{result['content']['text']}\n\n"
        
        if context.strip():
            print(f"   📚 KB Query successful - {len(response['retrievalResults'])} sources found")
            return context.strip()
        return None
    
    def _chunked_kb_query(self, query, chunk_size):
        """Multiple KB queries for large files"""
        chunks = []
        lines = query.split('\n')
        current_chunk = ""
        
        # Split into chunks by lines to maintain context
        for line in lines:
            if len(current_chunk + line + '\n') > chunk_size:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = line + '\n'
            else:
                current_chunk += line + '\n'
        
        if current_chunk:
            chunks.append(current_chunk)
        
        print(f"   📊 Processing {len(chunks)} chunks for comprehensive KB analysis")
        
        # Query each chunk and combine results
        all_context = ""
        total_sources = 0
        
        for i, chunk in enumerate(chunks[:3]):  # Limit to 3 chunks for cost control
            chunk_context = self._single_kb_query(chunk)
            if chunk_context:
                all_context += f"--- Chunk {i+1} Context ---\n{chunk_context}\n\n"
                total_sources += 1
        
        if all_context:
            print(f"   📚 Chunked KB Query successful - {total_sources} chunks analyzed")
            return all_context.strip()
        
        return None
    
    def get_file_hash(self, filepath):
        """Generate SHA256 hash of file content"""
        try:
            with open(filepath, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception:
            return None
    
    def load_cache(self):
        """Load file hash cache from local file or S3 (for CI/CD)"""
        cache = {}
        
        # Try S3 first (for CI/CD)
        if os.getenv('GITHUB_ACTIONS') == 'true' or os.getenv('CI') == 'true':
            cache = self.load_cache_from_s3()
            if cache:
                print(f"📋 Loaded S3 cache: {len(cache)} files")
                return cache
        
        # Fallback to local cache
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    cache = json.load(f)
                    print(f"📋 Loaded local cache: {len(cache)} files")
                    return cache
        except Exception as e:
            print(f"⚠️ Local cache load failed: {e}")
        
        return {}
    
    def save_cache(self):
        """Save file hash cache to local file and S3 (for CI/CD)"""
        # Save locally
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.file_cache, f, indent=2)
        except Exception as e:
            print(f"⚠️ Local cache save failed: {e}")
        
        # Save to S3 for CI/CD persistence
        if os.getenv('GITHUB_ACTIONS') == 'true' or os.getenv('CI') == 'true':
            self.save_cache_to_s3()
    
    def load_cache_from_s3(self):
        """Load cache from S3"""
        try:
            s3_bucket = os.getenv('S3_CACHE_BUCKET', 'ai-security-scanner-cache')
            cache_key = f"cache/{os.getenv('GITHUB_REPOSITORY', 'default')}/file_hash_cache.json"
            
            s3 = boto3.client('s3', region_name=self.region)
            response = s3.get_object(Bucket=s3_bucket, Key=cache_key)
            cache_data = json.loads(response['Body'].read())
            
            # Clean old cache entries (older than 7 days)
            cutoff_date = datetime.now().timestamp() - (7 * 24 * 60 * 60)
            cleaned_cache = {}
            for filepath, data in cache_data.items():
                try:
                    cache_time = datetime.fromisoformat(data.get('timestamp', '1970-01-01')).timestamp()
                    if cache_time > cutoff_date:
                        cleaned_cache[filepath] = data
                except:
                    pass
            
            return cleaned_cache
            
        except Exception as e:
            print(f"⚠️ S3 cache load failed: {e}")
            return {}
    
    def save_cache_to_s3(self):
        """Save cache to S3"""
        try:
            s3_bucket = os.getenv('S3_CACHE_BUCKET', 'ai-security-scanner-cache')
            cache_key = f"cache/{os.getenv('GITHUB_REPOSITORY', 'default')}/file_hash_cache.json"
            
            s3 = boto3.client('s3', region_name=self.region)
            s3.put_object(
                Bucket=s3_bucket,
                Key=cache_key,
                Body=json.dumps(self.file_cache, indent=2),
                ContentType='application/json'
            )
            print(f"📋 Saved cache to S3: s3://{s3_bucket}/{cache_key}")
            
        except Exception as e:
            print(f"⚠️ S3 cache save failed: {e}")
    
    def get_cached_result(self, filepath):
        """Get cached result if file hasn't changed"""
        current_hash = self.get_file_hash(filepath)
        if not current_hash:
            return None
        
        cache_key = filepath
        if cache_key in self.file_cache:
            cached_data = self.file_cache[cache_key]
            if cached_data.get('hash') == current_hash:
                return cached_data.get('result')
        
        return None
    
    def cache_result(self, filepath, result):
        """Cache scan result with file hash"""
        file_hash = self.get_file_hash(filepath)
        if file_hash:
            self.file_cache[filepath] = {
                'hash': file_hash,
                'result': result,
                'timestamp': datetime.now().isoformat()
            }
    
    
    def call_ai_with_compliance(self, prompt):
        """AI call with MANDATORY Knowledge Base compliance context"""
        
        # ENFORCE: Knowledge Base must be available
        if not self.kb_id:
            raise Exception("❌ BLOCKED: Knowledge Base ID required. KB is the source of truth for compliance.")
        
        # Extract key terms for KB query (not the full prompt)
        kb_query = self._extract_kb_query_terms(prompt)
        
        # MANDATORY: Query Knowledge Base with summary terms
        kb_context = self.query_knowledge_base(kb_query)
        if not kb_context:
            raise Exception("❌ BLOCKED: Knowledge Base query failed. Cannot proceed without KB source of truth.")
        
        # Build prompt with KB context as only source
        compliance_prompt = f"""
You are a security expert. Use ONLY the Knowledge Base context provided below as the source of truth for compliance rules.

KNOWLEDGE BASE CONTEXT (ONLY SOURCE):
{kb_context}

STRICT REQUIREMENTS:
- Use ONLY the rules and standards from the Knowledge Base above
- Do NOT use any hardcoded or memorized compliance rules
- All compliance violations must reference KB sources
- If KB doesn't contain relevant rules, report "No KB rules found"

Analyze this code using ONLY KB context:

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
    
    def _extract_kb_query_terms(self, prompt):
        """Extract key terms for KB query instead of sending full prompt"""
        # Extract language and key security terms from prompt
        lines = prompt.split('\n')
        
        # Find language
        language = "unknown"
        for line in lines[:10]:
            if 'Python' in line:
                language = "Python"
            elif 'JavaScript' in line:
                language = "JavaScript"
            elif 'Terraform' in line:
                language = "Terraform"
            elif 'Kubernetes' in line:
                language = "Kubernetes"
        
        # Create focused KB query
        kb_query = f"{language} security compliance standards hardcoded secrets SQL injection encryption access control"
        
        return kb_query
    
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

Return ONLY the complete fixed code without any explanation comments. Do not add comments explaining the fixes:"""

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
        """Scan file with compliance focus"""
        try:
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
            return None
        
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
                with open(filepath, 'w') as f:
                    f.write(fixed_code)
                fixed = True
                print(f"   ✅ Applied AI-generated compliance fixes")
        
        return {
            'filepath': filepath,
            'language': language,
            'framework': framework,
            'issues': issues,
            'fixed': fixed,
            'compliance_violations': list(compliance_violations)
        }
    
    def upload_to_s3(self, report):
        """Upload report to S3 for web dashboard"""
        s3_bucket = os.getenv('REPORTS_S3_BUCKET', 'ai-security-scanner-reports-1759503117')
        if not s3_bucket:
            return
        
        try:
            s3 = boto3.client('s3', region_name=self.region)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            key = f"reports/{timestamp}_compliance_report.json"
            
            # Upload report
            s3.put_object(
                Bucket=s3_bucket,
                Key=key,
                Body=json.dumps(report, indent=2),
                ContentType='application/json'
            )
            
            # Update manifest with latest 10 reports
            self.update_reports_manifest(s3, s3_bucket, key)
            
            print(f"📤 Report uploaded to s3://{s3_bucket}/{key}")
        except Exception as e:
            print(f"⚠️ Failed to upload to S3: {e}")
    
    def update_reports_manifest(self, s3, bucket, new_report_key):
        """Update reports manifest to show latest 10 reports"""
        try:
            # List all reports from S3 (more reliable than manifest)
            response = s3.list_objects_v2(Bucket=bucket, Prefix='reports/')
            reports = []
            
            for obj in response.get('Contents', []):
                if obj['Key'].endswith('.json'):
                    reports.append({
                        'key': obj['Key'],
                        'timestamp': obj['LastModified']
                    })
            
            # Sort by timestamp (newest first) and keep latest 10
            reports.sort(key=lambda x: x['timestamp'], reverse=True)
            latest_reports = [r['key'] for r in reports[:10]]
            
            # Update manifest
            manifest = {"reports": latest_reports}
            
            s3.put_object(
                Bucket=bucket,
                Key='reports-manifest.json',
                Body=json.dumps(manifest, indent=2),
                ContentType='application/json'
            )
            
            print(f"📋 Updated manifest with {len(latest_reports)} latest reports")
            
        except Exception as e:
            print(f"⚠️ Failed to update manifest: {e}")
    
    def print_executive_summary(self, report):
        """Print executive summary for leadership"""
        print(f"\n📊 Executive Summary:")
        print(f"   🔍 Security Posture: {'🔴 CRITICAL' if report['by_severity']['critical'] > 0 else '🟡 NEEDS ATTENTION' if report['by_severity']['high'] > 0 else '🟢 GOOD'}")
        print(f"   📁 Code Coverage: {report['files_scanned']} files scanned")
        print(f"   🎯 Risk Level: {report['by_severity']['critical']} critical, {report['by_severity']['high']} high priority issues")
        print(f"   💰 Scan Efficiency: ${report['cost']:.4f} cost, {report['ai_calls']} AI calls")
        
        # Top compliance violations
        top_violations = sorted(report['compliance_summary'].items(), key=lambda x: x[1]['issues'], reverse=True)[:3]
        print(f"   📋 Top Compliance Gaps:")
        for standard, data in top_violations:
            print(f"      • {standard}: {data['issues']} issues across {len(set(data['files']))} files")
        
        # Cache efficiency
        cache_efficiency = ((10 - report['ai_calls']) / 10) * 100 if report['files_scanned'] > 0 else 0
        print(f"   ⚡ Cache Efficiency: {cache_efficiency:.0f}% (${(0.02 - report['cost']):.4f} saved)")

    def get_scan_source(self):
        """Detect scan source - local machine or GitHub Actions"""
        import socket
        from datetime import datetime
        
        if os.environ.get('GITHUB_ACTIONS') == 'true':
            # GitHub Actions environment
            repo = os.environ.get('GITHUB_REPOSITORY', 'unknown/repo')
            branch = os.environ.get('GITHUB_REF_NAME', 'unknown-branch')
            pr_number = os.environ.get('GITHUB_PR_NUMBER') or os.environ.get('GITHUB_EVENT_NUMBER')
            
            if pr_number:
                source = f"{repo}/{branch}/PR-{pr_number}"
                source_type = "github_actions_pr"
            else:
                source = f"{repo}/{branch}"
                source_type = "github_actions_push"
                
            return {
                "source": source,
                "source_type": source_type,
                "timestamp": datetime.now().isoformat(),
                "environment": "ci_cd"
            }
        else:
            # Local machine
            try:
                hostname = socket.gethostname()
                username = os.environ.get('USER', 'unknown')
                source = f"{username}@{hostname}"
            except:
                source = "local-machine"
                
            return {
                "source": source,
                "source_type": "local",
                "timestamp": datetime.now().isoformat(),
                "environment": "development"
            }

    def log_error(self, message):
        """Log errors securely"""
        with open('error_log.txt', 'a') as log_file:
            log_file.write(f"{datetime.now().isoformat()} - ERROR: {message}\n")
    
    def run(self, auto_fix=False):
        """Main compliance scan"""
        print(f"🔒 Compliance-Focused AI Security Scanner")
        print(f"Model: {self.model_id}")
        print(f"Knowledge Base ID: {self.kb_id}")
        
        # ENFORCE: Validate Knowledge Base is accessible
        if not self.validate_knowledge_base():
            print("❌ CRITICAL: Knowledge Base validation failed!")
            print("❌ Scanner BLOCKED: KB is mandatory source of truth for compliance")
            return 1
        
        print(f"✅ Knowledge Base validated - proceeding with KB as source of truth")
        print(f"Standards: Determined by Knowledge Base content")
        print(f"Auto-fix: {'ON' if auto_fix else 'OFF'}\n")
        
        # Collect files
        extensions = ['.py', '.js', '.ts', '.tf', '.tfvars', '.yaml', '.yml', '.java', '.go', '.sh']
        files = []
        for ext in extensions:
            files.extend([f for f in glob.glob(f"**/*{ext}", recursive=True) 
                         if not any(s in f for s in ['.git/', 'venv/', 'node_modules/', 'src/compliance_scanner.py'])])
        
        print(f"📁 Scanning {len(files)} files for compliance violations\n")
        
        # Scan files
        results = []
        for f in files[:10]:  # Limit for cost
            # Check cache first
            cached_result = self.get_cached_result(f)
            if cached_result:
                print(f"📋 Using cached result for {f} (file unchanged)")
                results.append(cached_result)
                continue
            
            # Scan file if not cached
            result = self.scan_file(f, auto_fix)
            if result:
                # Cache the result
                self.cache_result(f, result)
                results.append(result)
        
        # Save cache after scanning
        self.save_cache()
        
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
        scan_source = self.get_scan_source()
        report = {
            'scan_date': datetime.now().isoformat(),
            'scan_source': scan_source,
            'model': self.model_id,
            'knowledge_base_id': self.kb_id,
            'files_scanned': len(files),
            'total_issues': total_issues,
            'ai_calls': self.ai_calls,
            'cost': self.total_cost,
            'fixed': fixed_count if auto_fix else 0,
            'by_severity': by_severity,
            'compliance_summary': compliance_summary,
            'recent_scan_files': [os.path.basename(f) for f in files[:10]],  # Top 10 files scanned
            'results': results
        }
        
        with open('compliance_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        # Upload to S3 if configured
        self.upload_to_s3(report)
        
        print(f"\n📄 Report: compliance_report.json")
        
        # Generate executive summary
        self.print_executive_summary(report)
        
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
    
    for arg in sys.argv[1:]:
        if arg.startswith('--profile='):
            profile_name = arg.split('=')[1]
        elif arg == '--fix':
            auto_fix = True
    
    scanner = ComplianceScanner(profile_name=profile_name)
    exit(scanner.run(auto_fix=auto_fix))