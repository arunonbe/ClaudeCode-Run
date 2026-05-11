# Enterprise Architect — oneplatform-rest_API

## Platform Generation
**Gen-3 (transitional)** — Spring Boot 3.x on Java 21 with modern JWT-based security, Redis caching, and Dapr service mesh integration. However, it retains deep dependencies on Gen-1/2 internal libraries (`xplatform 6.5.9`, `xsecurity 4.0.3`, `xaffiliate-service 4.0.1`, `branded-currency 3.0.4`, `comment 3.0.1`) and communicates with Gen-1 XMLRPC backends via director-service. The surface is modern; the core business logic is bridged through legacy adapters.

## Business Domain
**Recipient Experience — Cardholder Self-Service**
This is the primary backend for the MyPaymentVault cardholder portal, covering the full cardholder journey: onboarding, authentication, balance inquiry, payment disbursement selection, and fund access across all supported rails.

## Architectural Role
- **Backend-for-Frontend (BFF)**: Serves the `oneplatform-react_WAPP` / `oneplatform_WAPP` UI applications.
- **Multi-rail payment orchestrator**: Routes payment disbursement requests to the appropriate downstream rail (ACH, PayPal, Venmo, push-to-debit, IEFT, Western Union, Ria).
- **Authentication gateway**: Issues and validates JWT tokens; integrates MFA, BioCatch, reCAPTCHA, and OTP grace period logic.
- **Redis consumer**: Reads affiliate/program configuration from Redis (populated by `oneplatform-rediscache-adminservice`).
- **Dapr client**: Delegates to Dapr-hosted microservices for PayPal redemption, OTP, GeoIP, and push provisioning.

## System Dependencies
| System | Direction | Protocol |
|--------|-----------|----------|
| `oneplatform-react_WAPP` / `oneplatform_WAPP` (UI) | Upstream consumer | HTTP/REST + JWT |
| `oneplatform-rediscache-adminservice` | Upstream data producer (shared Redis) | None (shared cache) |
| `director-service` (ecount XMLRPC) | Downstream | HTTPS XMLRPC |
| `cbaseapp`, `EcountCore`, `jobsvc` (SQL Server) | Downstream | JDBC/TLS 1.2 |
| Dapr sidecar + downstream services | Downstream | HTTP/Dapr SDK |
| `PayPal`, `Venmo` | External downstream | HTTPS OAuth + REST |
| `CBTS` (cross-border transfer) | Downstream | HTTP/REST |
| `BioCatch` | External downstream | HTTPS REST |
| `Google reCAPTCHA Enterprise` | External downstream | HTTPS REST |
| Azure Redis Cache | Shared data store | TLS/Jedis |
| Azure App Configuration | Config/feature flag provider | HTTPS |
| `xSSO` | Downstream (SSO token decryption) | HTTPS |
| `Western Union` | External downstream | HTTPS + certificate |

## Integration Patterns
- **BFF + JWT stateless session**: Every request authenticated via JWT filter (`JwtAuthFilter`); no server-side session.
- **Cache-aside read**: Affiliate/content data read from Redis; falls back to SQL if cache miss (not confirmed in all paths).
- **Dapr service invocation**: Loose coupling to PayPal, OTP, GeoIP, push provisioning via Dapr HTTP sidecar.
- **XMLRPC legacy bridge**: Core card/transaction/member operations delegated to director-service via xplatform XMLRPC library.
- **Outbox / pub-sub**: PayPal payout state changes published via Dapr `OutboxMessage` / `PayoutRequestChangeEvent` pattern.
- **Feature flags**: Azure App Configuration feature management controls rollout of new behaviors (e.g., affiliate content cache usage).
- **Ehcache + Redis**: Two-layer caching — in-process Ehcache for frequently read copy data; Redis for cross-instance shared affiliate data.

## Strategic Status
- **Active / core production service** (version 5.8.0; prod profile complete with production hostnames).
- The SNAPSHOT dependency on `onbe-cloud-starter` indicates active development.
- The volume of payment rails and controllers (20+ controllers, 25+ services) makes this the most business-critical service in the six-repo set.
- Long-term, the deep coupling to `xplatform`, `xsecurity`, and director-service XMLRPC represents the primary modernization barrier.

## Migration Blockers
1. **xplatform XMLRPC dependency** (`com.ecount:xplatform:6.5.9`): Core card, registration, transaction, and authentication business logic lives in this legacy library and its downstream XMLRPC services. Replacing it requires a full domain re-implementation.
2. **xsecurity dependency** (`com.ecount.service.xsecurity:xsecurity-web/impl:4.0.3`): Custom security framework wrapping Spring Security; tightly coupled to xplatform identity model.
3. **Spring XMLRPC via director-service**: All ecount backend calls route through a central dispatcher at `bootAddress`; cannot be decomposed without replacing director-service.
4. **Three-database JDBC coupling**: Business logic is spread across stored procedures in `cbaseapp`, `EcountCore`, and `jobsvc` — migrating to a microservice model requires SP migration.
5. **Dapr required at runtime**: Any deployment without a properly configured Dapr sidecar breaks PayPal, OTP, GeoIP, and push provisioning flows — introduces operational coupling.
6. **Hardcoded secrets in YAML**: Multiple secrets in source control must be remediated before CI/CD pipeline can safely publish this artifact.
