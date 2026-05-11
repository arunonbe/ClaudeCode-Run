# DevOps & Operations Report — docker-logstash_INFRA_CONT

## Build
### Dockerfile (`Dockerfile`)
- **Base image**: `logstash:7.9.3` — Logstash 7.9.3, released September 2020. **This version is End-of-Life** (Elastic's 7.x support ended February 2025).
- **Build steps**:
  1. `mkdir -p ${HOME}/pki` — creates PKI directory
  2. `COPY pki/* pki/` — copies CA cert, server cert, and **server private key** into image
  3. `COPY *.conf config/` — copies both pipeline configs into image
  4. Installs `logstash-output-amazon_es` plugin
  5. Removes sample config; sets `http.host: "0.0.0.0"` in `logstash.yml`
  6. Sets ownership to `logstash` user; runs as non-root `logstash` user

### Build Output
- Docker image tagged as `{ECR_BASENAME_UTIL}/{CI_PROJECT_NAME}:{YYYYMMDD}-{SHORT_SHA}` and `:latest`
- Image pushed to AWS ECR utility repository

### Key Build Concerns
- Private key (`pki/server.key`) is `COPY`-ed into the image layer — it cannot be removed post-build without rebuilding; it is baked into every pulled image.
- `logstash-output-amazon_es` plugin installed at build time — correct for ChaosSearch/ES output, but ChaosSearch output is currently commented out.

## CI/CD Pipeline (`.gitlab-ci.yml`)
| Stage | Details |
|---|---|
| Image | `wcareplogle/cloud-deploy:latest` — custom deploy image from Docker Hub (unverified/personal account) |
| Service | `docker:19.03.12-dind` — Docker-in-Docker for building |
| Trigger | Every commit (no branch filters, no manual gate) |
| Build step | `git show` to derive date-based tag; `docker build`; `docker tag :latest`; `aws ecr get-login-password`; `docker push` |
| AWS Auth | `AWS_ACCESS_KEY_ID: ${ECR_AWS_ACCESS_KEY_ID}`, `AWS_SECRET_ACCESS_KEY: ${ECR_AWS_SECRET_ACCESS_KEY}` — injected from GitLab CI/CD variables |
| Docker host | `tcp://docker:2375` — **unencrypted Docker daemon** (TLS commented out in the config) |

### CI/CD Concerns
| Concern | Severity |
|---|---|
| `wcareplogle/cloud-deploy:latest` — unverified personal Docker Hub image used as pipeline runner | High |
| `docker:19.03.12-dind` — specific but old Docker version (2020); dind with unencrypted daemon | High |
| `tcp://docker:2375` — unencrypted Docker socket (TLS disabled via comment) | High |
| No pipeline stages for test, security scan, or smoke test | Medium |
| `:latest` tag pushed alongside date/SHA tag — leads to non-deterministic pulls | Medium |
| No branch filter — pipeline runs on all branches/tags | Low |

## Configuration
All runtime configuration is injected via environment variables. None are defined in the repository:

| Variable | Used In | Purpose |
|---|---|---|
| `INPUT_BEATS_PORT` | ingest-beats.conf:3 | Beats input port (default: 5044) |
| `OUTPUT_SQS_QUEUE` | ingest-beats.conf:14 | SQS queue name for output |
| `OUTPUT_SQS_REGION` | ingest-beats.conf:15 | AWS region for SQS |
| `OUTPUT_SQS_CODEC` | ingest-beats.conf:16 | Logstash codec for SQS messages |
| `INPUT_SQS_QUEUE` | ship-chaos.conf:3 | SQS queue name for input |
| `INPUT_SQS_REGION` | ship-chaos.conf:4 | AWS region for SQS input |
| `CHAOSSEARCH_S3_REGION` | ship-chaos.conf:21 | AWS region for S3 bucket |
| `CHAOSSEARCH_S3_BUCKET` | ship-chaos.conf:22 | S3 bucket name |
| `CHAOSSEARCH_S3_SIZE` | ship-chaos.conf:23 | Max file size before rotation |
| `CHAOSSEARCH_S3_TIME` | ship-chaos.conf:24 | Max time before file rotation |
| `ECR_AWS_ACCESS_KEY_ID` | .gitlab-ci.yml:19 | AWS key for ECR push (CI variable) |
| `ECR_AWS_SECRET_ACCESS_KEY` | .gitlab-ci.yml:20 | AWS secret for ECR push (CI variable) |
| `ECR_BASENAME_UTIL` | .gitlab-ci.yml:33–36 | ECR registry base URL |

**No `.env` file, no Kubernetes ConfigMap, no ECS task definition visible** — runtime environment injection mechanism is not defined in this repository.

## Observability
| Aspect | Status | Notes |
|---|---|---|
| Logstash HTTP API | Enabled | `http.host: "0.0.0.0"` in logstash.yml (Dockerfile:12) — Logstash monitoring API on port 9600 |
| Pipeline metrics | Available | Logstash exposes node stats at `/_node/stats` via HTTP API |
| X-Pack monitoring | Not configured | No `xpack.monitoring` settings in logstash.yml |
| Log aggregation | This IS the log aggregator | Meta-monitoring of Logstash itself not configured |
| Alerts | None in repo | No CloudWatch alarms, PagerDuty, or similar |
| Dead letter queue | Not configured | No `dead_letter_queue` plugin in pipeline configs |

## Infrastructure
- **Container runtime**: Docker (version not specified for production)
- **Image registry**: AWS ECR (`${ECR_BASENAME_UTIL}` utility repository)
- **Cloud**: AWS (SQS, S3, ECR, KMS)
- **Logstash version**: 7.9.3 (EOL)
- **Plugin**: `logstash-output-amazon_es` (for ChaosSearch/ES output)
- **PKI**: Self-managed; `pki/ca.crt`, `pki/server.crt`, `pki/server.key` baked into image

## Operational Risks
| Risk | Severity | Notes |
|---|---|---|
| Logstash 7.9.3 EOL (Elastic 7.x EOL Feb 2025) | High | No security patches; CVEs unaddressed |
| Private key baked into Docker image | Critical | Every ECR pull exposes the key; rotate immediately |
| Unencrypted Docker daemon in CI (`tcp://docker:2375`) | High | Man-in-the-middle risk during build |
| `wcareplogle/cloud-deploy:latest` unverified CI image | High | Supply chain risk — arbitrary code execution in pipeline |
| No restart policy or health check defined | Medium | Container failure results in silent log loss |
| No dead letter queue | Medium | Pipeline failures drop logs silently |
| Single pipeline config per function — no HA | Medium | No horizontal scaling or failover configured |
