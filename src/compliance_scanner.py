import os
import json
import boto3
import glob
import hashlib
from datetime import datetime

class ComplianceScanner:
    def __init__(self, profile_name=None):
        # Use AWS profile for local development, OIDC for GitHub Actions
        session = boto3.Session(profile_name=profile_name)
        self.region = os.getenv('AWS_REGION', 'us-east-1')
        self.bedrock = session.client('bedrock-runtime', region_name=self.region)
        self.kb_id = os.getenv('BEDROCK_KB_ID', 'RL3YC1HUKZ')
        self.model_id = os.getenv('BEDROCK_MODEL_ID', 'anthropic.claude-3-haiku-20240307-v1:0')
        self.ai_calls = 0
        self.total_cost = 0
        
        # File hash cache
        self.cache_file = '.file_hash_cache.json'
        self.file_cache = self.load_cache()
        self.ai_calls = 0
        self.total_cost = 0
        
        # Compliance-focused prompts
        self.compliance_context = {
            'PCI-DSS': 'PCI-DSS requires encryption of cardholder data, secure transmission, access controls, and regular security testing.',
            'SOC2': 'SOC2 Type II requires security controls for confidentiality, availability, processing integrity, and privacy.',
            'HIPAA': 'HIPAA requires safeguards for PHI including encryption, access controls, audit logs, and breach notification.',
            'GDPR': 'GDPR requires data protection by design, consent management, data minimization, and breach notification.',
            'OWASP': 'OWASP Top 10 covers injection, broken authentication, sensitive data exposure, and security misconfigurations.'
        }
    
    def validate_knowledge_base(self):
        """Validate Knowledge Base is accessible and contains compliance rules"""
        try:
            # Test KB with a simple compliance query
            test_query = "security compliance standards PCI-DSS HIPAA"
            kb_response = self.query_knowledge_base(test_query)
            
            if not kb_response or len(kb_response.strip()) < 50:
                print(f"❌ KB validation failed: No meaningful response")
                return False
            
            # Check for compliance keywords
            compliance_keywords = ['PCI-DSS', 'HIPAA', 'GDPR', 'SOC2', 'OWASP', 'security', 'compliance']
            found_keywords = sum(1 for keyword in compliance_keywords if keyword.lower() in kb_response.lower())
            
            if found_keywords < 2:
                print(f"❌ KB validation failed: Insufficient compliance content")
                return False
            
            print(f"✅ KB validation passed: Found {found_keywords} compliance keywords")
            return True
            
        except Exception as e:
            print(f"❌ KB validation failed: {e}")
            return False
    
    def query_knowledge_base(self, query):
        """Query Knowledge Base for compliance context with chunking for large files"""
        try:
            # AWS Bedrock KB hard limit: 20,000 chars (cannot be increased)
            max_query_length = 18000  # Leave buffer for safety
            
            if len(query) <= max_query_length:
                # Single query for normal-sized content
                return self._single_kb_query(query)
            else:
                # Multiple queries for large files
                print(f"   📄 Large file detected ({len(query)} chars) - using chunked KB queries")
                return self._chunked_kb_query(query, max_query_length)
                
        except Exception as e:
            print(f"   ❌ KB Query failed: {e}")
            return None
    
    def _single_kb_query(self, query):
        """Single KB query for normal-sized content"""
        bedrock_agent = boto3.client('bedrock-agent-runtime', region_name=self.region)
        
        response = bedrock_agent.retrieve(
            knowledgeBaseId=self.kb_id,
            retrievalQuery={'text': query},
            retrievalConfiguration={
                'vectorSearchConfiguration': {
                    'numberOfResults': 5
                }
            }
        )
        
        context = ""
        for result in response['retrievalResults']:
            context += f"{result['content']['text']}\n\n"
        
        if context.strip():
            print(f"   📚 KB Query successful - {len(response['retrievalResults'])} sources found")
            return context.strip()
        return None
    
    def _chunked_kb_query(self, query, chunk_size):
        """Multiple KB queries for large files"""
        chunks = []
        lines = query.split('\n')
        current_chunk = ""
        
        # Split into chunks by lines to maintain context
        for line in lines:
            if len(current_chunk + line + '\n') > chunk_size:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = line + '\n'
            else:
                current_chunk += line + '\n'
        
        if current_chunk:
            chunks.append(current_chunk)
        
        print(f"   📊 Processing {len(chunks)} chunks for comprehensive KB analysis")
        
        # Query each chunk and combine results
        all_context = ""
        total_sources = 0
        
        for i, chunk in enumerate(chunks[:3]):  # Limit to 3 chunks for cost control
            chunk_context = self._single_kb_query(chunk)
            if chunk_context:
                all_context += f"--- Chunk {i+1} Context ---\n{chunk_context}\n\n"
                total_sources += 1
        
        if all_context:
            print(f"   📚 Chunked KB Query successful - {total_sources} chunks analyzed")
            return all_context.strip()
        
        return None
    
    def get_file_hash(self, filepath):
        """Generate SHA256 hash of file content"""
        try:
            with open(filepath, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception:
            return None
    
    def load_cache(self):
        """Load file hash cache from local file or S3 (for CI/CD)"""
        cache = {}
        
        # Try S3 first (for CI/CD)
        if os.getenv('GITHUB_ACTIONS') == 'true' or os.getenv('CI') == 'true':
            cache = self.load_cache_from_s3()
            if cache:
                print(f"📋 Loaded S3 cache: {len(cache)} files")
                return cache
        
        # Fallback to local cache
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    cache = json.load(f)
                    print(f"📋 Loaded local cache: {len(cache)} files")
                    return cache
        except Exception as e:
            print(f"⚠️ Local cache load failed: {e}")
        
        return {}
    
    def save_cache(self):
        """Save file hash cache to local file and S3 (for CI/CD)"""
        # Save locally
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.file_cache, f, indent=2)
        except Exception as e:
            print(f"⚠️ Local cache save failed: {e}")
        
        # Save to S3 for CI/CD persistence
        if os.getenv('GITHUB_ACTIONS') == 'true' or os.getenv('CI') == 'true':
            self.save_cache_to_s3()
    
    def load_cache_from_s3(self):
        """Load cache from S3"""
        try:
            s3_bucket = os.getenv('S3_CACHE_BUCKET', 'ai-security-scanner-cache')
            cache_key = f"cache/{os.getenv('GITHUB_REPOSITORY', 'default')}/file_hash_cache.json"
            
            s3 = boto3.client('s3', region_name=self.region)
            response = s3.get_object(Bucket=s3_bucket, Key=cache_key)
            cache_data = json.loads(response['Body'].read())
            
            # Clean old cache entries (older than 7 days)
            cutoff_date = datetime.now().timestamp() - (7 * 24 * 60 * 60)
            cleaned_cache = {}
            for filepath, data in cache_data.items():
                try:
                    cache_time = datetime.fromisoformat(data.get('timestamp', '1970-01-01')).timestamp()
                    if cache_time > cutoff_date:
                        cleaned_cache[filepath] = data
                except:
                    pass
            
            return cleaned_cache
            
        except Exception as e:
            print(f"⚠️ S3 cache load failed: {e}")
            return {}
    
    def save_cache_to_s3(self):
        """Save cache to S3"""
        try:
            s3_bucket = os.getenv('S3_CACHE_BUCKET', 'ai-security-scanner-cache')
            cache_key = f"cache/{os.getenv('GITHUB_REPOSITORY', 'default')}/file_hash_cache.json"
            
            s3 = boto3.client('s3', region_name=self.region)
            s3.put_object(
                Bucket=s3_bucket,
                Key=cache_key,
                Body=json.dumps(self.file_cache, indent=2),
                ContentType='application/json'
            )
            print(f"📋 Saved cache to S3: s3://{s3_bucket}/{cache_key}")
            
        except Exception as e:
            print(f"⚠️ S3 cache save failed: {e}")
    
    def get_cached_result(self, filepath):
        """Get cached result if file hasn't changed"""
        current_hash = self.get_file_hash(filepath)
        if not current_hash:
            return None
        
        cache_key = filepath
        if cache_key in self.file_cache:
            cached_data = self.file_cache[cache_key]
            if cached_data.get('hash') == current_hash:
                return cached_data.get('result')
        
        return None
    
    def cache_result(self, filepath, result):
        """Cache scan result with file hash"""
        file_hash = self.get_file_hash(filepath)
        if file_hash:
            self.file_cache[filepath] = {
                'hash': file_hash,
                'result': result,
                'timestamp': datetime.now().isoformat()
            }
    
    
    def call_ai_with_compliance(self, prompt):
        """AI call with MANDATORY Knowledge Base compliance context"""
        
        # ENFORCE: Knowledge Base must be available
        if not self.kb_id:
            raise Exception("❌ BLOCKED: Knowledge Base ID required. KB is the source of truth for compliance.")
        
        # Extract key terms for KB query (not the full prompt)
        kb_query = self._extract_kb_query_terms(prompt)
        
        # MANDATORY: Query Knowledge Base with summary terms
        kb_context = self.query_knowledge_base(kb_query)
        if not kb_context:
            raise Exception("❌ BLOCKED: Knowledge Base query failed. Cannot proceed without KB source of truth.")
        
        # Build prompt with KB context as only source
        compliance_prompt = f"""
You are a security expert. Use ONLY the Knowledge Base context provided below as