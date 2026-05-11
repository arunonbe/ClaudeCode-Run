# prepaid-parent_PARENT — Data Architect View

## 1. Data Architecture Perspective

As a Maven parent POM, `prepaid-parent_PARENT` does not define data models, schemas, or data flows itself. However, its `<dependencyManagement>` block determines **what data access technologies and data serialization libraries** are available to all child services. This makes it architecturally significant from a data perspective — it defines the platform's data layer technology choices.

## 2. Database Connectivity Libraries Managed

| Library | Version | Purpose | Notes |
|---|---|---|---|
| `mssql-jdbc` | 12.6.0.jre11 | Microsoft SQL Server JDBC driver | Primary RDBMS for Onbe prepaid platform |
| `net.sourceforge.jtds:jtds` | 1.2.2 | Legacy jTDS SQL Server driver | Being phased out in favor of mssql-jdbc |
| `commons-dbcp` | 1.4 | JDBC connection pooling | Legacy; Spring Boot autoconfigures HikariCP |
| `commons-pool` | 1.6 | Object pooling for DBCP | |
| `com.microsoft.sql2k.jdbc:msbase/mssqlserver/msutil` | 2.2.0040 | Legacy SQL 2000 drivers | Legacy artifact; present for backward compatibility |

**Observation**: Both `mssql-jdbc` (modern) and `jtds`/`msbase`/`mssqlserver` (legacy SQL 2000 era) drivers are managed. This reflects the coexistence of modern Spring Boot services and legacy platform components. The presence of the SQL 2000 drivers (`mssqlserver` version 2.2.0040) suggests some services may still target very old SQL Server instances.

## 3. Data Serialization Libraries Managed

| Library | Version | Purpose |
|---|---|---|
| `com.google.code.gson:gson` | 2.10.1 | JSON serialization/deserialization |
| `org.json:json` | 20231013 | JSON reference implementation |
| `com.thoughtworks.xstream:xstream` | 1.4.20 | XML/object serialization |
| `jakarta.xml.bind:jakarta.xml.bind-api` | 4.0.1 | JAXB (Jakarta EE XML binding) |
| `com.sun.xml.bind:jaxb-impl` | 4.0.4 | JAXB implementation |
| `xmlbeans` | 2.3.0 | XML bean binding |
| `dom4j:dom4j` | 1.6.1 | Legacy DOM4J XML |
| `org.dom4j:dom4j` | 2.1.4 | Modern DOM4J XML |

**Note**: Both `jackson-*` (via Spring Boot BOM) and `gson` are managed. The Spring Boot BOM transitively includes Jackson as the primary serialization framework. Gson is retained for legacy compatibility.

## 4. Cryptographic Libraries Managed

Two generations of Bouncy Castle are managed:

| Library | Version | Use Case |
|---|---|---|
| `bcpg-jdk15on` | 1.48 | PGP operations (legacy JDK 1.5 variant) |
| `bcprov-jdk15on` | 1.48 | BouncyCastle crypto provider (legacy) |
| `bcpg-jdk18on` | 1.78 | PGP operations (current JDK 18+ variant) |
| `bcprov-jdk18on` | 1.78 | BouncyCastle crypto provider (current) |

The managed version 1.78 is current and addresses known vulnerabilities in earlier releases. The presence of both `jdk15on` and `jdk18on` variants indicates a planned migration path — new services should use `jdk18on` variants.

**PCI DSS Relevance**: Bouncy Castle is used for PGP encryption of settlement files (NACHA/ACH) and file signing. The transition to `jdk18on` 1.78 is required to use modern algorithm support and avoid deprecated ciphers.

## 5. Messaging Infrastructure Libraries Managed

| Library | Version | Purpose |
|---|---|---|
| `org.apache.activemq:activemq-broker` | 6.1.3 | ActiveMQ message broker (embedded or client) |
| `ibm.websphere:jakarta-com.ibm.mq` | 6.0 | IBM MQ client (Jakarta namespace) |
| `ibm.websphere:jakarta-com.ibm.mqjms` | 6.0 | IBM MQ JMS client |

The dual ActiveMQ + IBM MQ library management reflects a heterogeneous messaging environment — some services use ActiveMQ (possibly cloud/modern path) while others continue to use IBM MQ (legacy/on-premises path).

## 6. Caching Libraries Managed

| Library | Version | Purpose |
|---|---|---|
| `net.sf.ehcache:ehcache` | 2.10.8 | Distributed/local in-process cache |
| `com.googlecode.ehcache-spring-annotations` | 1.2.0 | Spring AOP cache annotations for Ehcache |
| `swarmcache` | 1.0RC2 | Distributed SwarmCache (very old; likely legacy only) |

Ehcache 2.x is mature but reaching end-of-life. Spring Boot 3.x natively integrates with Caffeine (L1) and Redis (L2). Consider migration for new services.

## 7. ORM and Time Libraries Managed

| Library | Version | Notes |
|---|---|---|
| `joda-time` | 2.12.7 | Date/time; largely superseded by `java.time` in Java 8+ |
| `joda-money` | 1.0.4 | Currency/money arithmetic — important for payment amounts |
| `com.auth0:java-jwt` | 3.4.0 | JWT token generation/validation |

`joda-money` is architecturally significant: it provides `Money` and `CurrencyUnit` types that enforce monetary arithmetic correctness, preventing floating-point errors in payment calculations.

## 8. File Transfer Libraries Managed

| Library | Version | Notes |
|---|---|---|
| `commons-net` | 3.9.0 | FTP/FTPS client |
| `org.apache.sshd:sshd-core` | 2.13.0 | SFTP/SSH server and client |
| `org.apache.sshd:sshd-scp` | 2.13.0 | SCP protocol |
| `org.apache.sshd:sshd-sftp` | 2.13.0 | SFTP protocol (PCI DSS compliant file transfer) |
| `com.jcraft:jsch` | 0.1.55 | Legacy SSH/SFTP client |

**PCI DSS Note**: `sshd-sftp` (Apache MINA SSHD) is the recommended modern path for secure file transfer (Req 4.2). The legacy `commons-net` (FTP, unencrypted) and `jsch` (older SSH library) are retained for backward compatibility but should not be used for new CHD-containing file transfers.
