#!/usr/bin/env python3
import os
import json
import glob
import re

class FreeSecurityAnalyzer:
    """100% FREE security analyzer using only regex patterns"""
    
    def __init__(self):
        self.rules = {
            'open_security_groups': {
                'pattern': r'0\.0\.0\.0/0',
                'severity': 'high',
                'description': 'Security group open to world (0.0.0.0/0)'
            },
            'hardcoded_passwords': {
                'pattern': r'password\s*=\s*["\'][^"\']{3,}["\']',
                'severity': 'high', 
                'description': 'Hardcoded password detected'
            },
            'privileged_containers': {
                'pattern': r'privileged:\s*true',
                'severity': 'high',
                'description': 'Privileged container detected'
            },
            'root_user': {
                'pattern': r'runAsUser:\s*0',
                'severity': 'high',
                'description': 'Container running as root user'
            },
            'hardcoded_secrets': {
                'pattern': r'(api_key|secret|token)\s*[=:]\s*["\'][^"\']{10,}["\']',
                'severity': 'high',
                'description': 'Hardcoded secret/API key detected'
            },
            'no_encryption': {
                'pattern': r'resource\s+"aws_s3_bucket".*?{[^}]*}',
                'severity': 'medium',
                'description': 'S3 bucket without encryption'
            }
        }
    
    def scan_file(self, content, filename):
        issues = []
        lines = content.split('\n')
        
        for rule_name, rule in self.rules.items():
            for i, line in enumerate(lines, 1):
                if re.search(rule['pattern'], line, re.IGNORECASE):
                    issues.append({
                        'severity': rule['severity'],
                        'description': rule['description'],
                        'line': i,
                        'file': filename,
                        'rule': rule_name
                    })
        
        return issues
    
    def run(self):
        # Scan infrastructure files
        patterns = ['*.tf', '*.yaml', '*.yml']
        files = []
        for pattern in patterns:
            files.extend(glob.glob(pattern))
        
        print(f"FREE scan: {len(files)} files")
        
        all_issues = []
        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                print(f"Scanning: {file_path}")
                issues = self.scan_file(content, file_path)
                all_issues.extend(issues)
                
            except Exception as e:
                print(f"Error: {e}")
        
        high_count = len([i for i in all_issues if i['severity'] == 'high'])
        medium_count = len([i for i in all_issues if i['severity'] == 'medium'])
        
        if high_count > 0:
            summary = f"❌ {high_count} critical, {medium_count} medium issues"
        elif medium_count > 0:
            summary = f"⚠️ {medium_count} medium issues"
        else:
            summary = "✅ No security issues detected"
        
        results = {
            'summary': summary,
            'issues': all_issues,
            'files_scanned': len(files),
            'estimated_monthly_cost': 0.00,
            'scan_cost': 0.00
        }
        
        with open('security-results.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n💰 FREE Analysis:")
        print(f"   Files: {len(files)}")
        print(f"   Issues: {len(all_issues)}")
        print(f"   Cost: $0.00 (100% FREE)")
        
        return high_count

if __name__ == '__main__':
    analyzer = FreeSecurityAnalyzer()
    high_issues = analyzer.run()
    exit(1 if high_issues > 0 else 0)
