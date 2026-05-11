# Enterprise Architect View — crypto-service_SVC

## 1. Platform Generation

| Attribute | Value |
|---|---|
| Generation | Legacy monolith façade — Gen 1/2 codebase wrapped with lightweight containerisation |
| Origin | Inherited from Citi Prepaid / Oracle Financial Services Software (OFSS); `groupId` still references `com.citi.prepaid`; author attribution throughout is "OFSS" |
| Java version | Compiled for Java 21 (pom.xml) but README still states "Java 8" — documentation has not been updated since the Java upgrade |
| Framework | Spring MVC (traditional XML-wired, no Spring Boot, no auto-configuration) |
| Transport | Spring HttpInvoker (Java object serialisation over HTTP) — a deprecated Spring remoting technology |
| Container runtime | Docker / AKS (containerised track) + Windows VM (legacy track) |
| Service mesh | None detected |
| API gateway | GitHub Actions `deployment.yml` sets `PUBLISH_TO_APIM: true` but both `INTERNAL_APIM` and `EXTERNAL_APIM` are false — no active gateway integration |

## 2. Domain Context

This service belongs to the **cryptographic key lifecycle management** sub-domain within Onbe's prepaid card and disbursements platform. Its upstream dependency is the **Wizard UI** (cardholder/programme onboarding portal). Its downstream dependency is the **PGP keyring server** (native OS process) and, indirectly, **Strongbox** (the service that performs actual file encryption using keys registered here).

Functional boundary: manage PGP **public** key registration only. Encryption and decryption of actual data files is out of scope.

## 3. Service Role in the Landscape

```
[Wizard UI / Workbench]
        |
        | Spring HttpInvoker (HTTP, serialised Java)
        v
[crypto-service_SVC / cryptokeysvc]   <-- THIS SERVICE
        |
        | Runtime.exec (OS subprocess)
        v
[pgp CLI binary on host OS]
        |
        | reads/writes
        v
[PGP Keyring on Windows host filesystem]
                              |
                              | public keys exported and used by
                              v
                      [Strongbox / file encryption service]
```

## 4. Key Integration Dependencies

| System | Direction | Protocol | Notes |
|---|---|---|---|
| Wizard UI (Workbench) | Inbound | Spring HttpInvoker over HTTP | Only known consumer; no other callers documented |
| PGP CLI binary | Outbound | OS subprocess (Runtime.exec) | Windows-only; must be pre-installed on host |
| CBASE config volume | Inbound | Filesystem mount | Properties, log config, key files |
| GitHub Packages | Outbound (build only) | HTTPS/Maven | Artefact registry |
| Onbe APIM | Outbound (configured, inactive) | HTTP | `PUBLISH_TO_APIM: true` but both gateway flags false |
| Wirecard DNS hosts | Network | TCP/IP | `qa.nam.wirecard.sys`, `ppnaut.nam.wirecard.sys` hardcoded in docker-compose; residual from Wirecard/Onbe infrastructure lineage |

## 5. Architectural Patterns Observed

| Pattern | Applied? | Notes |
|---|---|---|
| Layered architecture | Yes | common → impl → service tri-module Maven structure |
| Service interface / implementation separation | Yes | `ICryptoService` interface in `common`; `CryptoServiceImpl` in `impl` |
| Spring Remoting (HttpInvoker) | Yes | Both server-side (`HttpInvokerServiceExporter`) and client-side (`HttpInvokerProxyFactoryBean`) configured |
| Spring XML configuration | Yes | No annotations-based config; all wiring via XML beans |
| In-memory cache | Yes | `HttpCryptoSvcClientKeyListCache` with manual invalidation |
| Command pattern | Partial | `ExecuteCommands` wraps OS commands but not as formal GoF Command objects |
| REST / OpenAPI | No | Not present; HttpInvoker only |
| Event-driven / messaging | No | Not present |
| Circuit breaker / resilience | No | Not present |
| Health check endpoint | Yes | `/hc` returns static `"OK"` |

## 6. Platform / Modernisation Status

### What Has Been Done
- Java upgraded to 21 (source/target in pom.xml).
- Tomcat upgraded to 10.1.28 (Jakarta EE 10 / `web-app_6_0.xsd`).
- Containerised with Docker and AKS deployment pipeline added.
- Dependabot enabled for Maven dependency updates.
- CodeQL SAST scanning on weekly schedule.
- Log4j upgraded to Log4j2 (was Log4j 1.x historically).

### What Has Not Been Done (Modernisation Debt)
- README still says "Java 8" and "Tomcat 8.5.57" — not updated.
- Spring HttpInvoker transport: deprecated since Spring 5.3, removed from Spring 6 mainline (ported to `jakarta-spring-remoting` as a separate artifact). This is a significant modernisation blocker.
- No Spring Boot migration; XML-only Spring configuration retained.
- Windows CMD dependency unresolved in containerised deployment.
- `groupId` still references `com.citi.prepaid` — not rebranded to `com.onbe`.
- GitLab CI pipeline still present alongside GitHub Actions — dual-pipeline confusion.
- No OpenAPI/REST contract — impossible to publish meaningful API spec to APIM.

## 7. Blockers and Constraints

| Blocker | Impact | Detail |
|---|---|---|
| Windows CMD hard dependency | Blocks cloud-native operation | `cmd /c start/min` in `ExecuteCommands.java` line 38 cannot run on Linux containers |
| Spring HttpInvoker deprecation | Blocks Spring 6 upgrade | `jakarta-spring-remoting` is a community-maintained shim; long-term support uncertain |
| PGP CLI binary dependency | Blocks portability | Native `pgp` binary must be installed on host; not included in or managed by the container image |
| No authentication on service endpoint | Blocks production security posture | Any internal host can invoke key-management operations |
| `EXCLUDE_STAGE: true` | Reduces deployment safety | No staging environment validation before production push |

## 8. Fitness for Onbe Gen3 Target Architecture

If Onbe's Gen3 target is REST/OpenAPI microservices on AKS with Spring Boot, secrets from Azure Key Vault, and mTLS service mesh:

| Gen3 Criterion | Current State | Gap |
|---|---|---|
| REST + OpenAPI | Spring HttpInvoker (binary serialisation) | Full replacement required |
| Spring Boot | Traditional Spring MVC XML | Migration required |
| Stateless containers on Linux | Windows CMD dependency | OS abstraction layer required |
| Secrets management (AKV) | File-based properties via CBASE volume | Refactor to AKV SDK or CSI driver |
| HSM for key storage | None | New capability required |
| mTLS / service mesh | No TLS at application layer | Network policy or sidecar required |
| Observability (metrics/tracing) | Logging only | Micrometer + distributed tracing required |
| Automated testing | Zero test coverage in CI | Test suite must be written |
