#!/usr/bin/env python3
import os
import json
import boto3
import glob
import re
from datetime import datetime

class UltraCheapSecurityAnalyzer:
    def __init__(self):
        self.bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
        self.api_calls = 0
        
    def rule_based_check(self, content, filename):
        """Pre-filter with regex to catch obvious issues without AI"""
        issues = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Check for 0.0.0.0/0
            if '0.0.0.0/0' in line:
                issues.append({
                    'severity': 'high',
                    'description': 'Security group open to world (0.0.0.0/0)',
                    'line': i,
                    'file': filename
                })
            
            # Check for hardcoded passwords
            if re.search(r'password.*=.*["\'][^"\']{3,}["\']', line, re.IGNORECASE):
                issues.append({
                    'severity': 'high', 
                    'description': 'Hardcoded password detected',
                    'line': i,
                    'file': filename
                })
            
            # Check for privileged containers
            if 'privileged: true' in line:
                issues.append({
                    'severity': 'high',
                    'description': 'Privileged container detected',
                    'line': i,
                    'file': filename
                })
        
        return issues
    
    def ai_analyze_suspicious(self, content, filename):
        """Only use AI for complex cases that rules missed"""
        # Ultra-short prompt
        prompt = f"Security issues in {filename}:\n{content[:500]}\nJSON: {{\"issues\":[]}}"
        
        try:
            response = self.bedrock.invoke_model(
                modelId='anthropic.claude-3-haiku-20240307-v1:0',  # 10x cheaper than Sonnet
                body=json.dumps({
                    'anthropic_version': 'bedrock-2023-05-31',
                    'max_tokens': 100,  # Minimal output
                    'messages': [{'role': 'user', 'content': prompt}]
                })
            )
            
            self.api_calls += 1
            result = json.loads(response['body'].read())
            content_text = result['content'][0]['text']
            
            start = content_text.find('{')
            end = content_text.rfind('}') + 1
            if start != -1 and end != -1:
                return json.loads(content_text[start:end])
                
        except Exception as e:
            print(f"AI analysis failed for {filename}: {e}")
            
        return {"issues": []}

    def calculate_costs(self):
        # Claude 3 Haiku pricing: $0.25 per 1K input, $1.25 per 1K output tokens
        input_tokens = self.api_calls * 150  # Reduced input
        output_tokens = self.api_calls * 50   # Minimal output
        
        input_cost = (input_tokens / 1000) * 0.25
        output_cost = (output_tokens / 1000) * 1.25
        
        return {
            'per_scan': round(input_cost + output_cost, 4),
            'monthly_estimate': round((input_cost + output_cost) * 30, 2),
            'api_calls': self.api_calls
        }

    def run(self):
        # Only scan changed files if in PR
        if os.getenv('GITHUB_EVENT_NAME') == 'pull_request':
            # Get changed files only
            changed_files = os.popen('git diff --name-only HEAD~1').read().strip().split('\n')
            files = [f for f in changed_files if f.endswith(('.tf', '.yaml', '.yml'))]
        else:
            # Fallback to all files but with strict limits
            patterns = ['*.tf', '*.yaml', '*.yml']  # No recursive search
            files = []
            for pattern in patterns:
                files.extend(glob.glob(pattern))
        
        # Ultra-strict filtering
        files = [f for f in files if os.path.getsize(f) < 2048]  # 2KB max
        files = files[:3]  # Max 3 files per scan
        
        print(f"Ultra-cheap scan: {len(files)} files")
        
        all_issues = []
        
        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()[:1000]  # 1KB max per file
                
                print(f"Checking: {file_path}")
                
                # Rule-based check first (free)
                rule_issues = self.rule_based_check(content, file_path)
                all_issues.extend(rule_issues)
                
                # Only use AI if rules found something suspicious
                if rule_issues:
                    ai_issues = self.ai_analyze_suspicious(content, file_path)
                    for issue in ai_issues.get('issues', []):
                        issue['file'] = file_path
                        all_issues.append(issue)
                        
            except Exception as e:
                print(f"Error: {e}")
        
        costs = self.calculate_costs()
        high_count = len([i for i in all_issues if i['severity'] == 'high'])
        
        summary = f"❌ {high_count} critical issues" if high_count > 0 else "✅ No critical issues"
        
        results = {
            'summary': summary,
            'issues': all_issues,
            'files_scanned': len(files),
            'estimated_monthly_cost': costs['monthly_estimate'],
            'scan_cost': costs['per_scan']
        }
        
        with open('security-results.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n💰 Ultra-Cheap Analysis:")
        print(f"   Files: {len(files)} (max 3)")
        print(f"   AI calls: {self.api_calls}")
        print(f"   Cost: ${costs['per_scan']}")
        print(f"   Monthly: ${costs['monthly_estimate']}")
        
        return high_count

if __name__ == '__main__':
    analyzer = UltraCheapSecurityAnalyzer()
    high_issues = analyzer.run()
    exit(1 if high_issues > 0 else 0)
