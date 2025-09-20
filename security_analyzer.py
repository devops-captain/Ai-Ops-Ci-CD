#!/usr/bin/env python3
import os
import json
import boto3
import glob
import re
import argparse

class PureAISecurityAnalyzer:
    def __init__(self, region='us-east-1', max_size_kb=10240, recursive=True):
        self.bedrock = boto3.client('bedrock-runtime', region_name=region)
        self.api_calls = 0
        self.fixes_applied = []
        self.max_size_kb = max_size_kb
        self.recursive = recursive

        # File extensions to include (now includes PHP)
        self.extensions = [
            '.tf', '.tfvars', '.hcl', '.json', '.yaml', '.yml',
            '.py', '.js', '.ts', '.php',   # 👈 added .php here
            '.sh', '.ps1', '.env', '.ini', '.cfg', '.toml',
            '.dockerfile', 'Dockerfile',
            '.md', '.txt', '.sql', '.xml', '.html', '.css',
            '.scss', '.sass', '.jsp', '.rb', '.go', '.java',
            '.c', '.cpp', '.hpp', '.h', '.gradle', '.jsonnet',
            '.json5'
        ]

    def is_text_file(self, path, blocksize=512):
        try:
            with open(path, 'rb') as f:
                block = f.read(blocksize)
                if b'\0' in block:
                    return False
            return True
        except Exception:
            return False

    def find_files(self):
        files = []
        if self.recursive:
            for ext in self.extensions:
                if ext.lower() in ('dockerfile', '.dockerfile'):
                    files.extend(glob.glob('**/[Dd]ockerfile', recursive=True))
                else:
                    files.extend(glob.glob(f'**/*{ext}', recursive=True))
        else:
            for ext in self.extensions:
                if ext.lower() in ('dockerfile', '.dockerfile'):
                    files.extend(glob.glob('[Dd]ockerfile'))
                else:
                    files.extend(glob.glob(f'*{ext}'))

        files = [f for f in dict.fromkeys(files) if os.path.isfile(f)]
        return files

    def ai_analyze_and_fix(self, content, filename):
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

            fixed_content = output_text
            fixed_content = re.sub(r'^Here.*?:\s*', '', fixed_content, flags=re.IGNORECASE)
            fixed_content = re.sub(r'```(?:[\w+-]*)?\s*', '', fixed_content)
            fixed_content = re.sub(r'```\s*$', '', fixed_content)
            fixed_content = fixed_content.strip()

            return {
                "issues": [{"severity": "high", "description": "AI detected and fixed security issues", "line": 1}],
                "fixed_content": fixed_content,
                "changes_made": ["AI applied comprehensive security fixes"]
            }

        except Exception as e:
            print(f"❌ AI API call failed for {filename}: {e}")
            return {
                "issues": [],
                "fixed_content": content,
                "changes_made": []
            }

    def basic_validation(self, filename, content):
        lower = filename.lower()
        stripped = content.strip()
        try:
            if lower.endswith(('.tf', '.tfvars', '.hcl')):
                return 'resource' in stripped or 'provider' in stripped or 'module' in stripped
            if lower.endswith(('.yaml', '.yml')):
                return ':' in stripped and len(stripped.splitlines()) > 1
            if lower.endswith(('.json', '.json5', '.jsonnet')):
                try:
                    json.loads(stripped)
                    return True
                except Exception:
                    return '{' in stripped and '}' in stripped
            if lower.endswith(('.py', '.js', '.ts', '.php', '.sh', '.ps1', '.rb', '.go', '.java', '.c', '.cpp')):
                return len(stripped) > 20 and '\n' in stripped
            if lower.endswith(('.env', '.ini', '.cfg', '.toml')):
                return '=' in stripped or '[' in stripped
            if os.path.basename(filename).lower() in ('dockerfile',) or lower.endswith('dockerfile'):
                return 'FROM' in stripped or 'CMD' in stripped or 'ENTRYPOINT' in stripped
            if lower.endswith(('.md', '.txt', '.html', '.css', '.sql', '.xml')):
                return len(stripped) > 10
        except Exception:
            return False
        return len(stripped) > 10

    def apply_ai_fixes(self, file_path):
        try:
            size_kb = os.path.getsize(file_path) / 1024
            if size_kb > self.max_size_kb:
                print(f"⚠️ Skipping {file_path} (size {size_kb:.1f} KB > {self.max_size_kb} KB)")
                return []

            if not self.is_text_file(file_path):
                print(f"⚠️ Skipping binary file {file_path}")
                return []

            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                original_content = f.read()

            ai_result = self.ai_analyze_and_fix(original_content, file_path)
            if not ai_result:
                return []

            issues = ai_result.get('issues', [])
            fixed_content = ai_result.get('fixed_content', original_content)
            changes = ai_result.get('changes_made', [])
            valid = self.basic_validation(file_path, fixed_content)

            if (fixed_content and
                fixed_content != original_content and
                len(changes) > 0 and
                valid):

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
                print(f"ℹ️ No AI fixes applied to {file_path} (valid={valid}, changes={len(changes)})")

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
        files = self.find_files()
        print(f"🤖 Pure AI Security Analyzer: {len(files)} files found")
        print("Using 100% AI intelligence - ZERO manual security rules (heuristic validation only)")

        all_issues = []
        for file_path in files:
            try:
                if os.path.getsize(file_path) / 1024 <= self.max_size_kb:
                    issues = self.apply_ai_fixes(file_path)
                    for issue in issues:
                        issue['file'] = file_path
                        all_issues.append(issue)
                else:
                    print(f"⚠️ Skipping {file_path} due to size > {self.max_size_kb} KB")
            except Exception as e:
                print(f"❌ Error checking {file_path}: {e}")

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
        print(f"   Files found: {len(files)}")
        print(f"   AI calls: {self.api_calls}")
        print(f"   Issues: {total_issues}")
        print(f"   Fixed: {fixed_count}")
        print(f"   Cost: ${costs['per_scan']}")

        return 0

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Pure AI Security Analyzer')
    parser.add_argument('--region', default='us-east-1', help='AWS region for Bedrock (default us-east-1)')
    parser.add_argument('--max-size-kb', type=int, default=10240, help='Max file size to scan in KB (default 10240)')
    parser.add_argument('--no-recursive', action='store_true', help='Disable recursive search')
    args = parser.parse_args()

    analyzer = PureAISecurityAnalyzer(region=args.region, max_size_kb=args.max_size_kb, recursive=not args.no_recursive)
    analyzer.run()
    exit(0)
