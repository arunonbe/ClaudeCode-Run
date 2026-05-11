# DevOps & Operations Analysis — EstimationChatApp-_MISC

## Repository Overview

**Repo:** `EstimationChatApp-_MISC`
**Runtime:** Node.js (no version pinned in `package.json`)
**Docker base image:** `node:15.3.0-alpine3.10` (`Dockerfile` line 1)
**CI:** GitHub Actions — CodeQL only (`.github/workflows/codeql.yml`)
**Process manager:** None (bare `node ./main.js`)

---

## Build and Package

### Dependencies (`package.json`)
| Package | Version | Purpose |
|---------|---------|---------|
| `express` | `^4.17.1` | HTTP server framework |
| `socket.io` | `^3.0.3` | WebSocket / real-time messaging |
| `dotenv` | `^8.2.0` | Environment variable loading from `.env` |
| `consolidate` | `^0.16.0` | Template engine consolidation (unused in current views) |
| `mustache` | `^4.0.1` | Template engine (not visibly used; HTML files served as static) |
| `http-msgs` | `^1.0.9` | HTTP message helpers (used only for `send500` on failed login) |

**Dev dependencies:**
| Package | Version | Purpose |
|---------|---------|---------|
| `nodemon` | `^2.0.6` | Auto-restart on file change (dev only) |

**No test framework** — `package.json` line 8: `"test": "echo \"Error: no test specified\" && exit 1"`.

### Runtime Startup
```bash
node ./main.js
```
Server listens on port 3000 (`main.js` line 148: `http.listen(3000, ...)`). No port parameterisation — the port is hardcoded.

---

## Docker

### Dockerfile
```dockerfile
FROM node:15.3.0-alpine3.10
WORKDIR /app
COPY . .
CMD ["node", "./main.js"]
```

**Issues:**
1. **No `npm install`** — the Dockerfile copies the source but does not run `npm install`. The container will fail to start because `node_modules` is absent unless `node_modules` is included in the COPY (i.e., committed to the repo or not in `.dockerignore`). There is no `.dockerignore` file in this repo.
2. **Node 15.3.0** — Node 15 was EOL as of June 2021. Current LTS is Node 20/22.
3. **No non-root user** — the container runs as `root`, violating container security best practices and PCI DSS Req 7.2.
4. **`.env` file included in COPY** — the `.env` file with team credentials will be baked into the Docker image.
5. **No health check** — no `HEALTHCHECK` instruction.
6. **No `EXPOSE` instruction** — port 3000 is not declared.

### Corrected Dockerfile (recommended)
```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --omit=dev
COPY . .
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
USER appuser
EXPOSE 3000
HEALTHCHECK --interval=30s CMD wget -qO- http://localhost:3000/ || exit 1
CMD ["node", "./main.js"]
```

---

## CI/CD

### GitHub Actions — CodeQL
`.github/workflows/codeql.yml` is present (from `.github/` directory listing). Runs static security analysis on JavaScript. This is the same shared Onbe CodeQL workflow referenced in `enrollment_LIB`.

**No build or deployment pipeline** — no pipeline stages for install, lint, test, build, or deploy.

### `.gitlab-ci.yml`
A GitLab CI file is present in the root. Contents not fully read, but given the `_MISC` classification and the absence of a Kubernetes/production deployment target, this likely has minimal stages.

---

## Operational Considerations

### Availability
- Single Node.js process listening on port 3000.
- No process manager (PM2, systemd, Kubernetes) — if the process crashes, it does not restart.
- No cluster mode — single CPU core utilised regardless of host capacity.

### Monitoring
- No application performance monitoring.
- No structured logging — `console.log()` only (`main.js` lines 32, 101, 103, 140, 143).
- No health endpoint.

### Security Hardening Gaps
| Gap | Detail |
|-----|--------|
| HTTP only | No TLS; all traffic including login credentials in cleartext |
| No rate limiting | Login endpoint `/loginVerify` has no rate limiting; brute-force of 5 team codes takes at most 5 requests |
| Port 3000 hardcoded | Cannot change port without modifying source code |
| `.env` in repo | Team credentials included in Git history |
| No input sanitisation | `tname` and `code` from `req.body` used without sanitisation |
| CORS | Not configured — accepts connections from any origin (Socket.IO default) |

---

## Conclusion

`EstimationChatApp-_MISC` is a **developer sandbox tool** with no production-grade operational infrastructure. The Docker image is broken as-written (missing `npm install`). There is no deployment pipeline, no monitoring, and no process management. Given its `_MISC` classification, the expectation is that it runs locally on a developer's machine or at most on an internal development server. It should not be deployed to any internet-facing or production environment without significant hardening.

**Operational Recommendation:** If the tool is to be used regularly, run it as a Docker container via `docker-compose` on an internal development server behind the corporate VPN, not exposed to the public internet.
