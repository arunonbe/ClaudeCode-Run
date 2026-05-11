# prepaid-parent_PARENT — Enterprise Architect View

## 1. Architectural Role

`prepaid-parent_PARENT` is the **platform architectural baseline** for Onbe's modern prepaid services. In enterprise architecture terms, it is a **reference architecture artifact** that encodes technology decisions, version governance, and build standards for the entire prepaid service portfolio.

It serves three enterprise architecture functions:
1. **Technology standardization**: Fixes the technology stack version baseline for all child services
2. **Security governance**: Enforces banned dependencies and version requirements at build time
3. **Developer experience standardization**: Provides consistent build behavior across all teams

## 2. Technology Stack Governance (Full Dependency Version Inventory)

The following table captures all `<properties>` version entries from `pom.xml` (lines 12–134):

### Runtime Platform
| Property | Version |
|---|---|
| `spring-boot.version` | 3.4.5 |
| `spring-cloud.version` | 2023.0.2 |
| `maven.compiler.source/target` | 21 |

### Core Utilities
| Property | Version |
|---|---|
| `commons-codec.version` | 1.17.0 |
| `commons-beanutils.version` | 1.11.0 |
| `commons-lang.version` | 2.6 |
| `commons-io.version` | 2.14.0 |
| `commons-httpclient.version` | 3.1 |
| `commons-text.version` | 1.11.0 |
| `commons-collections.version` | 3.2.2 |
| `commons-validator.version` | 1.7 |
| `commons-net.version` | 3.9.0 |
| `commons-dbcp.version` | 1.4 |
| `commons-pool.version` | 1.6 |
| `gson.version` | 2.10.1 |
| `json.version` | 20231013 |

### Database
| Property | Version |
|---|---|
| `mssql-jdbc.version` | 12.6.0.jre11 |
| `jtds.version` | 1.2.2 |
| `msbase/mssqlserver/msutil.version` | 2.2.0040 |

### XML / Serialization
| Property | Version |
|---|---|
| `jakarta.xml.bind-api.version` | 4.0.1 |
| `jaxb-xjc.version` | 4.0.4 |
| `jaxb-impl.version` | 4.0.4 |
| `jaxb-api.version` | 2.3.1 |
| `xstream.version` | 1.4.20 |
| `xmlbeans.version` | 2.3.0 |
| `dom4j.version` | 1.6.1 |
| `org.dom4j.version` | 2.1.4 |

### Messaging
| Property | Version |
|---|---|
| `activemq-core.version` | 6.1.3 |
| `ibm.websphere.version` | 6.0 |
| `axis.version` (Jakarta variants) | 1.4 |

### Cryptography and Security
| Property | Version |
|---|---|
| `bcpg-jdk18on.version` | 1.78 |
| `bcprov-jdk18on.version` | 1.78 |
| `bcpg-jdk15on.version` | 1.48 |
| `bcprov-jdk15on.version` | 1.48 |
| `java-jwt.version` | 3.4.0 |
| `msal4j.version` | 1.16.1 |

### File Transfer / SSH
| Property | Version |
|---|---|
| `sshd-core.version` | 2.13.0 |
| `sshd-scp.version` | 2.13.0 |
| `sshd-sftp.version` | 2.13.0 |
| `jsch.version` | 0.1.55 |

### Cloud
| Property | Version |
|---|---|
| `aws-java-sdk-s3.version` | 1.12.747 |

### Circuit Breaker / Resilience
| Property | Version |
|---|---|
| `resilience4j-circuitbreaker.version` | 2.1.0 |
| `feign-core/jackson/slf4j.version` | 13.1 |

### UI / Web
| Property | Version |
|---|---|
| `springfox-swagger2.version` | 3.0.0 |
| `springfox-swagger-ui.version` | 3.0.0 |
| `struts.version` | 1.2.9 |
| `displaytag.version` | 1.2 |
| `poi.version` | 5.2.5 |
| `velocity.version` | 1.4 |

### Testing
| Property | Version |
|---|---|
| `junit.version` | 4.13.2 |
| `jmock-junit4.version` | 2.12.0 |
| `wiremock-jre8.version` | 3.0.1 |
| `wiremock-standalone.version` | 3.0.1 |
| `greenmail.version` | 2.0.1 |
| `easymock.version` | 2.4 |

## 3. Architectural Concerns

### 3.1 Version Staleness in Managed Versions
Despite being a modern POM, several managed versions show staleness:

| Dependency | Managed Version | Current | Concern |
|---|---|---|---|
| `struts` | 1.2.9 | EOL | Struts 1.x has critical CVEs (CVE-2014-0094, CVE-2016-1181). Presence in managed versions suggests legacy services using this framework still exist. |
| `java-jwt` | 3.4.0 | 4.x | Auth0 JWT 3.4.0 has vulnerabilities; 4.x is current |
| `jsch` | 0.1.55 | 0.2.x | JSch 0.1.55 has known issues; 0.2.x is maintained |
| `commons-httpclient` | 3.1 | Apache HttpClient 5.x | Commons HttpClient 3.1 is EOL (2007) |
| `commons-dbcp` | 1.4 | 2.x | DBCP 1.4 is EOL; HikariCP is preferred with Spring Boot |
| `velocity` | 1.4 | 2.3 (Velocity Engine) | Velocity 1.4 is EOL |
| `easymock` | 2.4 | 5.x | Very old test library |
| `springfox-swagger2` | 3.0.0 | springdoc-openapi is preferred | Springfox is unmaintained |

### 3.2 Dual Bouncy Castle Versions
Managing both `jdk15on` (1.48) and `jdk18on` (1.78) simultaneously risks classpath conflicts if both are included. Architecture guidance should explicitly state that new services must use only `jdk18on`.

### 3.3 `jsafe.version` = `"x"`
The property `jsafe.version` is set to the literal value `x` (pom.xml line 44), making this dependency unusable as-is. `jsafe` is RSA Security's (now Broadcom) FIPS-certified cryptographic library. If any child service references this, the build will fail. This appears to be a placeholder for a proprietary library that requires manual installation.

## 4. Enterprise Governance Model

The parent POM enforces a **layered governance model**:
1. **Hard blocks**: Log4j 1.x banned; SNAPSHOT deps in releases banned; Java < 21 banned
2. **Soft guidance**: Managed versions available but not mandatory (child can override)
3. **Transitive control**: `banTransitiveDependencies` with Spring/Jackson/Hibernate exclusions

This model enables strict control over the most critical security dependencies while allowing flexibility for legacy compatibility.

## 5. Alignment with Onbe Platform Strategy

The parent POM's technology choices align with Onbe's observable platform direction:
- **Azure-native**: MSAL4J for Azure AD; GitHub Actions for CI/CD; Azure App Configuration (inferred from deployment patterns)
- **Multi-cloud**: AWS S3 SDK managed alongside Azure libraries
- **Microservices**: Feign, Resilience4j, Spring Cloud — standard microservices toolkit
- **Containerization**: Spring Boot fat JAR packaging enables Docker deployment

Services not yet inheriting this parent (`pos-connector_LIB`, `prepaid-batch-framework_LIB`) should be assessed for migration priority based on CDE scope and risk.
