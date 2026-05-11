# Solution Architect Report — dmt-web_WAPP

## Architecture Overview
```
┌─────────────────────────────────────────────────────────┐
│  Browser                                                 │
│  Vue.js 2 SPA (App.vue, AppLogin.vue, AppRegister.vue)  │
│  Axios HTTP client                                       │
└────────────────┬────────────────────────────────────────┘
                 │ HTTP :80
┌────────────────▼────────────────────────────────────────┐
│  NGINX (tutum/nginx base)                                │
│  nginx/sites-enabled/flask_project                       │
│  Proxy: / → http://web:5000                             │
│  Static: /static → /usr/src/app/static                  │
└────────────────┬────────────────────────────────────────┘
                 │ HTTP :5000
┌────────────────▼────────────────────────────────────────┐
│  Flask 3.x + Flask-RestX (python:3.9-slim)              │
│  app/app/__init__.py  create_app()                       │
│  ├─ /api/user/*   (User namespace — ACTIVE)             │
│  └─ /api/field/*  (Field namespace — STUB/COMMENTED)    │
└────────────────┬────────────────────────────────────────┘
                 │ MongoEngine / PyMongo
┌────────────────▼────────────────────────────────────────┐
│  MongoDB (mongo:latest)                                  │
│  Database: dmt-web  Collection: user                     │
│  Port: 27017 (internal) / 27020 (dev external)          │
└─────────────────────────────────────────────────────────┘
```

## API Inventory
All endpoints are under the Flask-RestX API mounted at `/` with doc at `/docs`.

### User Namespace — `/api/user/` (ACTIVE)
| Method | Path | Class | File:Line | Auth Required |
|---|---|---|---|---|
| POST | `/api/user/register` | `UserRegister` | user/controller.py:24 | No |
| POST | `/api/user/login` | `UserLogin` | user/controller.py:33 | No |
| POST | `/api/user/refresh` | `UserRefresh` | user/controller.py:41 | CSRF cookie |
| POST | `/api/user/logout` | `UserLogout` | user/controller.py:49 | CSRF cookie |
| POST | `/api/user/protected` | `UserProtectedResource` | user/controller.py:57 | JWT + CSRF |

### Field Namespace — `/api/field/` (STUB — ALL COMMENTED OUT)
| Status | File |
|---|---|
| All endpoints commented out | field/controller.py:27–68 |
| `field_schema` defined with `type`, `enum`, `title`, `description`, `default`, `examples` | field/controller.py:16–23 |
| Syntax errors present in schema definition (`optional=true` — should be `optional=True`; `fields.Array` not a valid flask-restx type) | field/controller.py:19–22 |

### Routes Not Yet Registered
- `app/app/routes.py:6` imports `routes_field` but line 13 comment shows `routes_view` is commented out; field routes ARE registered via `routes_field(api, app)` at line 12 — but the namespace itself has no active endpoints.

## Security Architecture
| Control | Status | File:Line | Notes |
|---|---|---|---|
| Password hashing | Implemented | user/model.py:9–10 | bcrypt via `flask_bcrypt` |
| JWT (httponly cookies) | Implemented | production.py:31, user/service.py:56–58 | Prevents JS access |
| JWT CSRF protection | Implemented | production.py:44 | Double-submit cookie |
| JWT blocklist (logout) | Partial | \_\_init\_\_.py:20, user/service.py:82 | In-memory only — lost on restart |
| JWT payload encryption | Implemented | \_\_init\_\_.py:57, user/service.py:90 | Ephemeral Fernet key per process |
| HTTPS enforcement | Prod only | production.py:32 | `JWT_COOKIE_SECURE=True`; dev uses False |
| CORS | Enabled globally | \_\_init\_\_.py:28 | `CORS(app)` — no origin restriction set |
| Rate limiting | Not implemented | — | No Flask-Limiter or equivalent |
| Input validation | Minimal | user/controller.py:16–19 | Flask-RestX model schema; no custom sanitisation |
| Security headers | Not configured | — | No HSTS, CSP, X-Frame-Options via Flask or NGINX |
| CodeQL SAST | Weekly automated | .github/workflows/codeql.yml | Runs on self-hosted Linux runner |

## Technical Debt Inventory
| Item | Severity | File:Line |
|---|---|---|
| Hardcoded JWT secret key in both config files | Critical | production.py:50, development.py:51 |
| Credentials committed to Git in env files and Python source | Critical | .env_app, .env_db, development.py:20–23 |
| Flask dev server (`flask run`) used in entrypoint | Critical | entrypoint.sh:7 |
| FLASK_ENV hardcoded `development` in entrypoint | Critical | entrypoint.sh:4 |
| In-memory JWT blocklist (volatile on restart) | High | \_\_init\_\_.py:20 |
| `tutum/nginx` EOL base image | High | nginx/Dockerfile:1 |
| Python 3.9 (EOL Oct 2025) | High | app/Dockerfile:1, Pipfile:25 |
| `mongo:latest` unpinned tag | High | docker-compose.yml:30 |
| Vue 2 / Vuetify 2 EOL (Dec 2023) | High | ui/package.json:12–13 |
| `flask-script` deprecated library | Medium | app/Pipfile:8, manage.py:3 |
| `field/model.py` is a copy of `user/model.py` — not a real Field schema | Medium | field/model.py:1–20 |
| `field/controller.py` has Python syntax errors in schema definition | Medium | field/controller.py:19–22 |
| CORS `CORS(app)` with no allowed-origins restriction | Medium | \_\_init\_\_.py:28 |
| `to_dict()` on User exposes password hash | Medium | user/model.py:15–20 |
| Token refresh path mismatch: dev uses `/api/user/refresh`, prod config sets `/api/user/relogin` | Medium | development.py:37, production.py:36 |
| No Gunicorn or uWSGI — single-threaded Flask server | Critical | entrypoint.sh |
| `mongo/mongo_user_init.sh` commented out of compose but contains hardcoded credentials | High | mongo/mongo_user_init.sh:3–10 |
| Axios interceptor for token refresh is commented out | Low | ui/src/App.vue:186–212 |
| `HelloWorld.vue` default Vuetify scaffold in main content area | Low | ui/src/App.vue:13 |

## Gen-3 Migration Recommendations
| Concern | Current | Recommended |
|---|---|---|
| Auth | Local bcrypt + JWT | Integrate with Onbe SSO/OIDC (Okta, Entra ID); retire local user store |
| Secret management | Hardcoded in source | AWS Secrets Manager or HashiCorp Vault; inject at runtime via env |
| Flask server | `flask run` (dev server) | Gunicorn with `--workers` and `--worker-class gevent` behind NGINX |
| JWT blocklist | In-memory dict | Redis (already in Pipfile — `app/Pipfile:16`) |
| Container orchestration | Docker Compose | Kubernetes / ECS; Helm chart for config management |
| NGINX base image | `tutum/nginx` EOL | `nginx:alpine` pinned version |
| Python runtime | 3.9 EOL | Python 3.12+ |
| Frontend framework | Vue 2 / Vuetify 2 EOL | Vue 3 / Vuetify 3 |
| Observability | None | OpenTelemetry SDK + Logstash pipeline (see docker-logstash_INFRA_CONT) |
| MongoDB | Unencrypted, latest tag | Pinned version; TLS; WiredTiger encryption; Atlas or managed MongoDB |
| Field module | Stub | Implement `Field` model, service, and controller before user-facing launch |
| CORS | Open (`CORS(app)`) | Restrict to specific frontend origin(s) |
