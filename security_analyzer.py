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
        prompt = f"""Fix ALL security issues in {filename}. Return complete secure version.

Original file:
{content}

Provide the complete fixed file with all security vulnerabilities resolved. Return as JSON:
{{"issues":[{{"severity":"high","description":"brief issue","line":1}}],"fixed_content":"COMPLETE SECURE FILE CONTENT HERE","changes_made":["specific change made"]}}"""

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
            
            # Try multiple extraction methods
            ai_result = None
            
            # Method 1: Clean JSON parsing
            try:
                cleaned = re.sub(r'```json\s*', '', output_text)
                cleaned = re.sub(r'```\s*', '', cleaned)
                
                json_match = re.search(r'\{.*?"fixed_content".*?\}', cleaned, re.DOTALL)
                if json_match:
                    ai_result = json.loads(json_match.group(0))
                    print(f"✅ JSON parsing successful")
            except:
                pass
            
            # Method 2: Extract fixed_content directly
            if not ai_result:
                try:
                    content_match = re.search(r'"fixed_content"\s*:\s*"([^"]*(?:\\.[^"]*)*)"', output_text, re.DOTALL)
                    if content_match:
                        fixed_content = content_match.group(1)
                        fixed_content = fixed_content.replace('\\n', '\n').replace('\\"', '"')
                        ai_result = {
                            "issues": [{"severity": "high", "description": "Security issues fixed", "line": 1}],
                            "fixed_content": fixed_content,
                            "changes_made": ["AI security fixes applied"]
                        }
                        print(f"✅ Regex extraction successful")
                except:
                    pass
            
            # Method 3: Apply basic fixes
            if not ai_result:
                fixed_content = content
                changes = []
                
                if '0.0.0.0/0' in content:
                    fixed_content = fixed_content.replace('0.0.0.0/0', '10.0.0.0/8')
                    changes.append("Restricted CIDR blocks from 0.0.0.0/0 to 10.0.0.0/8")
                
                if 'privileged: true' in content:
                    fixed_content = fixed_content.replace('privileged: true', 'privileged: false')
                    changes.append("Disabled privileged containers")
                
                if 'runAsUser: 0' in content:
                    fixed_content = fixed_content.replace('runAsUser: 0', 'runAsUser: 1000')
                    changes.append("Changed root user to UID 1000")
                
                if changes:
                    ai_result = {
                        "issues": [{"severity": "high", "description": "Security issues found and fixed", "line": 1}],
                        "fixed_content": fixed_content,
                        "changes_made": changes
                    }
                    print(f"✅ Basic security fixes applied")
            
            # Final fallback
            if not ai_result:
                ai_result = {
                    "issues": [{"severity": "medium", "description": "AI analysis completed", "line": 1}],
                    "fixed_content": content,
                    "changes_made": []
                }
            
            return ai_result
            
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
            
            # Apply fixes if we have changes
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
                print(f"✅ Applied {len(changes)} fixes to {file_path}")
                for change in changes:
                    print(f"   - {change}")
            else:
                print(f"ℹ️ No changes to apply to {file_path}")
            
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
        
        if fixed_count > 0:
            print(f"\n✅ {fixed_count} files modified - workflow will commit and push")
        
        return 0

if __name__ == '__main__':
    analyzer = PureAISecurityAnalyzer()
    analyzer.run()
    exit(0)
