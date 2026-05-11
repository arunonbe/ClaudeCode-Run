# Enterprise Architect Report — dmt-web_WAPP

## Platform Generation
**Generation 2 (Transitional Web)** — A containerised, multi-tier web application replacing the Gen-1 Excel DMT. The stack (Flask + MongoDB + Vue.js + NGINX + Docker Compose) is a standard Gen-2 pattern. It has not yet reached Gen-3 maturity (no Kubernetes, no service mesh, no event-driven architecture, no API gateway, no observability stack).

## Domain
**Internal Operations / Data Management** — Web-based successor to `dmt_WAPP`. Targets the same internal Onbe user base for data field management. Not yet customer-facing. Domain bounded context: **User Identity & Access** (implemented) + **Field/Data Management** (stub only).

## Role in Enterprise Architecture
| Role | Detail |
|---|---|
| Web UI | Vue.js SPA (`ui/src/App.vue`) served via NGINX, proxied to Flask API |
| API Server | Flask-RestX providing OpenAPI-documented endpoints at `/api/*` |
| Identity Provider | Local user registration/auth (not integrated with enterprise SSO/LDAP) |
| Data Store | Standalone MongoDB — not integrated with enterprise data warehouse |
| Successor to dmt_WAPP | Direct replacement for the Excel-based DMT application |

## Dependencies
| Dependency | Type | Criticality | Notes |
|---|---|---|---|
| MongoDB | Runtime data store | Critical | No fallback; in-process data |
| NGINX | Reverse proxy / static file server | Critical | Routes all traffic |
| Flask + Flask-RestX | API framework | Critical | `flask==*`, `flask-restx==*` in Pipfile |
| Flask-JWT-Extended | Auth | Critical | JWT cookie management |
| Flask-Bcrypt | Auth | Critical | Password hashing |
| cryptography (Fernet) | Auth | High | JWT payload encryption — ephemeral key |
| MongoEngine | ORM | Critical | MongoDB object mapping |
| Redis | Listed in Pipfile | Not yet used | `redis==*` in Pipfile but no code references found — likely intended for JWT blocklist persistence |
| Vue 2 / Vuetify 2 | Frontend | High | EOL frameworks |
| Selenium | Dev dependency | Low | Listed for UI automation testing (Pipfile dev-packages) — no test code in repo |
| dmt_WAPP | Predecessor | Strategic | Excel app being replaced |
| Onbe/om-ci-setup | CI | Low | Shared GitHub Actions for CodeQL |

## Architectural Patterns
| Pattern | Implementation |
|---|---|
| MVC / layered | Python: model (`model.py`), service (`service.py`), controller (`controller.py`), interface (`interface.py`) per module |
| SPA + API | Vue.js SPA consuming Flask REST endpoints via Axios |
| Namespace routing | Flask-RestX Namespaces: `User` at `/api/user`, `Field` at `/api/field` (stub) |
| Cookie-based JWT | httponly access + refresh cookies; CSRF double-submit tokens |
| Module registration | `these_routes()` pattern in each module's `__init__.py` — clean plugin-style registration |

## Status
**Early development / proof-of-concept** — The `user` module is functionally complete with tests. The `field` module (`field/controller.py`) is entirely commented out. The `HelloWorld.vue` default component is still in the main content area, indicating the UI has not progressed beyond the authentication shell.

## Enterprise Blockers
1. **No SSO / LDAP Integration**: Users must self-register. There is no integration with Onbe's identity provider (SAML, OIDC, or LDAP). This is a significant gap for an internal enterprise tool.
2. **No Role-Based Access Control (RBAC)**: User roles are encrypted in the JWT payload (`__init__.py:77–89`) but the `Field` module that would consume them is not implemented.
3. **No Audit Trail**: No structured audit log for user actions — required for SOC 2 and GLBA.
4. **Data Isolation**: MongoDB instance is standalone; not integrated with enterprise data governance, backup, or DR processes.
5. **Field Management Not Implemented**: The core business function (data field management) is a stub — the application cannot yet replace its predecessor.
6. **No Production Hosting**: Only local Docker Compose; no production environment defined.
