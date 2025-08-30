#!/usr/bin/env python3
import os
import json
import boto3
import glob
import re
import subprocess

class AISecurityFixer:
    def __init__(self):
        self.bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
        self.api_calls = 0
        self.fixes_applied = []
        
    def detect_and_fix_issues(self, content, filename):
        """Detect issues and apply automatic fixes"""
        original_content = content
        fixed_content = content
        issues = []
        
        # Fix 1: Replace 0.0.0.0/0 with restricted CIDR
        if '0.0.0.0/0' in content and '.tf' in filename:
            fixed_content = re.sub(r'0\.0\.0\.0/0', '10.0.0.0/8', fixed_content)
            issues.append({
                'severity': 'high',
                'description': 'Fixed: Replaced 0.0.0.0/0 with 10.0.0.0/8',
                'fixed': True
            })
        
        # Fix 2: Add encryption to S3 buckets
        if 'resource "aws_s3_bucket"' in content and 'server_side_encryption_configuration' not in content:
            bucket_pattern = r'(resource "aws_s3_bucket" "[^"]*" \{[^}]*)\}'
            encryption_block = '''  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
    }
  }
}'''
            fixed_content = re.sub(bucket_pattern, r'\1\n' + encryption_block, fixed_content)
            issues.append({
                'severity': 'medium',
                'description': 'Fixed: Added S3 bucket encryption',
                'fixed': True
            })
        
        # Fix 3: Remove privileged containers
        if 'privileged: true' in content:
            fixed_content = re.sub(r'privileged:\s*true', 'privileged: false', fixed_content)
            issues.append({
                'severity': 'high', 
                'description': 'Fixed: Disabled privileged containers',
                'fixed': True
            })
        
        # Fix 4: Change root user to non-root
        if 'runAsUser: 0' in content:
            fixed_content = re.sub(r'runAsUser:\s*0', 'runAsUser: 1000', fixed_content)
            issues.append({
                'severity': 'high',
                'description': 'Fixed: Changed root user to UID 1000',
                'fixed': True
            })
        
        # Fix 5: Add resource limits to containers
        if 'containers:' in content and 'resources: {}' in content:
            resource_limits = '''resources:
          limits:
            memory: "512Mi"
            cpu: "500m"
          requests:
            memory: "256Mi"
            cpu: "250m"'''
            fixed_content = re.sub(r'resources:\s*\{\}', resource_limits, fixed_content)
            issues.append({
                'severity': 'medium',
                'description': 'Fixed: Added container resource limits',
                'fixed': True
            })
        
        # Use AI for complex fixes if needed
        if issues and len(fixed_content) != len(original_content):
            ai_suggestions = self.get_ai_suggestions(original_content, filename)
            issues.extend(ai_suggestions)
        
        return fixed_content, issues
    
    def get_ai_suggestions(self, content, filename):
        """Use Nova Micro for additional security suggestions"""
        prompt = f"Security fixes for {filename}:\n{content[:500]}\nSuggest 1-2 critical fixes. Brief response:"
        
        try:
            response = self.bedrock.invoke_model(
                modelId='amazon.nova-micro-v1:0',
                body=json.dumps({
                    'inputText': prompt,
                    'textGenerationConfig': {
                        'maxTokenCount': 100,
                        'temperature': 0.1
                    }
                })
            )
            
            self.api_calls += 1
            result = json.loads(response['body'].read())
            suggestion = result['results'][0]['outputText']
            
            return [{
                'severity': 'medium',
                'description': f'AI Suggestion: {suggestion[:100]}',
                'fixed': False
            }]
            
        except Exception as e:
            print(f"AI suggestion failed: {e}")
            return []
    
    def apply_fixes_to_file(self, file_path):
        """Apply fixes to a single file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            fixed_content, issues = self.detect_and_fix_issues(original_content, file_path)
            
            # Write fixed content back to file
            if fixed_content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                
                self.fixes_applied.append({
                    'file': file_path,
                    'issues_fixed': len([i for i in issues if i.get('fixed')])
                })
                print(f"✅ Fixed {len([i for i in issues if i.get('fixed')])} issues in {file_path}")
            
            return issues
            
        except Exception as e:
            print(f"Error fixing {file_path}: {e}")
            return []
    
    def commit_and_push_fixes(self):
        """Commit and push fixes back to repo"""
        if not self.fixes_applied:
            return
        
        try:
            # Configure git
            subprocess.run(['git', 'config', 'user.name', 'AI Security Fixer'], check=True)
            subprocess.run(['git', 'config', 'user.email', 'security-bot@ai-ops.com'], check=True)
            
            # Add fixed files
            for fix in self.fixes_applied:
                subprocess.run(['git', 'add', fix['file']], check=True)
            
            # Commit fixes
            total_fixes = sum(fix['issues_fixed'] for fix in self.fixes_applied)
            commit_msg = f"🤖 AI Security Fixes: {total_fixes} issues auto-fixed\n\n"
            
            for fix in self.fixes_applied:
                commit_msg += f"- {fix['file']}: {fix['issues_fixed']} fixes\n"
            
            subprocess.run(['git', 'commit', '-m', commit_msg], check=True)
            
            # Push to current branch
            current_branch = subprocess.run(['git', 'branch', '--show-current'], 
                                          capture_output=True, text=True, check=True).stdout.strip()
            subprocess.run(['git', 'push', 'origin', current_branch], check=True)
            
            print(f"🚀 Pushed {total_fixes} security fixes to {current_branch}")
            
        except subprocess.CalledProcessError as e:
            print(f"Git operation failed: {e}")
    
    def run(self):
        # Find infrastructure files
        patterns = ['*.tf', '*.yaml', '*.yml']
        files = []
        for pattern in patterns:
            files.extend(glob.glob(pattern))
        
        files = [f for f in files if os.path.getsize(f) < 5120]  # 5KB limit
        
        print(f"🔧 AI Security Fixer: {len(files)} files")
        
        all_issues = []
        
        for file_path in files:
            print(f"Analyzing & Fixing: {file_path}")
            issues = self.apply_fixes_to_file(file_path)
            
            for issue in issues:
                issue['file'] = file_path
                all_issues.append(issue)
        
        # Commit and push fixes
        self.commit_and_push_fixes()
        
        # Calculate costs
        input_cost = (self.api_calls * 200 / 1000000) * 35.00
        output_cost = (self.api_calls * 50 / 1000000) * 140.00
        total_cost = input_cost + output_cost
        
        # Generate summary
        fixed_count = len([i for i in all_issues if i.get('fixed')])
        remaining_count = len([i for i in all_issues if not i.get('fixed')])
        
        if remaining_count > 0:
            summary = f"🤖 {fixed_count} issues auto-fixed, {remaining_count} need manual review"
        else:
            summary = f"✅ {fixed_count} issues auto-fixed, all clear!"
        
        results = {
            'summary': summary,
            'issues': all_issues,
            'files_scanned': len(files),
            'fixes_applied': len(self.fixes_applied),
            'scan_cost': round(total_cost, 6),
            'estimated_monthly_cost': round(total_cost * 30, 4)
        }
        
        with open('security-results.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n🤖 AI Security Fixer Results:")
        print(f"   Files processed: {len(files)}")
        print(f"   Issues auto-fixed: {fixed_count}")
        print(f"   Cost: ${round(total_cost, 6)}")
        print(f"   Fixes pushed to repo: {len(self.fixes_applied)} files")
        
        return remaining_count

if __name__ == '__main__':
    fixer = AISecurityFixer()
    remaining_issues = fixer.run()
    exit(1 if remaining_issues > 0 else 0)
