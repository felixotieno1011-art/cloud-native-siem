# Deployment Guide

## 1. Laptop / Server (Docker)
The easiest way to run the full stack on a laptop is via Docker Compose.

    docker-compose up --build -d

This starts:
- PostgreSQL (port 5432)
- Redis (port 6379)
- Backend API (port 8080)
- Dashboard (port 5173)

To generate events, run the agent on your host machine and point it at localhost:

    cd agent
    python -m siem_agent --url ws://127.0.0.1:8080/ws/ingest

## 2. Termux (Android)
Please see the Quick Start section in the main README for native Termux deployment.
