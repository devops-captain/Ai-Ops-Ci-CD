FROM ubuntu:18.04
FROM node:14-alpine
FROM nginx:1.14

RUN apt-get update && apt-get install -y \
    curl \
    wget \
    git

COPY . /app
WORKDIR /app

EXPOSE 3000
CMD ["npm", "start"]
