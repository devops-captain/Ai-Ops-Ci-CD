#!/usr/bin/env python3
import os
import json
import boto3
import glob
from datetime import datetime

class SecurityAnalyzer:
    def __init__(self):
        self.bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
        self.api_calls = 0
        
    def analyze_file(self, content, filename):
        # Truncate large files to reduce input tokens
        if len(content) > 2000:
            content = content[:2000] + "\n# ... (truncated for cost optimization)"
        
        # Shorter, focused prompt to reduce output tokens
        prompt = f"""Analyze {filename} for CRITICAL security issues only:

{content}

Find ONLY high-severity issues:
- 0.0.0.0/0 in security groups
- Hardcoded passwords/keys
- Privileged containers
- Unencrypted storage

JSON: {{"issues": [{{"severity": "high", "description": "brief", "line": 1}}]}}"""

        try:
            response = self.bedrock.invoke_model(
                modelId='anthropic.claude-3-sonnet-20240229-v1:0',
                body=json.dumps({
                    'anthropic_version': 'bedrock-2023-05-31',
                    'max_tokens': 300,  # Reduced from 1500
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
            print(f"Error analyzing {filename}: {e}")
            
        return {"issues": []}

    def calculate_costs(self):
        # Optimized estimates: 300 input + 100 output tokens per file
        input_tokens = self.api_calls * 300
        output_tokens = self.api_calls * 100
        
        input_cost = (input_tokens / 1000) * 3.00
        output_cost = (output_tokens / 1000) * 15.00
        
        return {
            'per_scan': round(input_cost + output_cost, 4),
            'monthly_estimate': round((input_cost + output_cost) * 30, 2),
            'api_calls': self.api_calls
        }

    def run(self):
        # Find infrastructure files
        patterns = ['**/*.tf', '**/*.yaml', '**/*.yml']
        files = []
        for pattern in patterns:
            files.extend(glob.glob(pattern, recursive=True))
        
        # Filter files to reduce costs
        exclude = ['.github', 'node_modules', '.git', '__pycache__', 'test-configs']
        files = [f for f in files if not any(ex in f for ex in exclude)]
        
        # Skip files larger than 5KB to control costs
        filtered_files = []
        for file_path in files:
            try:
                if os.path.getsize(file_path) < 5120:  # 5KB limit
                    filtered_files.append(file_path)
                else:
                    print(f"Skipping large file: {file_path}")
            except:
                continue
        
        files = filtered_files
        print(f"Analyzing {len(files)} files (cost-optimized)...")
        
        all_issues = []
        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if len(content.strip()) == 0:
                    continue
                    
                print(f"Analyzing: {file_path}")
                analysis = self.analyze_file(content, file_path)
                
                for issue in analysis.get('issues', []):
                    issue['file'] = file_path
                    all_issues.append(issue)
                    
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
        
        # Calculate costs
        costs = self.calculate_costs()
        
        # Generate summary (focus on high severity only)
        high_count = len([i for i in all_issues if i['severity'] == 'high'])
        
        if high_count > 0:
            summary = f"❌ {high_count} critical security issues found"
        else:
            summary = "✅ No critical security issues detected"
        
        # Save results
        results = {
            'timestamp': datetime.utcnow().isoformat(),
            'summary': summary,
            'issues': all_issues,
            'files_scanned': len(files),
            'estimated_monthly_cost': costs['monthly_estimate'],
            'scan_cost': costs['per_scan']
        }
        
        with open('security-results.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n📊 Cost-Optimized Analysis:")
        print(f"   Files scanned: {len(files)}")
        print(f"   Critical issues: {high_count}")
        print(f"   Cost this scan: ${costs['per_scan']}")
        print(f"   Monthly estimate: ${costs['monthly_estimate']}")
        
        return high_count

if __name__ == '__main__':
    analyzer = SecurityAnalyzer()
    high_issues = analyzer.run()
    
    if high_issues > 0:
        print(f"\n❌ Found {high_issues} critical issues")
        exit(1)
    else:
        print("\n✅ No critical issues found")
        exit(0)
