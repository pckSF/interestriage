FROM mcr.microsoft.com/devcontainers/base:ubuntu-24.04

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        curl \
        ffmpeg \
        git \
        jq \
        nodejs \
        npm \
        postgresql-client \
        python3 \
        python3-dev \
        python3-pip \
        python3-venv \
        redis-tools \
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g pnpm

WORKDIR /workspace
