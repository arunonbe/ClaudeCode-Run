# Business Analyst Report — dmt-web_WAPP

## Business Purpose
`dmt-web_WAPP` is the **web-based successor to the Excel DMT application**. It provides a browser-delivered Data Management Tool with user registration, authentication, and a data field management module. The application targets internal Onbe operational users who currently use the Excel-based `dmt_WAPP`. The stated goal (README) is to replace the fat-client pattern with a containerised web stack accessible at `localhost` (dev) or a hosted URL (production).

## Capabilities
| Capability | Module | Key Classes / Files |
|---|---|---|
| User Registration | `app/app/user/` | `UserRegister` (controller.py:24), `UserService.create()` (user/service.py:15) |
| User Login / Logout | `app/app/user/` | `UserLogin` (controller.py:33), `UserLogout` (controller.py:49), `UserService.login()` (user/service.py:44), `UserService.logout()` (user/service.py:77) |
| JWT Token Refresh | `app/app/user/` | `UserRefresh` (controller.py:41), cookie-based refresh flow |
| Protected Resource Access | `app/app/user/` | `UserProtectedResource` (controller.py:57), `UserService.protected()` (user/service.py:88) |
| Field Management (stub) | `app/app/field/` | `Field` namespace defined (field/controller.py:10); all endpoints commented out — not yet active |
| Vue.js Web UI | `ui/src/` | `App.vue` (root), `AppLogin.vue`, `AppRegister.vue`, `AppBar.vue`, `HelloWorld.vue` |
| OpenAPI / Swagger Docs | Flask-RestX | Available at `/api/docs` (\_\_init\_\_.py:44) |

## Key Entities
| Entity | Model Class | File | Fields |
|---|---|---|---|
| User | `User` (MongoEngine Document) | `app/app/user/model.py:4` | `email` (unique, required), `pw` (bcrypt hash, min 6), `fullname` (optional, max 25) |
| Field | Not fully implemented | `app/app/field/model.py` | Currently a copy of User model — placeholder only |
| JWT Token Blocklist | In-memory dict | `app/app/__init__.py:20` | `{jti: 'true'}` — volatile, lost on restart |

## Business Rules
1. Email must be unique per user (`NotUniqueError` handling — user/service.py:24).
2. Password minimum length is 6 characters at the DB layer (`model.py:7`); UI enforces 12 characters (`AppLogin.vue:97`).
3. Passwords are bcrypt-hashed before storage (`model.py:9–10`).
4. JWT access tokens expire in 15 minutes; refresh tokens in 30 days (`production.py:61–62`, `development.py:52–53`).
5. On logout, the token JTI is added to an in-memory blocklist to invalidate it server-side (`user/service.py:82`).
6. CSRF protection is enabled via double-submit cookie pattern (`JWT_COOKIE_CSRF_PROTECT = True` in both configs).
7. JWT payload (user roles/details) is additionally encrypted with a per-process ephemeral Fernet key (`__init__.py:57`).

## User Flows
```
Registration:
  AppRegister.vue → POST /api/user/register → UserRegister.post() → UserService.create() → MongoDB

Login:
  AppLogin.vue → POST /api/user/login → UserLogin.post() → UserService.login()
    → bcrypt verify → create_access_token + create_refresh_token
    → httponly cookies set in browser response

Protected Action:
  App.vue isUserAuthenticated() → POST /api/user/protected → JWT + CSRF verify
    → Fernet decrypt roles from JWT → 200 OK

Logout:
  AppBar.vue → POST /api/user/logout → JWT blocklist entry → cookies cleared
```

## Compliance Relevance
- **GLBA / SOC 2**: Internal user authentication system; credential storage (bcrypt) and JWT token management are primary controls.
- **OWASP / PCI DSS Req 6**: CSRF protection implemented; XSS mitigation via httponly cookies. Several issues noted below.
- **GDPR / CCPA**: User email stored in MongoDB — constitutes personal data requiring data subject rights support.

## Risks
| Risk | Severity | Notes |
|---|---|---|
| In-memory JWT blocklist lost on restart | High | All logged-out tokens become valid again after app restart (\_\_init\_\_.py:20) |
| Hardcoded JWT secret key in source code | Critical | `JWT_SECRET_KEY = 'ThisIsTheSecretKeyUsedToSaltJWT'` in both production.py:50 and development.py:51 |
| Default credentials in `.env_app` | High | `SECRET_KEY=supersecretkey`, `DB_PASS=mongo-pass` committed to repo |
| MongoDB root credentials in `.env_db` | High | Root username/password present in committed file (existence noted; values redacted here) |
| Field module is a stub | Medium | `field/controller.py` endpoints all commented out; `field/model.py` is a copy of User model — not functional |
| No rate limiting on auth endpoints | High | `/api/user/login` and `/api/user/register` have no brute-force protection |
| Self-registration is open | Medium | Any person who can reach the endpoint can register — no invite/approval flow |
| Password minimum 6 chars at API vs 12 at UI | Medium | API accepts 6-char passwords; UI enforces 12 — inconsistency creates API-bypass risk |
