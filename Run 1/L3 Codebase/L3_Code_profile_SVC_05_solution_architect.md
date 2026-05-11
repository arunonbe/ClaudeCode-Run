# Solution Architect — profile_SVC

## Technical Architecture

```
profile-common/             -- IProfile interface + domain model (records, outputs)
profile-client/
  IProfileClient            -- extends IProfile
  ProfileClientFactory      -- factory for creating client instances
  ProfileXMLRPCClient       -- thread-safe XML-RPC client
    MultiThreadedHttpConnectionManager (1-minute connection timeout)
    SimpleProfileServiceLocationResolvingCache (1-hour Director cache)
  ProfileXMLRPCClientUtils  -- invokeXMLRPCCall helper
profile-impl/
  ProfileImpl               -- IProfile + IDatasourceConfigured + IDirectorLocationAware
    ProfileLibrary          -- agent-scoped singleton
      ProfileDataLibrary    -- DAO orchestration
        FdrProfileClass*    -- FDR RDBMS DAOs
        FdrProfileScope*    -- FDR scope DAOs
        CoreProfileMember*  -- Core2 RDBMS DAOs
profile-xmlrpc/
  ProfileXmlRPCServlet      -- extends XmlRPCServlet (HTTP POST/GET)
    ProfileProxy            -- XML-RPC method dispatcher → ProfileImpl
profile-monitor/
  MonitorMain               -- standalone health check tool
```

## API Surface

The service exposes an **XML-RPC interface** over HTTP POST:

- **Endpoint:** `/services/ProfileWebServices` (from `BACKEND_SUFFIX` in deployment config)
- **RPC Interface:** `ECountCore.Profile`
- **Methods:** `ClassRetrieve`, `ClassLogInquiry`, `ClassPut`, `ClassGet`, `ClassUpdate`, `ClassCreate`, `ClassDelete`, `ClassSelect`, `ClassDrop`, `ScopeCreate`, `ScopeRetrieve`, `ScopeUpdate`, `ScopeDelete`

No REST, GraphQL, or gRPC interface exists.

## Security Posture

### Authentication / Authorisation
- No built-in authentication on the XML-RPC endpoint
- `agent` parameter is an unverified free-form string (e.g., `B2CTEST`)
- Security is entirely perimeter-based — caller verification relies on network access controls

### Cryptography
No application-level cryptography. Transport security depends on infrastructure (TLS termination upstream).

### Secrets Management
- Database credentials managed externally via `NamedDataSourcesList` / Spring data source configuration
- Maven repository credentials in `.mvn/wrapper/settings.xml`
- No secrets in version-controlled source code (settings.xml is referenced but credentials not visible)

### CVE / Dependency Risk

| Dependency | Version | Risk |
|---|---|---|
| Apache Commons HttpClient | 3.1.4 (referenced as `xmlrpc.version` dependency) | Critical — EOL since 2011; multiple known CVEs (HTTPCLIENT-1481, etc.) |
| Apache XML-RPC | 3.1.4 (`com.citi.prepaid.service.core:xmlrpc`) | Unmaintained |
| Lombok | 1.18.30 | Recent — low risk |
| `ecount-system:4.0.3`, `ecountcore.common:3.1.6`, `xplatform:6.5.8` | Internal proprietary | Cannot assess without source |
| `prepaid-parent:6.0.13` | Internal BOM | Dependency version management responsibility |

### CodeQL
Configured to run on all pushes and PRs (via `codeql.yml` → `om-ci-setup codeql-auto.yml`).

### Trivy Container Scanning
`.trivyignore` present — some container vulnerabilities have been acknowledged/suppressed. Content of trivyignore not available in source.

## Technical Debt

| Item | Location | Severity |
|---|---|---|
| Apache Commons HttpClient 3.x | `profile-client/pom.xml` (via `xmlrpc` dependency) | Critical — EOL, CVEs |
| XML-RPC protocol | Entire service | High — no authentication, binary-incompatible with REST consumers |
| Tests skipped in CI (`-Dmaven.test.skip`) | `deployment.yml`, `github-package-publish.yml` | High |
| `ProfileLibrary` is an agent-scoped singleton — concurrent access to `ProfileLibrary.getInstance(agent, this)` | `ProfileImpl.java:81,112,144,181,216,251,285,313,349,384,415,452` | Medium — thread safety of singleton creation not visible without `ProfileLibrary` source |
| `logException()` prints full stack trace via `log.error(msg)` string concatenation | `ProfileImpl.java:495–503` | Low — stack trace in log is good, but string-building anti-pattern |
| `.gitlab-ci.yml` present — dual CI systems | Root | Medium — maintenance burden |
| `4.0.4-SNAPSHOT` — no stable release version | `pom.xml:14` | Medium |
| Windows batch build scripts (`mvn_core2_Profile.bat`) | Root | Low — not containerised developer tooling |
| PACT verification disabled | `deployment.yml` line `VERIFY_PROVIDER_PACT: false` | Medium — no contract test |

## Gen-3 Migration Requirements

To migrate Profile SVC to Gen-3:

1. **Replace XML-RPC with REST API** — design RESTful endpoints for each profile operation (GET/PUT/POST/DELETE on `/profiles/{scope}/{key}`)
2. **Replace Apache Commons HttpClient 3.x** — migrate to Spring WebClient or httpclient5
3. **Implement OAuth2/OIDC authentication** — replace the unverified `agent` string with JWT-based caller identity
4. **Replace Director service discovery** — use Kubernetes service DNS or Spring Cloud Discovery
5. **Replace `ecount-system` / `ecountcore.common` / `xplatform` dependencies** — re-implement DAL using Spring Data JPA or JDBC Template
6. **Adopt `platform-envers-db-audit`** — replace ad-hoc `ClassLogInquiry` audit with Hibernate Envers
7. **Enable PACT contract tests** — add `VERIFY_PROVIDER_PACT: true` once REST API is defined
8. **Re-enable test execution** — remove `-Dmaven.test.skip` from CI

## Code-Level Risks (file:line references)

| Risk | File | Line (approx.) | Detail |
|---|---|---|---|
| Apache HttpClient 3.x static singleton with no connection pool limits | `ProfileXMLRPCClient.java` | 91–97 | `connectionManager = new MultiThreadedHttpConnectionManager()` — no max connections set beyond 1-minute timeout |
| `ProfileImpl.logException()` uses string concatenation with stack trace | `ProfileImpl.java` | 495–503 | `msg.append(sw.toString())` inside `log.error()` — minor but creates large log messages |
| Director cache is 1 hour — no invalidation on failure | `ProfileXMLRPCClient.java` | 111 | `new SimpleProfileServiceLocationResolvingCache(directorLocation, agent, 1000*60*60)` — stale for 60 min after failover |
| Tests skipped in all CI builds | `deployment.yml:32`, `github-package-publish.yml:41` | — | `-Dmaven.test.skip` in all Maven invocations |
| `PACT_PACTICIPANT` declared but `VERIFY_PROVIDER_PACT: false` | `deployment.yml:27–28` | — | Contract tests inactive |
