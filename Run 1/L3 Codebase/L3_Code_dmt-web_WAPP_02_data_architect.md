# Data Architect Report — dmt-web_WAPP

## Data Stores
| Store | Type | Version | Port | Purpose |
|---|---|---|---|---|
| MongoDB | Document DB | `latest` (docker-compose.yml:30) | 27017 (internal), 27020 (external dev) | Primary application data store |
| In-memory dict (`jwt_token_blocklist`) | Python dict | — | — | JWT token revocation list — volatile |

## Schema

### Collection: `dmt-web` (alias `prod` — `__init__.py:18`)

**Document: `User`** — `app/app/user/model.py:4`
| Field | Type | Constraints | Sensitivity |
|---|---|---|---|
| `_id` | ObjectId (auto) | Primary key | Low |
| `email` | EmailField | required, unique | PII — personal data |
| `pw` | StringField | required, min_length=6, bcrypt hash | Credential |
| `fullname` | StringField | optional, max_length=25 | PII |

**Note**: `app/app/field/model.py` is an identical copy of the User model — `Field` entity is a placeholder, not a real schema.

## Sensitive Data Locations
| File | Line | Sensitivity | Detail |
|---|---|---|---|
| `.env_app` | 4 | Secret | `SECRET_KEY` — Flask session secret; plaintext in repo |
| `.env_app` | 6–7 | Credential | `DB_USER` and `DB_PASS` for MongoDB application user; plaintext in repo |
| `.env_db` | 1–2 | Credential | MongoDB root username and password; plaintext in repo |
| `mongo/mongo_user_init.sh` | 3–10 | Credential | Hardcoded app-user name and password for MongoDB `dmt-web` DB; note says this file is commented out of compose |
| `app/app/config/development.py` | 20–23 | Credential | MongoDB username/password hardcoded in Python source (same values as `.env_db`) |
| `app/app/config/production.py` | 50 | Secret | `JWT_SECRET_KEY` hardcoded as literal string |
| `app/app/config/development.py` | 51 | Secret | `JWT_SECRET_KEY` same hardcoded literal string |

**All credential values redacted here per Onbe data handling policy. Existence and file locations only are noted above.**

## Encryption
| Layer | Status | Detail |
|---|---|---|
| Passwords at rest | Implemented | bcrypt via `flask_bcrypt.generate_password_hash()` — `user/model.py:10` |
| JWT payload (roles) | Implemented | Per-process ephemeral Fernet symmetric key — `__init__.py:57`, `user/service.py:90` |
| JWT transport | Partial | httponly cookies with `JWT_COOKIE_SECURE = True` in production (`production.py:32`); `False` in dev (`development.py:33`) |
| MongoDB at rest | Not configured | No `--enableEncryption` or TLS settings in `docker-compose.yml` |
| MongoDB in transit | Not configured | No TLS/SSL options set for MongoDB client or server |
| Flask-to-MongoDB connection | Plaintext | Connection string in dev config uses `host: 'database:27017'` with no TLS |

## Data Flow
```
Browser (Vue.js)
  │  HTTPS (production) / HTTP (dev) via NGINX:80
  ▼
NGINX (nginx/sites-enabled/flask_project)
  │  Proxy to http://web:5000
  ▼
Flask App (port 5000)
  │  MongoEngine ORM
  ▼
MongoDB (port 27017 internal / 27020 external)
  └─ dmt-web database
       └─ users collection
```

## Data Quality
- Email uniqueness enforced at DB level via MongoEngine `unique=True` (`user/model.py:5`).
- No data validation beyond MongoEngine field constraints visible.
- No ETL, migration scripts, or seed data management.
- `mongo/mongo_user_init.sh` exists but is **commented out** of `docker-compose.yml` (line 3 of the script itself says `#- ./mongo:/...`).

## Compliance Gaps
| Gap | Standard | Recommendation |
|---|---|---|
| Credentials and secrets committed to Git in `.env_app`, `.env_db`, config files | PCI DSS Req 3, SOC 2 | Remove secrets from source control immediately; use a secrets manager (AWS Secrets Manager, Vault) |
| JWT blocklist is in-memory — data lost on restart | GLBA / SOC 2 CC6 | Move blocklist to Redis (already in Pipfile) or MongoDB |
| No MongoDB encryption at rest or in transit | PCI DSS Req 3.5, Req 4 | Enable TLS for MongoDB; enable WiredTiger encryption at rest |
| User email stored without explicit retention/deletion policy | GDPR Art. 17, CCPA | Implement data subject deletion endpoint |
| `to_dict()` method exposes `pw` hash in user/model.py:16–20 | PCI DSS / Best Practice | Remove `pw` from `to_dict()` return; the `__init__.py:82` deletes it before JWT encoding but the method itself is a latent risk |
| `mongo:latest` Docker image tag | SOC 2 CC7 | Pin to a specific version for reproducible and auditable builds |
