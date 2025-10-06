FROM ubuntu:20.04
FROM node:16-alpine
FROM nginx:1.20

RUN apt-get update && apt-get install -y \
    curl \
    wget \
    git

COPY . /app
WORKDIR /app

EXPOSE 3000
CMD ["npm", "start"]
