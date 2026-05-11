# Enterprise Architect View — xsso_SVC

## Platform Generation
**Gen-1** — Original SSO service. Despite Java 21 compilation, containerisation with Docker, and GitHub Actions CI/CD (which are modernisation indicators), the core SSO mechanism (RSA/JKS, custom Base64Coder, XStream deserialization, per-affiliate JKS keystores, no token expiry) is Gen-1 in design and security posture.

## Business Domain
Identity and Access Management / Single Sign-On. Security-critical service enabling cross-application authentication for cardholder sessions across partner applications and internal One Platform systems.

## Role in the Platform
**Authentication gateway.** xsso_SVC is the cryptographic boundary for cardholder identity tokens. All partner applications that wish to authenticate a cardholder without a fresh login must pass a token through this service. It is the sole trust anchor for SSO in the platform.

## Dependency Hierarchy
```
xplatform-library_LIB (infrastructure — crypto, cache, config)
        |
xplatform_LIB 6.1.8 (business logic — Affiliate, GetPuid, EManageManager)
        |
xsso_SVC (this repo — SSO token service)
        ^
        |  (consumed by)
Partner applications / One Platform services (SSO token consumers)
```

## Dependencies
| Dependency | Direction | Notes |
|---|---|---|
| xplatform_LIB 6.1.8 | Upstream | Affiliate resolution, PUID lookup, EManageManager |
| JobSvcDataSource (SQL Server) | External | PUID→MemberId lookup |
| JKS keystores (per-affiliate) | External (filesystem) | RSA key material; mounted via Docker volume |
| spring-dbctx-mock 2.0.1 | Compile (!) | Mock library in compile scope — anomalous |
| XStream | Framework | XML deserialisation of token payload |
| dom4j | Framework | XML parsing for timestamp validation |
| jtds + mssql-jdbc | Framework | Dual SQL Server drivers |
| Tomcat 10.1.28 | Container | Runtime; embedded in Docker image |
| BellSoft Liberica JRE 21 Alpine | Base image | Container base |

## Integration Patterns
- **HTTP Servlet pattern** — four independent HTTP servlets; no REST framework
- **Per-affiliate JKS keystore pattern** — cryptographic isolation per partner
- **Spring XML wiring** — bean graph defined in `applicationContext-xSSO.xml`
- **JNDI DataSource** — JobSvc DB injected via JNDI
- **Docker + GitHub Actions CI/CD** — containerised deployment

## Strategic Status
**High-priority modernisation target.** Reasons:
- Security-critical service with documented cryptographic weaknesses (hardcoded IV, default passwords, no token expiry, JKS on filesystem)
- Container-ready infrastructure (Dockerfile, docker-compose, GitHub Actions) — migration effort is lower than non-containerised services
- SNAPSHOT version (`3.0.1-SNAPSHOT`) — active development path
- No token expiry means the service cannot participate in a zero-trust security model
- Wirecard-branded host entries in docker-compose confirm legacy infrastructure dependencies

Recommended direction: Replace with an industry-standard IdP integration (e.g., Azure AD B2C, Okta, or Keycloak) with JWT-based tokens, short expiry, refresh tokens, and PKCS12 keystores backed by Azure Key Vault.

## Migration Blockers
- **Partner JKS keystores:** Each affiliate has a dedicated RSA keypair; migrating requires coordinating key rotation with all partners simultaneously
- **Token format dependency:** Partner applications are coded to submit the existing RSA-encrypted Base64 format; migration requires a transition period with both formats supported
- **`spring-dbctx-mock` in compile scope:** Suggests production code may have a dependency on mock infrastructure — requires investigation before migration
- **No token expiry protocol:** Adding expiry requires changes to all token producers (partners) and consumers simultaneously
- **PUID→MemberId coupling:** The PUID resolution depends on the JobSvc database and the `GetPuid` stored procedure — this coupling must be preserved in any replacement
- **Wirecard QA host IPs hardcoded:** Indicates active dependency on Wirecard infrastructure that may not be replaceable without a separate workstream
