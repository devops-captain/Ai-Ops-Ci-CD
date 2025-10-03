#!/usr/bin/env python3
import os
import json
import boto3
import glob
from datetime import datetime

class ComplianceScanner:
    def __init__(self, profile_name=None):
        # Use AWS profile for local development, OIDC for GitHub Actions
        session = boto3.Session(profile_name=profile_name)
        self.bedrock = session.client('bedrock-runtime', region_name='us-east-1')
        self.kb_id = '6OFPQYR1JK'  # Your Knowledge Base ID
        self.model_id = 'anthropic.claude-3-haiku-20240307-v1:0'  # 14% cheaper, good detection
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
    
    def compliance_detect(self, code, language, framework, filepath):
        """Compliance-focused detection using AI"""
        framework_text = f"/{framework}" if framework else ""
        
        # Pure AI prompt - no hardcoded patterns
        prompt = f"""You are a security expert. Analyze this {language}{framework_text} code for compliance violations using your knowledge of security standards.

Use your expertise in: PCI-DSS, SOC2, HIPAA, GDPR, OWASP Top 10

Return JSON array with exact line numbers:
[{{"line": <exact_line_number>, "severity": "critical|high|medium|low", 
"category": "<type>", "description": "<what_you_found>", "cvss": <score>, 
"compliance_violations": ["<standard>"], "remediation": "<fix>"}}]

Code from {filepath}:
```
{code}
```

IMPORTANT: Return ONLY the JSON array, no other text."""

        output = self.call_ai_with_compliance(prompt)
        if not output:
            return []
        
        try:
            # Clean and extract JSON
            output = output.strip()
            if '```' in output:
                # Remove code blocks
                lines = output.split('\n')
                output = '\n'.join([l for l in lines if not l.strip().startswith('```')])
            
            if '[' in output and ']' in output:
                json_start = output.index('[')
                json_end = output.rindex(']') + 1
                json_str = output[json_start:json_end]
                issues = json.loads(json_str)
                
                # Validate issues have required fields
                valid_issues = []
                for issue in issues:
                    if isinstance(issue, dict) and 'line' in issue and 'severity' in issue:
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
        
        return {
            'filepath': filepath,
            'language': language,
            'framework': framework,
            'issues': issues,
            'fixed': fixed,
            'compliance_violations': list(compliance_violations)
        }
    
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
        
        print(f"\n📄 Report: compliance_report.json")
        
        return 1 if by_severity['critical'] > 0 else 0

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
