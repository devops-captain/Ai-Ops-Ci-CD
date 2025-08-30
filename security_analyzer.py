#!/usr/bin/env python3
import os
import json
import boto3
import glob
import subprocess
import re
from datetime import datetime

class PureAISecurityAnalyzer:
    def __init__(self):
        self.bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
        self.api_calls = 0
        self.fixes_applied = []
        
    def ai_analyze_and_fix(self, content, filename):
        """Pure AI analysis and fixing using Nova Micro - NO MANUAL RULES"""
        prompt = f"""You are a security expert. Analyze {filename} and fix ALL security issues.

Original file:
{content}

Provide the complete fixed file content with all security issues resolved.

Return ONLY this JSON:
{{
  "issues": [{{"severity": "high", "description": "issue found", "line": 1}}],
  "fixed_content": "COMPLETE SECURE FILE CONTENT HERE",
  "changes_made": ["change 1", "change 2"]
}}"""

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
                        "maxTokens": 2500,
                        "temperature": 0.1,
                        "topP": 0.9
                    }
                })
            )
            
            self.api_calls += 1
            result = json.loads(response['body'].read())
            output_text = result['output']['message']['content'][0]['text']
            
            print(f"🤖 AI analyzing {filename}...")
            print(f"AI response length: {len(output_text)} chars")
            
            # Extract JSON from AI response
            try:
                # Find JSON block more aggressively
                json_patterns = [
                    r'\{[^{}]*"fixed_content"[^{}]*"[^"]*"[^{}]*\}',
                    r'\{.*?"fixed_content".*?\}',
                    r'\{.*\}'
                ]
                
                for pattern in json_patterns:
                    json_match = re.search(pattern, output_text, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(0)
                        try:
                            ai_result = json.loads(json_str)
                            if 'fixed_content' in ai_result and ai_result['fixed_content']:
                                print(f"✅ Successfully parsed AI JSON response")
                                return ai_result
                        except:
                            continue
                
                # If JSON extraction fails, try to get fixed content directly
                print("⚠️ JSON parsing failed, extracting content manually")
                
                # Look for code blocks or content after "fixed_content"
                content_patterns = [
                    r'```(?:terraform|yaml|tf)?\s*(.*?)```',
                    r'"fixed_content":\s*"([^"]*(?:\\.[^"]*)*)"',
                    r'Fixed content:\s*(.*?)(?:\n\n|\Z)',
                ]
                
                for pattern in content_patterns:
                    content_match = re.search(pattern, output_text, re.DOTALL | re.IGNORECASE)
                    if content_match:
                        fixed_content = content_match.group(1).strip()
                        if len(fixed_content) > 50:  # Reasonable content length
                            print(f"✅ Extracted fixed content ({len(fixed_content)} chars)")
                            return {
                                "issues": [{"severity": "high", "description": "AI detected and fixed security issues", "line": 1}],
                                "fixed_content": fixed_content.replace('\\n', '\n').replace('\\"', '"'),
                                "changes_made": ["AI applied comprehensive security fixes"]
                            }
                
                print("❌ Could not extract fixed content from AI response")
                return {
                    "issues": [{"severity": "medium", "description": "AI analysis completed but no fixes extracted", "line": 1}],
                    "fixed_content": content,
                    "changes_made": []
                }
                    
            except Exception as parse_error:
                print(f"❌ Content extraction failed: {parse_error}")
                return {
                    "issues": [],
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
        """Apply ONLY AI-generated fixes"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            ai_result = self.ai_analyze_and_fix(original_content, file_path)
            
            issues = ai_result.get('issues', [])
            fixed_content = ai_result.get('fixed_content', original_content)
            changes = ai_result.get('changes_made', [])
            
            # Apply AI fixes if we have meaningful changes
            if (fixed_content != original_content and 
                len(fixed_content) > 20 and 
                len(changes) > 0):
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                
                self.fixes_applied.append({
                    'file': file_path,
                    'issues_fixed': len(issues),
                    'changes': changes
                })
                print(f"✅ AI fixed {len(issues)} issues in {file_path}")
                for change in changes:
                    print(f"   - {change}")
            else:
                print(f"ℹ️ No AI fixes applied to {file_path}")
            
            return issues
            
        except Exception as e:
            print(f"❌ Error processing {file_path}: {e}")
            return []
    
    def commit_and_push_fixes(self):
        """Commit and push AI fixes"""
        if not self.fixes_applied:
            print("ℹ️ No AI fixes to commit")
            return
        
        try:
            subprocess.run(['git', 'config', 'user.name', 'Pure AI Security Fixer'], check=True)
            subprocess.run(['git', 'config', 'user.email', 'ai@nova-micro.com'], check=True)
            
            for fix in self.fixes_applied:
                subprocess.run(['git', 'add', fix['file']], check=True)
            
            total_fixes = sum(fix['issues_fixed'] for fix in self.fixes_applied)
            commit_msg = f"🤖 Pure AI Security Fixes: {total_fixes} issues fixed by Nova Micro\n\n"
            
            for fix in self.fixes_applied:
                commit_msg += f"- {fix['file']}: {fix['issues_fixed']} issues\n"
                for change in fix['changes']:
                    commit_msg += f"  * {change}\n"
            
            subprocess.run(['git', 'commit', '-m', commit_msg], check=True)
            
            current_branch = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], 
                                          capture_output=True, text=True, check=True).stdout.strip()
            if current_branch:
                subprocess.run(['git', 'push', 'origin', current_branch], check=True)
                print(f"🚀 Pushed {total_fixes} pure AI fixes to {current_branch}")
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Git operation failed: {e}")
    
    def calculate_costs(self):
        """Calculate Nova Micro costs"""
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
        print("Using 100% AI intelligence - NO manual rules")
        
        all_issues = []
        
        for file_path in files:
            if os.path.getsize(file_path) < 10240:  # 10KB limit
                issues = self.apply_ai_fixes(file_path)
                for issue in issues:
                    issue['file'] = file_path
                    all_issues.append(issue)
        
        self.commit_and_push_fixes()
        
        costs = self.calculate_costs()
        fixed_count = len(self.fixes_applied)
        total_issues = len(all_issues)
        
        summary = f"🤖 Pure AI: {total_issues} issues analyzed, {fixed_count} files fixed"
        
        results = {
            'summary': summary,
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
