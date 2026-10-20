# Security Policy and Threat Model

## Supported Versions

| Version | Supported |
| ------- | --------- |
| 0.1.x   | Yes       |

## Architecture Threat Model

This system is designed as a local-first SIEM. It assumes the host device
(Termux on Android) is trusted. Below is the threat model per component.

### 1. Agent (Termux -> Backend)

- Threat: Spoofed agent sending fake data.
- Mitigation: Agents pass an X-Agent-Id header. For production deployment,
  upgrade to mutual TLS or per-agent JWT.
- Threat: Network sniffing.
- Mitigation: The system currently runs on localhost. For remote deployment,
  wrap the WebSocket in TLS (wss://) with a proper certificate.

### 2. Backend (Starlette -> PostgreSQL)

- Threat: SQL Injection.
- Mitigation: All queries use pg8000 parameter binding. No string
  concatenation in SQL statements.
- Threat: Denial of Service (event flooding).
- Mitigation: Redis buffering, PostgreSQL connection-per-request isolation.
  Future work includes per-agent rate limiting.
- Threat: Secret leakage.
- Mitigation: gitleaks runs on every push. Environment variables are not
  committed; .env is gitignored.

### 3. Dashboard (React)

- Threat: XSS via malicious event payloads.
- Mitigation: React auto-escapes rendered values. Event payloads are parsed
  as JSON and rendered as text nodes only. No dangerouslySetInnerHTML usage.
- Threat: CORS abuse.
- Mitigation: CORS is restricted to the dashboard origin only.

## Reporting a Vulnerability

Please report security vulnerabilities via GitHub Security Advisories
or by opening a private issue at the repository owner.
