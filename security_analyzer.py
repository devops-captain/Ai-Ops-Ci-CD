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
        """Pure AI analysis and fixing using Nova Micro"""
        prompt = f"""Fix security issues in {filename}. Provide the complete fixed file.

{content}

Return the fixed content in this format:
FIXED_CONTENT_START
[complete fixed file content here]
FIXED_CONTENT_END

CHANGES:
- change 1
- change 2"""

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
                        "maxTokens": 4000,
                        "temperature": 0.1,
                        "topP": 0.9
                    }
                })
            )
            
            self.api_calls += 1
            result = json.loads(response['body'].read())
            output_text = result['output']['message']['content'][0]['text'].strip()
            
            print(f"🤖 AI analyzing {filename}...")
            print(f"AI response length: {len(output_text)} chars")
            
            # Extract fixed content using markers
            fixed_content = None
            changes = []
            
            # Method 1: Look for FIXED_CONTENT markers
            content_match = re.search(r'FIXED_CONTENT_START\s*(.*?)\s*FIXED_CONTENT_END', output_text, re.DOTALL)
            if content_match:
                fixed_content = content_match.group(1).strip()
                print(f"✅ Extracted fixed content using markers ({len(fixed_content)} chars)")
            
            # Method 2: Look for code blocks
            if not fixed_content:
                if filename.endswith('.tf'):
                    code_match = re.search(r'```(?:terraform|hcl)?\s*(.*?)```', output_text, re.DOTALL)
                else:
                    code_match = re.search(r'```(?:yaml|yml)?\s*(.*?)```', output_text, re.DOTALL)
                
                if code_match:
                    fixed_content = code_match.group(1).strip()
                    print(f"✅ Extracted fixed content from code block ({len(fixed_content)} chars)")
            
            # Method 3: Look for structured content
            if not fixed_content:
                if filename.endswith('.tf'):
                    tf_match = re.search(r'(resource\s+"[^"]+"\s+"[^"]+"\s*\{.*)', output_text, re.DOTALL)
                    if tf_match:
                        fixed_content = tf_match.group(1).strip()
                        print(f"✅ Extracted Terraform content ({len(fixed_content)} chars)")
                else:
                    yaml_match = re.search(r'(apiVersion:.*)', output_text, re.DOTALL)
                    if yaml_match:
                        fixed_content = yaml_match.group(1).strip()
                        print(f"✅ Extracted YAML content ({len(fixed_content)} chars)")
            
            # Extract changes
            changes_match = re.search(r'CHANGES:\s*(.*?)(?:\n\n|\Z)', output_text, re.DOTALL)
            if changes_match:
                changes_text = changes_match.group(1)
                changes = [line.strip('- ').strip() for line in changes_text.split('\n') if line.strip().startswith('-')]
            
            if not changes:
                # Look for any bullet points or changes mentioned
                change_patterns = [
                    r'(?:Fixed|Changed|Updated|Removed|Added).*?(?:\n|$)',
                    r'-\s+.*?(?:\n|$)',
                    r'•\s+.*?(?:\n|$)'
                ]
                for pattern in change_patterns:
                    matches = re.findall(pattern, output_text, re.IGNORECASE)
                    if matches:
                        changes = [match.strip() for match in matches[:3]]  # Limit to 3
                        break
            
            if not changes:
                changes = ["AI applied security improvements"]
            
            # Validate fixed content
            if fixed_content and len(fixed_content) > 50 and fixed_content != content:
                return {
                    "issues": [{"severity": "high", "description": "Security vulnerabilities fixed by AI", "line": 1}],
                    "fixed_content": fixed_content,
                    "changes_made": changes
                }
            else:
                print(f"⚠️ No valid fixed content extracted")
                return {
                    "issues": [{"severity": "medium", "description": "AI analysis completed", "line": 1}],
                    "fixed_content": content,
                    "changes_made": []
                }
            
        except Exception as e:
            print(f"❌ AI API call failed for {filename}: {e}")
            return {
                "issues": [],
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
            
            # Apply fixes if we have different content
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
                print(f"✅ AI applied fixes to {file_path}")
                for change in changes:
                    print(f"   - {change}")
            else:
                print(f"ℹ️ No AI fixes applied to {file_path}")
            
            return issues
            
        except Exception as e:
            print(f"❌ Error processing {file_path}: {e}")
            return []
    
    def calculate_costs(self):
        input_tokens = self.api_calls * 800
        output_tokens = self.api_calls * 700
        
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
        
        print(f"🤖 Pure AI Security Analyzer: {len(files)} files")
        
        all_issues = []
        
        for file_path in files:
            if os.path.getsize(file_path) < 12288:
                issues = self.apply_ai_fixes(file_path)
                for issue in issues:
                    issue['file'] = file_path
                    all_issues.append(issue)
        
        costs = self.calculate_costs()
        fixed_count = len(self.fixes_applied)
        total_issues = len(all_issues)
        
        results = {
            'summary': f"🤖 Pure AI: {total_issues} issues analyzed, {fixed_count} files fixed",
            'issues': all_issues,
            'files_scanned': len(files),
            'fixes_applied': fixed_count,
            'scan_cost': costs['per_scan'],
            'estimated_monthly_cost': costs['monthly_estimate'],
            'ai_calls': self.api_calls
        }
        
        with open('security-results.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n🤖 Pure AI Analysis Complete:")
        print(f"   Files: {len(files)}")
        print(f"   AI calls: {self.api_calls}")
        print(f"   Issues: {total_issues}")
        print(f"   Fixed: {fixed_count}")
        print(f"   Cost: ${costs['per_scan']}")
        
        if fixed_count > 0:
            print(f"\n✅ {fixed_count} files modified by AI")
        
        return 0

if __name__ == '__main__':
    analyzer = PureAISecurityAnalyzer()
    analyzer.run()
    exit(0)
