# Solution Architect Report — wirecard_sg-bank-agent_LIB

## API Surface

- **Spring Boot Actuator** at `/sg-bank-agent/monitoring` with ALL endpoints exposed (`exposure.include: '*'`): health, env, beans, mappings, metrics, loggers, heapdump, threaddump, etc.
- **Spring MVC batch job trigger** via `BatchJobController` and `RestJobController` — allows HTTP-triggered Spring Batch job execution.
- **H2 Console** at `/sg-bank-agent/h2-console` — direct database access via browser.
- No public-facing cardholder API; all external communication is via SFTP and ActiveMQ.

## Security Posture

**Critically insecure.** Multiple critical and high severity findings:

### Credential Exposure in Source Code

All of the following are committed to Git history and visible to anyone with repository access:

| Finding | Severity | File | Line |
|---------|----------|------|------|
| CIMB SFTP RSA private key (2048-bit, full key material) | **CRITICAL** | `sg-bank-agent-config/src/main/resources/application.yml` | 34–61 |
| PGP private key passphrase `wirecard` | **CRITICAL** | `application.yml` | 154 |
| AWS access key ID `[REDACTED — rotate immediately]` | **CRITICAL** | `gradle.properties` | 31 |
| AWS secret access key `[REDACTED — rotate immediately]` | **CRITICAL** | `gradle.properties` | 32 |
| Nexus release password `dwil15?` | **HIGH** | `gradle.properties` | 22, 26 |
| Nexus DEV/QA password `acmng` | **HIGH** | `gradle.properties` | 10, 14, 17, 21 |
| Sonar admin password `admin` | **MEDIUM** | `gradle.properties` | 35 |
| AWS Nexus admin password `admin123` | **HIGH** | `gradle.properties` | 13 |
| ActiveMQ local credentials `local/local` | **LOW** (dev only) | `application.yml` | 13–14 |
| PGP private key file committed | **CRITICAL** | `sg-bank-agent-config/src/main/resources/sgba-pgp/0xCE5B683F-sec.asc` | entire file |

### Over-Exposed Actuator Endpoints

`application.yml` lines 72–79:
```yaml
management:
  endpoints:
    web:
      base-path: /monitoring
      exposure:
        include: '*'
  endpoint:
    health:
      show-details: 'ALWAYS'
```

All actuator endpoints are exposed with no authentication configured. This exposes:
- `/monitoring/env` — all environment variables including any runtime-injected secrets.
- `/monitoring/beans` — full Spring bean graph.
- `/monitoring/heapdump` — full JVM heap dump (contains all in-memory data including connection strings, tokens).
- `/monitoring/threaddump` — thread state.
- `/monitoring/loggers` — can be used to enable DEBUG logging remotely.
- `/monitoring/metrics` — performance data.

This configuration, combined with no Spring Security, means an unauthenticated caller can dump the entire JVM heap and extract any runtime secrets.

### H2 Console Enabled

`application.yml` line 87: `spring.h2.console.enabled: true` with `path: /h2-console`. If the production profile shares this configuration (or if production accidentally runs with the default profile), any user with network access can query the production database via a browser.

### SFTP Host Key Bypass (Not Confirmed, Risk Present)

The `CimbSftpCommonChannelConfig.java` uses the `BatchCommonChannelConfig` from `wirecard_sftp-common-utilities_LIB`. The host key verification behavior depends on that library's configuration. If `wirecard_sftp-common-utilities_LIB` implements a permissive `HostKeyRepository` (a common pattern in test utilities that bleeds into production), then man-in-the-middle attacks on the CIMB SFTP connection are possible. This should be verified.

## Technical Debt

- **Spring Boot 1.5.x → 3.x**: Full framework migration required.
- **PGP library update**: BouncyCastle 1.48 → 1.78+ (multiple CVEs in 1.48).
- **JSch → Apache SSHD or SSHj**: JSch 0.1.55 has known CVEs; Apache SSHD (used in test-utilities) is the preferred replacement.
- **Secrets management**: All credentials must be moved to Vault, Azure Key Vault, or environment injection. Git history must be purged.
- **Actuator endpoint lockdown**: Add Spring Security to restrict all actuator endpoints to authenticated admin users or localhost only.
- **H2 console removal from non-test profiles**.
- **XSLT-based transformation**: The XSLT approach for CIMB file generation is fragile and difficult to test; replace with a typed Java object mapper.
- **Page size of 1**: The `page-size: 1` in batch job configuration is likely a workaround for a data issue. Should be investigated and fixed to improve throughput.
