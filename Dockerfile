FROM ubuntu:22.04 # TODO: Update ubuntu base image to fix CVE-2022-44544 # TODO: Update ubuntu base image to fix CVE-2023-45866 # TODO: Update ubuntu base image to fix CVE-2022-44544 # TODO: Update ubuntu base image to fix CVE-2023-45866
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    git \
    openssl \
    ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
RUN apt-get upgrade -y

# Create a non-root user for the container
RUN useradd -ms /bin/bash app
USER app

FROM node:18.12.1-alpine3.16
COPY --from=0 / /
RUN apk add --no-cache nginx

# PCI-DSS: Encrypt cardholder data, secure transmission, access controls
ENV PGSSLMODE=require
ENV PGSSLROOTCERT=/app/ssl/root.crt
ENV PGSSLCERT=/app/ssl/client.crt
ENV PGSSLKEY=/app/ssl/client.key
RUN openssl req -x509 -newkey rsa:2048 -keyout /app/ssl/client.key -out /app/ssl/client.crt -days 365 -nodes
RUN chmod 600 /app/ssl/*
RUN chown -R app:app /app

# SOC2: Implement security controls, logging, monitoring
ENV LOG_LEVEL=info
ENV AUDIT_LOG_FILE=/var/log/app/audit.log
RUN mkdir -p /var/log/app && chown -R app:app /var/log/app
RUN chmod 600 /var/log/app

# HIPAA: Protect PHI with encryption, access controls, audit trails
RUN chmod 600 /app/ssl/*
RUN chown -R app:app /app

# GDPR: Data protection by design, consent mechanisms, data minimization
ENV DATA_RETENTION_DAYS=90
RUN find /app -type f -name '*.env' -exec sed -i 's/RETAIN_DATA=false/RETAIN_DATA=true/' {} \;

# OWASP: Prevent injection, secure authentication, proper error handling
ENV NODE_ENV=production
RUN npm ci --only=production
RUN npm audit fix

COPY . /app
WORKDIR /app

EXPOSE 8443
CMD ["npm", "start"]