
# General Security Patterns

## Hardcoded Secrets
NEVER use:
- password = "plaintext"
- api_key = "hardcoded_key"

ALWAYS use:
- Environment variables
- AWS Secrets Manager
- Kubernetes secrets

## Network Security
- Use HTTPS/TLS everywhere
- Implement proper firewall rules
- Regular security audits
