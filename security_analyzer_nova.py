#!/usr/bin/env python3
import os
import json
import boto3
import glob
import re
from datetime import datetime

class NovaSecurityAnalyzer:
    def __init__(self):
        self.bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
        self.api_calls = 0
        
    def rule_based_check(self, content, filename):
        """Free pre-filtering"""
        issues = []
        lines = content.split('\n')
        
        critical_patterns = {
            '0.0.0.0/0': 'Security group open to world',
            'privileged: true': 'Privileged container',
            'runAsUser: 0': 'Container running as root'
        }
        
        for i, line in enumerate(lines, 1):
            for pattern, desc in critical_patterns.items():
                if pattern in line:
                    issues.append({
                        'severity': 'high',
                        'description': desc,
                        'line': i,
                        'file': filename
                    })
        
        return issues
    
    def nova_analyze(self, content, filename):
        """Use Nova Micro for AI analysis"""
        # Ultra-short prompt for Nova Micro
        prompt = f"Security check {filename}:\n{content[:800]}\nCritical issues only. JSON:"
        
        try:
            response = self.bedrock.invoke_model(
                modelId='amazon.nova-micro-v1:0',  # Cheapest model
                body=json.dumps({
                    'inputText': prompt,
                    'textGenerationConfig': {
                        'maxTokenCount': 150,  # Minimal output
                        'temperature': 0.1,
                        'topP': 0.9
                    }
                })
            )
            
            self.api_calls += 1
            result = json.loads(response['body'].read())
            
            # Extract issues from Nova response
            output_text = result['results'][0]['outputText']
            
            # Simple parsing for Nova output
            if 'high' in output_text.lower() or 'critical' in output_text.lower():
                return {
                    'issues': [{
                        'severity': 'high',
                        'description': 'AI detected security issue',
                        'line': 1
                    }]
                }
                
        except Exception as e:
            print(f"Nova analysis failed for {filename}: {e}")
            
        return {"issues": []}

    def calculate_costs(self):
        # Nova Micro pricing: $0.035 per 1M input, $0.14 per 1M output tokens
        input_tokens = self.api_calls * 200  # Reduced input
        output_tokens = self.api_calls * 50   # Minimal output
        
        input_cost = (input_tokens / 1000000) * 35.00  # $0.035 per 1K = $35 per 1M
        output_cost = (output_tokens / 1000000) * 140.00  # $0.14 per 1K = $140 per 1M
        
        return {
            'per_scan': round(input_cost + output_cost, 6),
            'monthly_estimate': round((input_cost + output_cost) * 30, 4),
            'api_calls': self.api_calls
        }

    def run(self):
        # Scan only small files
        patterns = ['*.tf', '*.yaml', '*.yml']
        files = []
        for pattern in patterns:
            files.extend(glob.glob(pattern))
        
        # Ultra-strict limits for Nova
        files = [f for f in files if os.path.getsize(f) < 3072]  # 3KB max
        files = files[:5]  # Max 5 files
        
        print(f"Nova Micro scan: {len(files)} files")
        
        all_issues = []
        
        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()[:1200]  # 1.2KB max per file
                
                print(f"Checking: {file_path}")
                
                # Rule-based check first (FREE)
                rule_issues = self.rule_based_check(content, file_path)
                all_issues.extend(rule_issues)
                
                # Use Nova only if no obvious issues found
                if not rule_issues:
                    nova_issues = self.nova_analyze(content, file_path)
                    for issue in nova_issues.get('issues', []):
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
        
        print(f"\n💰 Nova Micro Analysis:")
        print(f"   Files: {len(files)}")
        print(f"   AI calls: {self.api_calls}")
        print(f"   Cost: ${costs['per_scan']}")
        print(f"   Monthly: ${costs['monthly_estimate']}")
        
        return high_count

if __name__ == '__main__':
    analyzer = NovaSecurityAnalyzer()
    high_issues = analyzer.run()
    exit(1 if high_issues > 0 else 0)
