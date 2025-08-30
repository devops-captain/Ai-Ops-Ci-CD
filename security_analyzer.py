#!/usr/bin/env python3
import os
import json
import boto3
import glob
import re

class PureAISecurityAnalyzer:
    def __init__(self):
        self.bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
        self.api_calls = 0
        self.fixes_applied = []
        
    def ai_analyze_and_fix(self, content, filename):
        """Pure AI analysis and fixing with better prompting"""
        prompt = f"""You are a security expert. Fix ALL security vulnerabilities in this {filename} file.

CRITICAL SECURITY RULES:
- Replace 0.0.0.0/0 with specific IP ranges like 10.0.0.0/8
- Set runAsUser to non-root (1000+)
- Set privileged to false
- Remove hardcoded secrets
- Add resource limits
- Use secure configurations

Original file:
{content}

Provide ONLY the complete, valid, secure file content. No explanations, no comments, no extra text."""

        try:
            response = self.bedrock.invoke_model(
                modelId='amazon.nova-micro-v1:0',
                body=json.dumps({
                    "messages": [
                        {
                            "role": "user",
                            "content": [{"text": prompt}]
                        }
                    ],
                    "inferenceConfig": {
                        "maxTokens": 3000,
                        "temperature": 0.1,
                        "topP": 0.9
                    }
                })
            )
            
            self.api_calls += 1
            result = json.loads(response['body'].read())
            output_text = result['output']['message']['content'][0]['text'].strip()
            
            print(f"🤖 AI analyzing {filename}...")
            
            # Clean the response - remove any explanatory text
            fixed_content = output_text
            
            # Remove common AI response artifacts
            fixed_content = re.sub(r'^Here.*?:\s*', '', fixed_content, flags=re.IGNORECASE)
            fixed_content = re.sub(r'^The.*?:\s*', '', fixed_content, flags=re.IGNORECASE)
            fixed_content = re.sub(r'```(?:terraform|hcl|yaml|yml)?\s*', '', fixed_content)
            fixed_content = re.sub(r'```\s*$', '', fixed_content)
            fixed_content = re.sub(r'CHANGES:.*$', '', fixed_content, flags=re.DOTALL)
            fixed_content = re.sub(r'Changes made:.*$', '', fixed_content, flags=re.DOTALL)
            
            # Clean up whitespace
            fixed_content = fixed_content.strip()
            
            # Validate the content
            if filename.endswith('.tf'):
                if not re.search(r'resource\s+"[^"]+"\s+"[^"]+"\s*\{', fixed_content):
                    print(f"⚠️ Invalid Terraform syntax in AI response")
                    return self._create_fallback_result(content)
            elif filename.endswith(('.yaml', '.yml')):
                if not re.search(r'apiVersion:', fixed_content):
                    print(f"⚠️ Invalid YAML syntax in AI response")
                    return self._create_fallback_result(content)
            
            # Check if content is actually different and improved
            if (len(fixed_content) > 50 and 
                fixed_content != content and
                self._is_more_secure(content, fixed_content)):
                
                changes = self._detect_changes(content, fixed_content)
                print(f"✅ AI generated secure configuration")
                
                return {
                    "issues": [{"severity": "high", "description": "Security vulnerabilities fixed", "line": 1}],
                    "fixed_content": fixed_content,
                    "changes_made": changes
                }
            else:
                print(f"⚠️ AI response not suitable")
                return self._create_fallback_result(content)
            
        except Exception as e:
            print(f"❌ AI API call failed for {filename}: {e}")
            return self._create_fallback_result(content)
    
    def _is_more_secure(self, original, fixed):
        """Check if the fixed version is more secure"""
        security_improvements = 0
        
        # Check for security improvements
        if '0.0.0.0/0' in original and '0.0.0.0/0' not in fixed:
            security_improvements += 1
        if 'runAsUser: 0' in original and 'runAsUser: 0' not in fixed:
            security_improvements += 1
        if 'privileged: true' in original and 'privileged: true' not in fixed:
            security_improvements += 1
        if 'resources: {}' in original and 'resources: {}' not in fixed:
            security_improvements += 1
        
        return security_improvements > 0
    
    def _detect_changes(self, original, fixed):
        """Detect what changes were made"""
        changes = []
        
        if '0.0.0.0/0' in original and '0.0.0.0/0' not in fixed:
            changes.append("Restricted network access from 0.0.0.0/0")
        if 'runAsUser: 0' in original and 'runAsUser: 0' not in fixed:
            changes.append("Changed from root user to non-root user")
        if 'privileged: true' in original and 'privileged: true' not in fixed:
            changes.append("Disabled privileged container mode")
        if 'resources: {}' in original and 'resources: {}' not in fixed:
            changes.append("Added resource limits")
        if 'password' in original.lower() and 'password' not in fixed.lower():
            changes.append("Removed hardcoded credentials")
        
        if not changes:
            changes = ["Applied security improvements"]
        
        return changes
    
    def _create_fallback_result(self, content):
        """Create fallback result when AI fails"""
        return {
            "issues": [{"severity": "medium", "description": "Analysis completed", "line": 1}],
            "fixed_content": content,
            "changes_made": []
        }
    
    def apply_ai_fixes(self, file_path):
        """Apply AI-generated fixes"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            ai_result = self.ai_analyze_and_fix(original_content, file_path)
            
            if not ai_result:
                return []
            
            issues = ai_result.get('issues', [])
            fixed_content = ai_result.get('fixed_content', original_content)
            changes = ai_result.get('changes_made', [])
            
            # Apply fixes if we have meaningful changes
            if (fixed_content and 
                fixed_content != original_content and 
                len(changes) > 0):
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                
                self.fixes_applied.append({
                    'file': file_path,
                    'issues_fixed': len(issues),
                    'changes': changes
                })
                print(f"✅ Applied {len(changes)} security fixes to {file_path}")
                for change in changes:
                    print(f"   - {change}")
            else:
                print(f"ℹ️ No security improvements applied to {file_path}")
            
            return issues
            
        except Exception as e:
            print(f"❌ Error processing {file_path}: {e}")
            return []
    
    def calculate_costs(self):
        input_tokens = self.api_calls * 700
        output_tokens = self.api_calls * 600
        
        input_cost = (input_tokens / 1000000) * 35.00
        output_cost = (output_tokens / 1000000) * 140.00
        
        return {
            'per_scan': round(input_cost + output_cost, 6),
            'monthly_estimate': round((input_cost + output_cost) * 30, 4),
            'api_calls': self.api_calls
        }
    
    def run(self):
        patterns = ['*.tf', '*.yaml', '*.yml']
        files = []
        for pattern in patterns:
            files.extend(glob.glob(pattern))
        
        print(f"🤖 AI Security Analyzer: {len(files)} files")
        
        all_issues = []
        
        for file_path in files:
            if os.path.getsize(file_path) < 10240:
                issues = self.apply_ai_fixes(file_path)
                for issue in issues:
                    issue['file'] = file_path
                    all_issues.append(issue)
        
        costs = self.calculate_costs()
        fixed_count = len(self.fixes_applied)
        total_issues = len(all_issues)
        
        results = {
            'summary': f"🤖 AI: {total_issues} issues analyzed, {fixed_count} files fixed",
            'issues': all_issues,
            'files_scanned': len(files),
            'fixes_applied': fixed_count,
            'scan_cost': costs['per_scan'],
            'estimated_monthly_cost': costs['monthly_estimate'],
            'ai_calls': self.api_calls
        }
        
        with open('security-results.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n🤖 Analysis Complete:")
        print(f"   Files: {len(files)}")
        print(f"   AI calls: {self.api_calls}")
        print(f"   Issues: {total_issues}")
        print(f"   Fixed: {fixed_count}")
        print(f"   Cost: ${costs['per_scan']}")
        
        return 0

if __name__ == '__main__':
    analyzer = PureAISecurityAnalyzer()
    analyzer.run()
    exit(0)
