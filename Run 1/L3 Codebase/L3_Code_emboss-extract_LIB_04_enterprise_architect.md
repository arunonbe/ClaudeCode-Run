# 04 Enterprise Architect — emboss-extract_LIB

## Platform Generation

`emboss-extract_LIB` is a **Generation 0 / Generation 1** component — the oldest tier of the Onbe/EcountCore platform. Evidence:

- Java compiler target is **1.5** (Java 5, released 2004)
- Spring Framework **2.0** (released 2006, unsupported)
- Log4j **1.2.8** (released circa 2004, severely outdated even relative to the later 1.2.15 used by `ecount-host-log4j_LIB`)
- JUnit **3.8.1** (pre-annotations test framework, 2004 era)
- No parent POM — predates the standardised Onbe Maven parent hierarchy
- Binary JARs checked into `lib/` — a practice abandoned in later generations

This library was almost certainly written in the 2006–2009 timeframe and has not been materially updated since.

## Role in Platform Architecture

```
┌───────────────────────────────────────────────────────────────┐
│              Onbe Prepaid Card Platform                       │
│                                                               │
│  ┌──────────────────────┐                                     │
│  │  Job Scheduler       │  (Control-M / cron)                 │
│  │  (runs nightly)      │                                     │
│  └──────────┬───────────┘                                     │
│             │  java -cp embossExtract.jar Extractor {vendorId}│
│             ▼                                                 │
│  ┌──────────────────────┐                                     │
│  │  emboss-extract_LIB  │  (this repo)                        │
│  │  Extractor.main()    │                                     │
│  └──────────┬───────────┘                                     │
│             │                                                 │
│     ┌───────┴──────────────────────────┐                      │
│     │                                  │                      │
│     ▼                                  ▼                      │
│  SQL Server                     Local Filesystem              │
│  (dbo.core_process_*            /upload/EmbossFileExtract/    │
│   emboss_queue_extract)         {VendorName}_{timestamp}.xml  │
│                                          │                    │
│                                          ▼                    │
│                                 NDM / Connect:Direct          │
│                                 (to card bureau)              │
└───────────────────────────────────────────────────────────────┘
```

The library sits at the **cardholder data egress boundary** — it is the point at which PANs leave the Onbe SQL Server environment and are formatted for transmission to an external card bureau. This makes it one of the most PCI-sensitive processes in the platform.

## Integration Dependencies

| Dependency | Version | Status |
|---|---|---|
| `spring:2.0` | Gen-0 Spring | End-of-life since 2009 |
| `log4j:1.2.8` (lib/) | Gen-0 logging | Critical CVEs |
| `jtds:1.2` | Gen-1 JDBC | Unmaintained |
| `xerces:2.8.1` | Gen-0 XML | Outdated |
| EcountCore DB stored procedures | Gen-1 | `dbo.core_process_emboss_*` |
| NDM (external) | Gen-0 file transfer | External dependency |

## Card Bureau Integration Model

The library produces XML files consumed by card bureaus in the `http://www.ecount.com/` namespace. Each bureau (FDR, PSX, METACA, ARROWEYE, CITI-NAOT) presumably has its own ingestion pipeline that processes these files. The XML schema is proprietary to Onbe/EcountCore.

**No formal interface contract** (no XSD, no OpenAPI spec) is documented in the repository. The XML structure is entirely implicit in the `StaxEmbossExtractBuilder.createRequestNode()` method.

## Migration Complexity

| Migration Scenario | Effort | Risk |
|---|---|---|
| Upgrade Spring 2.0 → Spring 6.x / Spring Boot 3 | Very High | Spring XML bean definitions would need to be replaced with annotations/Java config |
| Replace Log4j 1.2.8 with Logback / Log4j 2 | Medium | Log4j 1.x API is different; appenders need rewriting |
| Replace jTDS with mssql-jdbc | Medium | Connection string format changes |
| Add PAN encryption before file write | High | Requires HSM or PGP library integration; bureau must accept encrypted format |
| Replace XML output with bureau-specific format (e.g., ISO 8583, fixed-length) | Very High | Requires bureau-by-bureau renegotiation |
| Move credentials out of property files | Medium | Requires integration with Azure Key Vault or Director |
| Containerise the batch job | High | Requires Spring Boot migration first |

## Strategic Recommendation

This library should be **retired and rebuilt** as a modern Spring Batch or cloud-native batch job. The immediate priorities for compliance are:

1. **Remove hardcoded credentials from source control** (Days 1–5)
2. **Encrypt the output file** (PGP or HSM) before writing to disk (Sprint 1)
3. **Upgrade Log4j** to a supported version (Sprint 1)
4. **Pin to a release version** and establish a proper CI/CD pipeline (Sprint 2)

Long term: migrate to a Spring Batch job with Azure Key Vault for credentials, structured JSON logging, and SFTP (TLS 1.2+) direct bureau integration, replacing the NDM dependency.
