# Solution Architect — oneplatform_WAPP

## Technical Architecture
- **Language**: Java 8.
- **Web framework**: Apache Struts 1.3.10 (action-based MVC with Tiles layout, xDoclet annotation-driven config generation).
- **DI / IoC**: Spring 2.0.3.
- **ORM / Data access**: Spring JDBC, custom multi-context JDBC (`spring-dbctx`), jTDS 1.2 JDBC.
- **Logging**: Log4j 1.2.17 + JSON event layout (Logstash), filesystem config.
- **Serialization**: Jackson 2.5.1, Gson 2.3.1, XStream 1.4.8, `org.json`.
- **Security**: xSecurity library, RSA MFA, custom CSRF (`OneTokenProcessor`), custom session management, Biocatch.
- **Transport**: HTTPS enforced via `SSLLoginFilter`; session cookies set with `Secure` + `HttpOnly` flags (via `OPConstants.VaConstants`).
- **Template engine**: JSP / JSTL / Tiles for desktop views; HTML templates aggregated into `cpmain.html` for mobile SPA.
- **Deployment**: WAR to Tomcat on Windows, port 9000 dev / standard HTTP(S) prod.

## API Surface

### Mobile JSON API
Single action endpoint pattern: HTTP POST with JSON body `{inputRequest: {action: {type: "..."}, data: {...}}}`. Response: `{successResponse: {...}}` or `{errorResponse: {...}}`.

Key action types (inferred from `MobileLoginAction`, factory pattern):
- `login` — standard login.
- `pclogin` — payment hub return login.
- `cclogin` — claim code login.
- Dashboard, alerts, profile, contacts, bank transfer, global deposits, etc. (via `MobileActionFactory`).

### Desktop / Web
Struts action paths: `/activate/card/display`, `/defaultlogin.do`, etc. (generated via xDoclet from `@struts.action` annotations).

## Security Posture

### Authentication
- Username + salted-hash password (new format) or MD5 (legacy, migrated on login).
- MFA: RSA (device fingerprint), OTP (phone), security questions — resolved by `MobileMFAResolver`.
- CSRF: `OneTokenProcessor.saveCSRFToken()` on state-changing flows.
- CAPTCHA: SimpleCaptcha on login forms (configurable per affiliate).
- Biocatch behavioral analytics on login.
- Session invalidation on login (`LoginAction.invalidate()`).
- Cookie flags: `Secure`, `HttpOnly` (see `OPConstants.VaConstants`).

### Cryptography
- **MD5 password hashes** (`MobileLoginAction.java:201`): `Password.encryptPasswordMD5(password)`. MD5 is cryptographically broken and does not meet PCI DSS Req 8.3 for password storage. This is a **critical finding**.
- New format: `Password.genSaltedHashPassword()` / `getSaltedHashPasswordFromPlainTextPwd()` — algorithm not visible in this repo but assumed to be bcrypt or PBKDF2 based on naming.
- No explicit at-rest encryption of database fields in this layer.

### Secrets Management
- Database credentials in Spring XML context files (not in this repo; likely CONFIG_dev/qa/prod repos).
- KYC client secret referenced via property key `kycMsClientSecret` (loaded from Spring property placeholder).
- No vault or secrets manager integration visible in this application.

### CVEs and Vulnerable Dependencies

| Dependency | Version | CVE Highlights |
|---|---|---|
| `log4j:log4j` | 1.2.17 | CVE-2019-17571 (CVSS 9.8, RCE via SocketServer), CVE-2022-23302/23303/23305 |
| `org.apache.struts:struts-core` | 1.3.10 | Multiple historical CVEs; Struts 1 EOL since 2013 |
| `org.springframework:spring` | 2.0.3 | Extremely outdated; Spring 2.x EOL since ~2012; multiple CVEs |
| `com.thoughtworks.xstream:xstream` | 1.4.8 | CVE-2020-26217, CVE-2021-21344/21345/21346 (RCE via deserialization) |
| `commons-httpclient` | 3.0.1 | EOL; replaced by Apache HttpClient 4/5 |
| `net.sourceforge.jtds:jtds` | 1.2 | Outdated; missing TLS 1.2/1.3 support |
| `lowagie:itext` | 5.0.5 | EOL; CVE-2017-5846 and others |
| `com.fasterxml.jackson.core:jackson-databind` | 2.5.1 | Dozens of deserialization CVEs in 2.x < 2.9.10.x |
| `org.jsoup:jsoup` | 1.8.3 | CVE-2021-37714 (ReDoS) |
| `xerces:xercesImpl` | 2.8.1 | CVE-2012-0881 (DoS) |
| `com.google.code.gson:gson` | 2.3.1 | CVE-2022-25647 (ReDoS) |
| `commons-fileupload` | 1.4 | CVE-2023-24998 |

## Technical Debt
1. **Entire stack is EOL**: Struts 1, Spring 2, Log4j 1, Java 8, jTDS.
2. **MD5 password hashes**: active production security vulnerability.
3. **Tests skipped in CI/CD**: no automated test gate in either Jenkins or GitLab pipeline.
4. **Hardcoded file system paths** in `web.xml` (`D:/c-base/...`).
5. **xDoclet code generation**: pre-annotation technology that makes build fragile and IDE support poor.
6. **1 400+ line `MobileLoginAction.executeAction()` method**: a single method handling 15+ distinct login/MFA/claim scenarios. Extremely difficult to test, review, or maintain.
7. **`project.build.sourceEncoding=Cp1252`**: non-UTF-8 source encoding; may cause issues with internationalization.
8. **XStream 1.4.8**: known RCE deserialization vulnerabilities; used for serialization in several dependent libraries.

## Gen-3 Migration Requirements
1. Rewrite all cardholder flows in Spring Boot 3.x / React (Gen-3 recipient web).
2. Replace Struts action framework with Spring MVC / REST.
3. Replace Log4j 1.x with Log4j 2.x or SLF4J/Logback + structured logging.
4. Replace MD5 password hashing with bcrypt/Argon2.
5. Upgrade all EOL dependencies or remove.
6. Replace jTDS with Microsoft JDBC Driver for SQL Server.
7. Externalize configuration to Azure App Config or Spring Cloud Config.
8. Containerize (remove Windows path dependencies).
9. Re-implement all MFA flows using Gen-3 MFA service.
10. Re-integrate Biocatch, Cambridge FX, KYC via Gen-3 service adapters.

## Code-Level Risks (file:line references)
- `src/main/java/com/ecount/one/mobile/MobileLoginAction.java:201` — `Password.encryptPasswordMD5(password)`: MD5 hash comparison; critical PCI DSS Req 8.3 violation.
- `src/main/java/com/ecount/one/mobile/MobileLoginAction.java:98-99` — plaintext password extracted from JSON in memory; must never be logged (no explicit guard).
- `src/main/java/com/ecount/one/mobile/MobileLoginAction.java:392` — `new Integer(affiliateId)` — deprecated boxing constructor, Java 9+ deprecation warning.
- `src/main/webapp/WEB-INF/web.xml:49` — `file:D:/c-base/config/oneplatform/log4j.xml`: hardcoded Windows path.
- `src/main/webapp/WEB-INF/web.xml:82` — `fileUploadTempRepository = d:/C-Base/logs`: uploads temporarily co-located with logs.
- `pom.xml:43` — `struts.version=1.3.10`: EOL framework with known CVEs.
- `pom.xml:40` — `log4j.version=1.2.17`: EOL with critical CVEs.
- `pom.xml:48` — `xstream.version=1.4.8`: RCE deserialization CVEs.
- `pom.xml:58` — `jackson.version=2.5.1`: multiple deserialization CVEs.
- `Jenkinsfile:13` — `mvn clean deploy -Dmaven.test.skip=true`: no test gate in deployment pipeline.
