# csa_WAPP — DevOps / Operations View

## 1. Build System

| Attribute | Value |
|---|---|
| Build tool | Apache Maven (with Maven Wrapper `mvnw` / `mvnw.cmd`) |
| Java version | 1.8 (source and target: `pom.xml` lines 17-20) |
| Artifact type | WAR |
| Artifact name | `ROOT.war` (`deployment.name=ROOT` in `pom.xml` line 34) |
| Maven version | Wrapper properties in `.mvn/wrapper/maven-wrapper.properties` |
| Parent POM | `com.citi.prepaid.web:webapp-parent:9` |
| GroupId | `com.citi.prepaid.one.web` |
| ArtifactId | `csa` |
| Version | `2.0.51-SNAPSHOT` |

### Key Maven Plugins

| Plugin | Purpose |
|---|---|
| `maven-compiler-plugin:3.8.1` | Java 8 compilation |
| `maven-release-plugin:3.0.0-M1` | Versioned releases |
| `maven-jetty-plugin:6.1.3` | Local dev server (port 9090, context `/csa`) |
| `maven-antrun-plugin` | XDoclet code generation (`webdoclet` task to regenerate `struts-config.xml`) |
| `maven-surefire-plugin` | Unit tests — **`testFailureIgnore=true`** (line 169) silently swallows failures |
| `jacoco-maven-plugin:0.8.12` | Code coverage report (JaCoCo) |
| `maven-parasoft-plugin` | Static analysis via Parasoft |
| `maven-source-plugin:3.2.1` | Source JAR |

### XDoclet Code Generation
`pom.xml` lines 101-123: `maven-antrun-plugin` runs `webdoclet` task in the `test` phase to regenerate `struts-config.xml` from `@struts.action` Javadoc annotations. Any action class change requires running the full Maven lifecycle to regenerate config.

---

## 2. CI/CD Pipelines

### GitHub Actions (primary, post-migration)

**File: `.github/workflows/cicd-deployment.yml`**
- Trigger: `workflow_dispatch` with booleans `skip_tests` and `deploy_to_production`
- Uses reusable workflow `Onbe/om-ci-setup/.github/workflows/build-east-java.yml@main`
- Builds with Java 8, self-hosted runner, publishes to GitHub Packages
- Deploys to UAT: servers `u-az-app01.nam.wirecard.sys`, `u-az-app02.nam.wirecard.sys`
- Deploy path: `D:\c-base\opt\tomcat\servers\CSA\webapps`
- Windows service name: `Apache Tomcat 8.5 CSA`
- Deploy user: `NAM\qa_east_deploy`
- Secret: `QA_EAST_DEPLOY_PASSWORD`

**File: `.github/workflows/cicd-csa-uat-deployment.yml`**
- Trigger: `workflow_dispatch`
- Deploys to **stage** (u-az-app01/02) AND **cert** (q-na-app01.nam.wirecard.sys, q-na-app02.nam.wirecard.sys) simultaneously from the same build artifact
- `DELETE_TARGETS` includes `ROOT` expanded directory — full clean-redeploy
- No production deployment gate in this workflow (cert is the pre-prod stage)

**File: `.github/workflows/codeql.yml`**
- Trigger: `workflow_dispatch`, `pull_request`, scheduled weekly (Tuesdays 18:34 UTC)
- Uses `Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main` with self-hosted Linux x64 runner

**File: `.github/dependabot.yml`**
- Maven ecosystem, weekly schedule, root directory

### GitLab CI (legacy / parallel)

**File: `.gitlab-ci.yml`**
- Includes `northlane/development/application-development/configuration/ci-templates/maven.gitlab-ci.yml`
- Dev hosts: `d-na-app01`; QA hosts: `q-na-app01`, `q-na-app02`
- All Maven phases use `-Dmaven.test.skip=true` — **tests never run in GitLab pipeline**
- Health-check URI: `/login.jsp`

---

## 3. Configuration Management

### Property File Locations (runtime, file system)

| Property File | Location | Contains |
|---|---|---|
| `applicationContext-csa.properties` | `d:/c-base/config/csa/` | `ecount.agent`, `ecount.appId`, `mac.address`, `cbase.home`, feature flags, KYC params, CBTS params |
| `xSecurity.properties` | `d:/c-base/config/service/xSecurity/` | Security service config |
| `dropDownsData-csa.properties` | `d:/c-base/config/csa/` | UI dropdown values (AccessLevel, State, etc.) |
| `director-client.properties` | `D:/c-base/config/` | Director service URL |
| `log4j.xml` | `d:/c-base/config/csa/` | Log4j configuration |

All paths are hardcoded Windows `D:\` drive paths — **no environment variable substitution**, no container-friendly path pattern.

### Key Configuration Parameters (from `csa.xml` placeholder names)

| Property Key | Purpose |
|---|---|
| `ecount.agent` | Agent identifier for all core API calls |
| `ecount.appId` | Application ID for security service |
| `director.address` | XML-RPC Director service endpoint URL |
| `cbtsClient.URIBase` | Cross-border transfer service REST URL |
| `cbtsClient.UserName` / `cbtsClient.Password` | CBTS credentials (injected as constructor args) |
| `live.chat.secret.key` / `live.chat.iv.key` | Symmetric key material for live-chat encryption |
| `kyc.ms.client.id` / `kyc.ms.client.secret` | Azure AD / MS identity for KYC portal |
| `kyc.ms.authority` / `kyc.ms.scope` | Azure token endpoint |
| `cms.url` / `cms.recipient.url` / `cms.op.url` | External portal URLs |
| `cbts.retry.enabled` / `cbts.retry.count` / `cbts.retry.interval` | CBTS retry policy |
| `display.security.questions` / `display.reset.otp` | MFA feature flags |
| `enable.worldlink` | WorldLink international transfer toggle |
| `op.restricted.email.domain` | Operator email domain restriction |

---

## 4. Deployment Target

| Component | Value |
|---|---|
| Application server | Apache Tomcat 8.5 (Windows service) |
| Deployment path | `D:\c-base\opt\tomcat\servers\CSA\webapps` |
| Context path | ROOT (deployed as `ROOT.war`, served at `/`) |
| JVM | Java 8 |
| OS | Windows (all file paths use `D:\`) |
| Environments | dev (`d-na-app01`), stage (u-az-app01/02), cert (q-na-app01/02), UAT (u-az-app01/02) |
| Node count | 2 (HA pair in each environment) |

---

## 5. Observability

| Mechanism | Implementation | Notes |
|---|---|---|
| Application logging | Log4j 1.2.17 (`pom.xml` line 339) with `jsonevent-layout` JSON appender | `log4j.xml` loaded from `d:/c-base/config/csa/`; refresh interval 300 000 ms (`web.xml` line 47) |
| Performance logging | `PerformanceFilter` (`web.xml` line 102) | Logs URL + milliseconds per request to Log4j INFO |
| Audit trail | `AuditManagerImpl` + `JdbcAuditEventDao` → SQL Server | Business-level audit; 20 event types |
| Session attribute logging | `LoggingSessionAttributeListener` (`web.xml` line 151) | Logs session changes |
| Request sanitisation in logs | `LogUtil.sanitizeForLog()` in `PerformanceFilter`, `GlobalExceptionHandler` | CRLF injection prevention |
| No APM / distributed tracing | — | No OpenTelemetry, no AppDynamics/Dynatrace integration visible |
| No health endpoint | — | Health check is just HTTP GET `/login.jsp` (`.gitlab-ci.yml` line 12) |
| Coverage reports | JaCoCo plugin generates to `target/site/jacoco` | Not wired to any quality gate |

---

## 6. Infrastructure Dependencies

| Dependency | Type | Notes |
|---|---|---|
| SQL Server | Relational DB | Three JNDI data sources; container-managed connections |
| ECount Core Director | XML-RPC service | Real-time card/member/transfer operations |
| CBTS (Wirecard) | REST API | Cross-border FX fund transfers |
| RingCentral | Inbound HTTP | CTI auto-login integration (`/loginctl.do`) |
| IEFT / Allotments | Internal service | Payroll allotment management |
| Comment Service | Internal JAR | `com/ecount/services/comment/comment.xml` |
| Message Center | Internal JAR | Email dispatch `MessageCenter-client.xml` |
| Affiliate Service | Internal JAR | `affiliateServiceApplicationContext.xml` |
| Symbol Service | Internal JAR | `applicationContext-symbol.xml` |
| BrandedCurrency Service | Internal JARs | eGift certificate / claimable choice |
| xSecurity Service | Internal JARs (`xsecurity.version=2016.1.1`) | Operator authentication and privilege management |

---

## 7. Risks and Operational Concerns

| Risk | Severity | Detail |
|---|---|---|
| Hardcoded Windows `D:\` paths in config | High | All property file locations use `D:\c-base\...`; impossible to containerise without path rewiring |
| Log4j 1.2.17 | High | EOL; Log4Shell (CVE-2021-44228) affected log4j 2.x, but log4j 1.x has its own CVEs (CVE-2019-17571, CVE-2022-23302/3/5) |
| `testFailureIgnore=true` | High | CI build succeeds even if unit tests fail; no quality gate |
| Tests skipped in GitLab pipeline | High | `MAVEN_BUILD_OPTS: "-Dmaven.test.skip=true"` in all phases |
| No rollback procedure documented | Medium | `cicd-csa-uat-deployment.yml` backs up to `D:\c-base\backup` but no automated rollback workflow |
| No production deployment automation | Medium | `cicd-deployment.yml` deploys to UAT; production step requires `deploy_to_production=true` but no separate prod workflow defined |
| `forceHttps=false` | High | TLS not enforced at application level; credentials could be exposed over plain HTTP if infra misconfigured |
| Tomcat work directory cleaned on deploy | Low-medium | `CLEAN_TARGETS` includes `work` directory — JSP recompilation on restart increases startup time |
| Single region deployment | Medium | All servers in `nam.wirecard.sys` / `d-na-app01` namespace; no DR/failover region visible |
| Java 8 EOL (Oracle support ended 2019 for free tier) | Medium | `pom.xml` line 17 `java.version=1.8`; upgrade path to Java 21 exists (`cicd-deployment.yml` line 22 comment) but not yet enacted |

---

## 8. CI/CD Quality Gates

| Gate | Status |
|---|---|
| Unit tests | Enabled in GitHub Actions (`SKIP_TESTS` optional bool), disabled in GitLab |
| Code coverage threshold | None — JaCoCo reports but no minimum configured |
| Static analysis | Parasoft plugin present but no failure threshold visible |
| CodeQL SAST | Weekly + PR trigger (`.github/workflows/codeql.yml`) |
| Dependency updates | Dependabot weekly Maven scan |
| Manual approval for production | Implicit (no automated prod deploy) |
