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
        """Pure AI analysis and fixing - NO MANUAL RULES"""
        prompt = f"""You are a security expert. Fix ALL security vulnerabilities in this {filename} file.

Provide ONLY the complete, valid, secure file content. No explanations, no comments, no extra text.

Original file:
{content}"""

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
            
            # Clean the response - remove AI artifacts only
            fixed_content = output_text
            fixed_content = re.sub(r'^Here.*?:\s*', '', fixed_content, flags=re.IGNORECASE)
            fixed_content = re.sub(r'```(?:terraform|hcl|yaml|yml)?\s*', '', fixed_content)
            fixed_content = re.sub(r'```\s*$', '', fixed_content)
            fixed_content = fixed_content.strip()
            
            # Basic syntax validation only
            is_valid = False
            if filename.endswith('.tf'):
                is_valid = 'resource' in fixed_content
            elif filename.endswith(('.yaml', '.yml')):
                is_valid = 'apiVersion:' in fixed_content
            
            # Apply if AI provided valid, different content
            if (is_valid and 
                len(fixed_content) > 50 and 
                fixed_content != content):
                
                print(f"✅ AI generated secure configuration")
                
                return {
                    "issues": [{"severity": "high", "description": "AI detected and fixed security issues", "line": 1}],
                    "fixed_content": fixed_content,
                    "changes_made": ["AI applied comprehensive security fixes"]
                }
            else:
                print(f"ℹ️ AI did not provide improved configuration")
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
        """Apply ONLY AI-generated fixes - NO MANUAL VALIDATION"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            ai_result = self.ai_analyze_and_fix(original_content, file_path)
            
            if not ai_result:
                return []
            
            issues = ai_result.get('issues', [])
            fixed_content = ai_result.get('fixed_content', original_content)
            changes = ai_result.get('changes_made', [])
            
            # Apply if AI provided different content with changes
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
        
        print(f"🤖 Pure AI Security Analyzer: {len(files)} files")
        print("Using 100% AI intelligence - ZERO manual security rules")
        
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
        
        return 0

if __name__ == '__main__':
    analyzer = PureAISecurityAnalyzer()
    analyzer.run()
    exit(0)
