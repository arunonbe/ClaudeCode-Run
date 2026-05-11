# service-tester_WAPP — Data Architect View

## Data Stores
| Store | Type | Location | Purpose |
|---|---|---|---|
| Service Tester Database | SQL Server | JNDI: `jdbc/ServiceTesterDataSource` | User registry, access/role definitions, audit log |
| User XML file | File | `users.xml` (classpath) | Optional file-based user source |

## Schema (Reconstructed from SQL Enum in JdbcUserDao.java)
| Table | Key Columns | Notes |
|---|---|---|
| `[user]` | username, name, email, defaultContext, defaultMethod, created | Primary user registry |
| `[access_all]` | username, resourceName | Maps users to service contexts |
| `[role_all]` | username, resourceName, name, expires | Role assignments with optional expiration |
| `[admin_access]` | username | Marker table for admin privilege |
| `[default_user]` | username | Single-row: the default user |
| `[log]` | updated (datetime), username, message | Audit log for user management actions |

## Sensitive Data
| Data Element | Location | Notes |
|---|---|---|
| User email addresses | `[user].email` column and `User.java` entity | PII — GDPR/CCPA applicable |
| Session IDs | HTTP session (not persisted to DB) | Standard Tomcat session management |
| Service invocation payloads | Runtime only — not persisted | Could contain PAN/card data if user submits such inputs |

## Encryption
- No field-level encryption in application code.
- Database connection via JNDI `jdbc/ServiceTesterDataSource` — TLS for JDBC depends on Tomcat context configuration.
- Passwords: container-managed authentication (Tomcat FORM auth). Application does not handle passwords directly.

## Data Flow
```
Browser (authenticated user)
  → Spring MVC DispatcherServlet
    → ServiceTestPageController / LoginFormController
      → UserFactory (CachedUserFactory → DatabaseUserFactory)
        → JdbcUserDao → SQL Server [user], [role_all], [access_all] tables

Service invocation:
Browser → ServiceTestPageController
  → Context.findMethod(methodName)
    → ServiceMethod.invoke(xmlInput)
      → Underlying Spring bean (could be any wired service)
        → Returns Object → marshalled to XML → rendered in Response JSP
```

## Data Quality / Retention
- `[log]` table uses `getdate()` for timestamp — server-side timestamp.
- Role expiry stored in `[role_all].expires` as TIMESTAMP — active governance mechanism.
- No data retention policy in application code; database-level retention policy required.
- `users.xml` provides default users with no password hash — uses container authentication only.

## Compliance Gaps
- **GDPR Art. 25**: User email addresses stored in plain text; no pseudonymisation.
- **PCI DSS Req 7**: `<role-name>*</role-name>` in web.xml grants all authenticated users access to all protected pages — role-based access is not enforced at the servlet layer.
- **PCI DSS Req 10**: `[log]` table captures user management actions but does not capture service invocation events — no record of what service methods were called or what data was passed.
