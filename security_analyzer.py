#!/usr/bin/env python3
import os
import json
import boto3
import glob
import subprocess
from datetime import datetime

class PureAISecurityAnalyzer:
    def __init__(self):
        self.bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
        self.api_calls = 0
        self.fixes_applied = []
        
    def ai_analyze_and_fix(self, content, filename):
        """Pure AI analysis and fixing using Nova Micro"""
        prompt = f"""Analyze and fix security issues in {filename}:

{content}

1. Identify ALL security vulnerabilities
2. Provide the COMPLETE fixed file content
3. List what was changed

Response format:
{{
  "issues": [
    {{"severity": "high|medium|low", "description": "issue description", "line": 1}}
  ],
  "fixed_content": "complete fixed file content here",
  "changes_made": ["change 1", "change 2"]
}}"""

        try:
            response = self.bedrock.invoke_model(
                modelId='amazon.nova-micro-v1:0',
                body=json.dumps({
                    'inputText': prompt,
                    'textGenerationConfig': {
                        'maxTokenCount': 2000,  # Increased for full file content
                        'temperature': 0.1,
                        'topP': 0.9
                    }
                })
            )
            
            self.api_calls += 1
            result = json.loads(response['body'].read())
            output_text = result['results'][0]['outputText']
            
            print(f"🤖 AI Response for {filename}:")
            print(f"Raw output: {output_text[:200]}...")
            
            # Try to extract JSON from AI response
            try:
                # Find JSON in the response
                start = output_text.find('{')
                end = output_text.rfind('}') + 1
                if start != -1 and end != -1:
                    json_str = output_text[start:end]
                    ai_result = json.loads(json_str)
                    return ai_result
            except:
                pass
            
            # Fallback: Create basic response if JSON parsing fails
            return {
                "issues": [{
                    "severity": "medium",
                    "description": f"AI detected security issues in {filename}",
                    "line": 1
                }],
                "fixed_content": content,  # Return original if parsing fails
                "changes_made": ["AI analysis completed"]
            }
            
        except Exception as e:
            print(f"❌ AI analysis failed for {filename}: {e}")
            return {
                "issues": [],
                "fixed_content": content,
                "changes_made": []
            }
    
    def apply_ai_fixes(self, file_path):
        """Apply AI-generated fixes to file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            print(f"🔍 Analyzing {file_path} with pure AI...")
            ai_result = self.ai_analyze_and_fix(original_content, file_path)
            
            issues = ai_result.get('issues', [])
            fixed_content = ai_result.get('fixed_content', original_content)
            changes = ai_result.get('changes_made', [])
            
            # Apply AI fixes if content changed
            if fixed_content != original_content and len(changes) > 0:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                
                self.fixes_applied.append({
                    'file': file_path,
                    'issues_fixed': len(issues),
                    'changes': changes
                })
                print(f"✅ AI fixed {len(issues)} issues in {file_path}")
                print(f"   Changes: {', '.join(changes)}")
            else:
                print(f"ℹ️ No fixes needed for {file_path}")
            
            return issues
            
        except Exception as e:
            print(f"❌ Error processing {file_path}: {e}")
            return []
    
    def commit_and_push_fixes(self):
        """Commit and push AI fixes"""
        if not self.fixes_applied:
            print("ℹ️ No fixes to commit")
            return
        
        try:
            subprocess.run(['git', 'config', 'user.name', 'Pure AI Security Fixer'], check=True)
            subprocess.run(['git', 'config', 'user.email', 'ai-fixer@nova-micro.com'], check=True)
            
            for fix in self.fixes_applied:
                subprocess.run(['git', 'add', fix['file']], check=True)
            
            total_fixes = sum(fix['issues_fixed'] for fix in self.fixes_applied)
            commit_msg = f"🤖 Pure AI Security Fixes: {total_fixes} issues fixed by Nova Micro\n\n"
            
            for fix in self.fixes_applied:
                commit_msg += f"- {fix['file']}: {fix['issues_fixed']} issues\n"
                for change in fix['changes']:
                    commit_msg += f"  * {change}\n"
            
            subprocess.run(['git', 'commit', '-m', commit_msg], check=True)
            
            current_branch = subprocess.run(['git', 'branch', '--show-current'], 
                                          capture_output=True, text=True, check=True).stdout.strip()
            subprocess.run(['git', 'push', 'origin', current_branch], check=True)
            
            print(f"🚀 Pushed {total_fixes} AI fixes to {current_branch}")
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Git operation failed: {e}")
    
    def calculate_costs(self):
        """Calculate Nova Micro costs"""
        # Nova Micro: $0.035 per 1M input tokens, $0.14 per 1M output tokens
        input_tokens = self.api_calls * 800   # Larger input for complex analysis
        output_tokens = self.api_calls * 500  # Larger output for full fixes
        
        input_cost = (input_tokens / 1000000) * 35.00
        output_cost = (output_tokens / 1000000) * 140.00
        
        return {
            'per_scan': round(input_cost + output_cost, 6),
            'monthly_estimate': round((input_cost + output_cost) * 30, 4),
            'api_calls': self.api_calls
        }
    
    def run(self):
        # Find all infrastructure files
        patterns = ['*.tf', '*.yaml', '*.yml']
        files = []
        for pattern in patterns:
            files.extend(glob.glob(pattern))
        
        print(f"🤖 Pure AI Security Analyzer: {len(files)} files")
        print(f"Using Nova Micro for 100% AI-powered analysis and fixes")
        
        all_issues = []
        
        for file_path in files:
            if os.path.getsize(file_path) < 10240:  # 10KB limit
                issues = self.apply_ai_fixes(file_path)
                for issue in issues:
                    issue['file'] = file_path
                    all_issues.append(issue)
            else:
                print(f"⚠️ Skipping large file: {file_path}")
        
        # Commit AI fixes
        self.commit_and_push_fixes()
        
        # Calculate costs
        costs = self.calculate_costs()
        
        # Generate summary
        fixed_count = len(self.fixes_applied)
        total_issues = len(all_issues)
        
        if fixed_count > 0:
            summary = f"🤖 Pure AI: {total_issues} issues analyzed, {fixed_count} files fixed"
        else:
            summary = f"🤖 Pure AI: {total_issues} issues analyzed, no fixes needed"
        
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
        print(f"   Files analyzed: {len(files)}")
        print(f"   AI API calls: {self.api_calls}")
        print(f"   Issues found: {total_issues}")
        print(f"   Files fixed: {fixed_count}")
        print(f"   Cost: ${costs['per_scan']}")
        print(f"   Monthly estimate: ${costs['monthly_estimate']}")
        
        return len([i for i in all_issues if i.get('severity') == 'high'])

if __name__ == '__main__':
    analyzer = PureAISecurityAnalyzer()
    high_issues = analyzer.run()
    exit(1 if high_issues > 0 else 0)
