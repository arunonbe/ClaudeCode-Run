# DevOps / Operations Analysis — issuing-classic-selfservice_WAPP

## 1. Technology Stack

| Component | Version / Details |
|---|---|
| Language | Python 3.x |
| Framework | Django 2.1.11 (`requirements.txt` line 2) |
| Database driver | `django-pyodbc-azure==2.1.0.0` + `pyodbc==4.0.27` — ODBC to SQL Server |
| WSGI server | `portal/wsgi.py` (Django default WSGI) |
| Auth hardening | `django-axes==5.0.12` (brute-force lockout) |
| Logging | `python-json-logger==0.1.11` (JSON structured logs) |
| Testing | `coverage==4.5.4`, `factory-boy==2.12.0`, `Faker==2.0.1` |
| Data analysis | `numpy==1.17.1`, `pandas==0.25.1`, `pygal==2.4.0` (charts) |
| Form tooling | `django-crispy-forms==1.7.2`, `django-formtools==2.1`, `django-widget-tweaks==1.4.5` |

## 2. CI/CD Pipeline

### GitHub Actions
File: `.github/workflows/codeql.yml`

```yaml
name: "CodeQL"
on:
  workflow_dispatch:
  schedule:
    - cron: 8 2 * * 6   # Weekly Saturday 02:08 UTC
jobs:
  analyze:
    uses: Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main
    secrets: inherit
    with:
      java-runner: "['self-hosted', 'X64', 'Linux', 'ubuntu-docker']"
```

**Observations**: Only CodeQL SAST scanning is configured. There is no build, test, or deployment pipeline in GitHub Actions for this repo. The CodeQL workflow reuses the shared Onbe CI template (`om-ci-setup`) on a self-hosted runner.

### Build Process
- No `Jenkinsfile`, no `Dockerfile`, no `docker-compose.yml` found in the repository.
- Build and deployment are likely handled manually or via a separate deployment mechanism not captured in this repository.
- `requirements.txt` specifies all Python dependencies with pinned versions (good for reproducibility, but **Django 2.1.11 is end-of-life** — no longer receives security patches).

## 3. Configuration Management

`portal/settings.py` shows a two-path configuration:

**Production** (lines 42–48):
```python
if DEBUG is False:
    with open('/etc/config.json') as config_file:
        config = json.load(config_file)
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True
```
Configuration is loaded from `/etc/config.json` — an externally injected secrets file. CSRF and session cookies are secured in production only.

**Local/Development** (lines 52–53):
```python
else:
    from .local_settings import config
```
`local_settings.py` contains secrets (database passwords, secret key) and is **not committed to git** (correctly excluded via `.gitignore`).

**Critical Finding**: `portal/settings.py` line 27 shows `DEBUG = True` hardcoded. The comment on line 50 says:
```
# %%%% <DEV OPS NOTIFICATION>: DELETE THE FOLLOWING LINES DURING PRODUCTION DEPLOYMENT %%%% #
```
This is a manual, error-prone production deployment step. If `DEBUG = True` is accidentally left in production, Django will expose full stack traces including database credentials to any user who triggers a 500 error.

**Recommendation**: Replace the manual DEBUG flag with environment variable: `DEBUG = os.environ.get('DJANGO_DEBUG', 'False') == 'True'`.

## 4. Deployment Architecture

Based on `portal/wsgi.py` (`WSGI_APPLICATION = 'portal.wsgi.application'`), the application is deployed as a WSGI application. The likely deployment target is:
- IIS on Windows (ODBC driver for SQL Server is `django-pyodbc-azure`) or
- Apache/Nginx + gunicorn/uWSGI on Linux.

`TIME_ZONE = 'America/New_York'` (settings.py line 239) confirms Eastern Time deployment context, consistent with Eastern US data centers referenced in other repos.

## 5. Logging Configuration

`portal/settings.py` (lines 262–300) configures JSON structured logging via `python-json-logger`:

- **`normal-activity`** handler: `INFO` level, `RotatingFileHandler`, JSON format. Log path from config.
- **`errors-only`** handler: `ERROR` level, `RotatingFileHandler`, JSON format. Error log path from config.
- Root logger captures all `INFO` and above.

**Observation**: No SIEM integration (e.g., Splunk, Elasticsearch) is configured in code. Logs go to rotating files — forwarding to a centralized platform is assumed to occur at the infrastructure level.

## 6. Security Middleware

Middleware stack (`settings.py` lines 114–130):
- `django.middleware.security.SecurityMiddleware` — HTTP security headers
- `django.middleware.csrf.CsrfViewMiddleware` — CSRF token enforcement
- `django.middleware.clickjacking.XFrameOptionsMiddleware` — X-Frame-Options
- `axes.middleware.AxesMiddleware` — last in stack for login lockout

**Missing**: No rate limiting beyond django-axes login attempts. No Content Security Policy (CSP) header configuration visible. No HTTPS enforcement middleware (`SecurityMiddleware` HSTS settings not configured in code).

## 7. Dependency Vulnerabilities (Known Risks)

| Package | Version | Status |
|---|---|---|
| Django | 2.1.11 | **EOL — no security patches since April 2021** |
| numpy | 1.17.1 | Old — multiple CVEs in 1.x series |
| urllib3 | 1.25.3 | Old — CVE-2023-45803, CVE-2023-43804 present in older versions |
| django-axes | 5.0.12 | Check for updates |

**Recommendation**: Upgrade Django to 4.2 LTS minimum (4.2 receives security support until April 2026) or Django 5.x. The entire `requirements.txt` should be reviewed and upgraded.

## 8. Test Coverage

Tests are present for most modules:
- `issue_checks/tests/` — test_forms, test_models, test_urls, test_views, test_views_tools
- `block_global_deposit/tests/` — same pattern
- `void_card_inventory/tests/` — same pattern
- `trace_ip/tests/` — same pattern
- `change_usernames/tests/` — same pattern

`coverage==4.5.4` is installed, implying code coverage reporting is used. SQLite is used as the test database engine (settings.py line 80) to avoid SQL Server dependency during testing.
