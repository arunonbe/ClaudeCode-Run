# DevOps & Operations Report — dmt-web_WAPP

## Build
| Component | Build Method | File |
|---|---|---|
| Flask (Python) API | `docker build ./app` (Dockerfile) | `app/Dockerfile` |
| Vue.js UI | Multi-stage Docker build via Vue CLI (`vue-cli-service build`) | `ui/` — built into `app/app/static` per `ui/vue.config.js:22` |
| NGINX | `docker build ./nginx` | `nginx/Dockerfile` |

### Flask Dockerfile (`app/Dockerfile`)
- Base: `python:3.9-slim`
- Only installs `pip` and `pipenv` — **no `COPY`, no `RUN pipenv install`, no `CMD`** are present (lines 1–8 are the entire file)
- This is an **incomplete Dockerfile**; the entrypoint is handled by the volume-mounted `entrypoint.sh`

### NGINX Dockerfile (`nginx/Dockerfile`)
- Base: `tutum/nginx` — this is an **unmaintained, EOL image** (tutum.co was shut down in 2018)
- Replaces default site config with `sites-enabled/flask_project`

### Entrypoint (`app/entrypoint.sh`)
```bash
cd /app
pipenv install       # installs from Pipfile at runtime
export FLASK_ENV=development   # hardcoded development mode
mkdir -p instance && touch instance/config.py
pipenv run flask run --host=0.0.0.0
```
- **FLASK_ENV is hardcoded as `development` in the entrypoint** — this means the production container still runs in development mode.
- `flask run` is used (development server, not Gunicorn/uWSGI) — **not production-grade**.

## Deploy
- **Local/dev only**: `docker-compose up -d` from repo root.
- No Kubernetes manifests, Helm charts, ECS task definitions, or Ansible playbooks present.
- No staging or production deployment pipeline.
- GitHub Actions workflow exists only for CodeQL security scanning (`.github/workflows/codeql.yml`).

### docker-compose.yml Summary
| Service | Image | Ports | Env File |
|---|---|---|---|
| `web` | Built from `./app` | 5000:5000 | `.env_app` |
| `nginx` | Built from `./nginx` | 80:80 | — |
| `database` | `mongo:latest` | 27020:27017 | `.env_db` |

- Volume mount `./app:/app` means local code changes reflect immediately — **appropriate for dev, not for production**.
- MongoDB port 27020 is exposed to host — **direct DB access possible from host network in dev**.

## Configuration
| Variable | Source | Notes |
|---|---|---|
| `DEBUG`, `SECRET_KEY`, `DB_*` | `.env_app` | Committed to Git with placeholder values — must be overridden in production |
| `MONGO_INITDB_ROOT_*` | `.env_db` | Committed to Git — credential values present |
| `JWT_SECRET_KEY` | `config/production.py:50` | Hardcoded literal in source code |
| `FLASK_ENV` | `entrypoint.sh:4` | Hardcoded `development` |
| MongoDB dev credentials | `config/development.py:20–23` | Hardcoded in Python source |

- An `instance/config.py` file is created empty at startup (`entrypoint.sh:6`) — intended as the protected server-side override path (`__init__.py:37`) but is always empty in the Docker setup.

## Observability
| Aspect | Status | Notes |
|---|---|---|
| Application Logging | Partial | Python `logging` module used in `UserService` methods (user/service.py:16, 22, 25, 45, 50, etc.) — level INFO |
| Log Aggregation | None | No log shipper, no Logstash/Beats config, no CloudWatch/Datadog integration |
| Health Checks | None | No `/health` or `/status` endpoint defined |
| Metrics | None | No Prometheus, StatsD, or APM agent |
| Distributed Tracing | None | No OpenTelemetry or similar |
| Alerts | None | No alerting configuration |

## Infrastructure
- **All local Docker Compose** — no cloud-native infrastructure defined.
- Python 3.9 (Pipfile `[requires]`) — EOL as of October 2025; must be upgraded.
- `vue@2.x` and `vuetify@2.x` — Vue 2 reached EOL December 31, 2023.
- `flask-script` dependency in `manage.py:3` — this package is deprecated and unsupported (Flask-Script was archived in 2020).

## Risks
| Risk | Severity | Notes |
|---|---|---|
| Flask dev server in production | Critical | `flask run` in entrypoint.sh — not thread-safe, not production-ready |
| Python 3.9 EOL | High | No security patches as of Oct 2025 |
| `tutum/nginx` EOL base image | High | Unmaintained base; known CVEs likely |
| `mongo:latest` unpinned | High | Breaks reproducible builds; upgrade may break app |
| Secrets in Git | Critical | `.env_app`, `.env_db`, config files contain credentials |
| No production deployment process | High | No mechanism to deploy to non-local environment |
| Vue 2 / Vuetify 2 EOL | Medium | No security updates for frontend framework |
| `flask-script` deprecated | Medium | Should be replaced with Flask CLI (`@app.cli.command`) |

## CI/CD
- **GitHub Actions**: Only `.github/workflows/codeql.yml` — scheduled weekly CodeQL scan (Fridays at 06:33 UTC).
- CodeQL uses shared `Onbe/om-ci-setup` workflow with `self-hosted` Linux runners.
- **No build, test, or deploy pipeline** beyond CodeQL.
- `pytest` and `coverage` are in Pipfile — tests exist but are not run in any automated pipeline.
