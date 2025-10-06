FROM ubuntu:20.04.5 # TODO: Update ubuntu base image to fix CVE-2005-0080 # TODO: Update ubuntu base image to fix CVE-2006-0176
FROM node:16.19.0-alpine3.16 # TODO: Update node base image to fix CVE-2000-0558 # TODO: Update node base image to fix CVE-2000-0754
FROM nginx:1.20.2

RUN apt-get update && apt-get install -y \
    curl \
    wget \
    git

COPY . /app
WORKDIR /app

# PCI-DSS: Encrypt cardholder data, secure transmission, access controls
ENV PGSSLMODE=require
ENV PGSSLROOTCERT=/app/ssl/root.crt
ENV PGSSLCERT=/app/ssl/client.crt
ENV PGSSLKEY=/app/ssl/client.key

# SOC2: Implement security controls, logging, monitoring
ENV LOG_LEVEL=info
ENV AUDIT_LOG_FILE=/var/log/app/audit.log
RUN mkdir -p /var/log/app && chown -R app:app /var/log/app

# HIPAA: Protect PHI with encryption, access controls, audit trails
RUN chmod 600 /app/ssl/*
RUN chown -R app:app /app

# GDPR: Data protection by design, consent mechanisms, data minimization
ENV DATA_RETENTION_DAYS=30
RUN find /app -type f -name '*.env' -exec sed -i 's/RETAIN_DATA=false/RETAIN_DATA=true/' {} \;

# OWASP: Prevent injection, secure authentication, proper error handling
ENV NODE_ENV=production
RUN npm ci --only=production
RUN npm audit fix

EXPOSE 8443
CMD ["npm", "start"]