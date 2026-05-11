# pos-connector_LIB — DevOps and Operations View

## 1. Build System and Packaging

The project uses Apache Maven with a minimal POM (`pom.xml`). It does **not** extend `prepaid-parent_PARENT` — it declares no parent POM, making it an independent build artifact.

| Attribute | Value |
|---|---|
| GroupId | `com.ecount.web` |
| ArtifactId | `posconnector` |
| Packaging | `war` (web application archive) |
| Maven version | Maven Wrapper present (`mvnw`, `.mvn/wrapper/`) |
| Java target | Not declared — defaults to compiler default; likely Java 8 or below given Spring 1.2.7 |
| Build output | `posconnector.war` |

**Build command**: `./mvnw clean package` (or `mvn clean package`)

## 2. CI/CD Pipeline

A GitHub Actions workflow file is present at `.github/workflows/codeql.yml`, indicating automated CodeQL static analysis scanning on GitHub. There is **no deployment pipeline** configured in this repository. No Dockerfile, no Kubernetes manifests, and no `.gitlab-ci.yml` are present.

Deployment appears to be entirely manual — copying the WAR to a Tomcat `webapps` directory on a Windows server (evidenced by the hardcoded Windows path `D:\c-base\config\posconnector\` in `StartupServlet.java` line 65).

## 3. Runtime Environment

| Component | Details |
|---|---|
| Application server | Apache Tomcat (WAR deployment, servlet API 2.4 per `web.xml`) |
| Operating system | Windows (hardcoded `D:\c-base\...` paths) |
| Config file location | `D:\c-base\config\posconnector\application-config.properties` |
| JVM memory | Not specified in startup scripts (no `setenv.bat` present in repo) |
| Logging | Log4j 1.x, config at `WEB-INF/classes/log4j.properties` |

## 4. Startup Sequence and Servlet Lifecycle

| Step | Component | Notes |
|---|---|---|
| 1 | `StartupServlet.init()` | Reads `application-config.properties`; creates `ISOMUX`; starts `KeepAlivePos` thread |
| 2 | `KeepAlivePos` thread | Runs at `MAX_PRIORITY`; blocks 120s initially |
| 3 | `POSMessageListener` | Registered with MUX; handles incoming ISO messages |
| 4 | `PosShutdownListener` | Context destroyed → sends logoff; stops MUX thread |

The `KeepAlivePos` thread is started at `Thread.MAX_PRIORITY` (`StartupServlet.java` line 54), which can starve other JVM threads. This is an operational risk in a shared Tomcat instance.

## 5. Dependency Versions (Security Risk Assessment)

All dependencies declared in `pom.xml` are severely outdated:

| Dependency | Version in Repo | Current Stable | Known CVEs |
|---|---|---|---|
| `org.jpos:jpos` | 1.5.2 | 2.x | Multiple (abandoned branch) |
| `org.springframework:spring` | 1.2.7 | 6.x | CVE-2022-22965 (Spring4Shell), others |
| `log4j:log4j` | 1.2.8 | (EOL; migrate to log4j2) | CVE-2019-17571 (RCE via SocketServer), CVE-2022-23302/3/5 |
| `net.sourceforge.jtds:jtds` | 1.2 | 1.3.1 | CVE-2021-43180 (NTLM hash exposure) |
| `javax.servlet:servlet-api` | 2.4 | Jakarta EE 10 | Architectural mismatch risk |
| `junit:junit` | 3.8.1 | 4.13.2 | Test-only; lower severity |

**Critical**: Log4j 1.2.8 is affected by CVE-2019-17571 (deserialization RCE if SocketServer is used) and the 2022 JMSAppender/JDBCAppender CVEs. Upgrade to log4j2 or SLF4J + Logback is mandatory for PCI DSS compliance (Requirement 6.3.3 — all components protected from known vulnerabilities).

## 6. Dependabot Configuration

A `.github/dependabot.yml` is present, meaning GitHub will raise automated PRs for dependency updates. However, given the extremely outdated baseline, automated updates may require manual intervention for major version jumps.

## 7. Monitoring and Alerting

No monitoring configuration is present in the repository. The `KeepAlivePos.java` thread logs connection failures at WARN level (line 45): `logger.warn("Heartbeat failure, initiating reconnection.")`. To properly alert on POS connectivity loss, this log line must be ingested by a SIEM/alerting platform.

Recommended operational monitors:
- Alert on `"Heartbeat failure"` log string in real-time
- Alert on absence of successful keepalive response for > 5 minutes
- Alert on servlet startup failure (no ISO MUX in servlet context)

## 8. Operational Runbook Notes

- **Configuration change procedure**: Edit `D:\c-base\config\posconnector\application-config.properties` on the host; restart Tomcat to reload.
- **Graceful shutdown**: Tomcat context destroy triggers `PosShutdownListener`, which attempts a logoff to the host.
- **Manual reconnect**: No admin endpoint exists; reconnection requires Tomcat restart or will occur automatically via keepalive logic after a detected failure.
- **Log location**: Log4j writes to the location configured in `log4j.properties` (not present in repo — assumed environment-provided).
