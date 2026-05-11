# actimize-kyc_LIB — Enterprise Architect View

## Platform Generation (Gen-1/Gen-2/Gen-3)

**Classification: Gen-1**

Evidence supporting this classification:

| Indicator | Evidence |
|---|---|
| Java 6 runtime | Keytool instructions reference `D:\c-base\opt\jdk1.6.0_16` |
| JAX-WS RI 2.1.2-hudson-182-RC1 | Comment in `KycCheckServiceSIT.wsdl` line 1 — this version shipped with Java 6 (2008 era) |
| Apache XmlBeans 2.5.0 | Released 2008; vendored in-repo; project archived by Apache |
| Apache Ant build | No Maven POM, no Gradle; pure Ant with hardcoded Windows paths |
| Manual deployment via text files | `deploy kycbean jar to repository.txt`, `keytool security cer add.txt` |
| Internal Nexus at `ecsvn.office.ecount.com` | Old eCount-era Maven repository; plain HTTP |
| Binary JARs in Git | Two copies of `KycCheckServiceXmlBeans.jar` committed to version control |
| `ecountcore` database prefix | All SQL scripts target `ecountcore` — the legacy eCount Core platform database |
| Single static version (1.0) | No semver, no SNAPSHOT lifecycle |
| No CI/CD | Zero pipeline artefacts |

This library is a pre-cloud, pre-containerisation, monolithic-era shared library from the eCount platform generation, developed approximately 2008–2012.

## Business Domain

**Domain: Identity & Compliance — KYC / AML / CIP / CDD**

The library sits at the intersection of two Onbe business domains:
1. **Identity Verification (CIP)**: Verifying the identity of new customers using SSN + biographic data against authoritative sources (Actimize/Fortent CIP engine).
2. **Risk Screening (CDD / AML)**: Screening customers against watchlists (OFAC SDN, PEP lists, government sanctions) to fulfil Customer Due Diligence obligations under BSA.

As a library (not a service), it does not own the domain logic — it provides the typed API client that enables other components to interact with the Actimize KYC platform.

## Role in Platform

`actimize-kyc_LIB` plays the role of a **shared infrastructure library** — specifically, a compiled SOAP client stub generated from the Actimize KYC service WSDL/XSD contract. Its role in the platform is:

- **Dependency for KYC-initiating services**: Any Onbe/eCount application that needs to trigger a KYC check, retrieve a risk score, or query watchlist results must include this library as a Maven dependency.
- **Schema authority**: The `KycCheckService.xsd` embedded in (and used to generate) this library is the canonical definition of the KYC API contract between Onbe and the Actimize platform.
- **Credential carrier**: The `kyc_profile` SQL scripts seed the database record that tells consuming services which endpoint URL and credentials to use per environment.

The library does not orchestrate multi-step KYC workflows, does not own the KYC check lifecycle, and does not store KYC results. It is a thin, typed integration layer.

## Dependencies

### Upstream Dependencies (what this library depends on)
| Dependency | Type | Detail |
|---|---|---|
| NICE Actimize KYC Service (Fortent) | External SOAP service | `*.nam.nsroot.net:8181/kycapp/KycCheckService`; all three environments on private network |
| `ecountcore` SQL Server database | Database | Table `kyc_profile` — endpoint URL and credentials |
| JVM `cacerts` truststore | Infrastructure | Must contain imported `servercert.bin` per environment |
| Apache XmlBeans 2.5.0 (`xbean.jar`) | Build-time library | Vendored in repo; required only for rebuild |
| JDK 1.6 (`jsr173_1.0_api.jar`) | Build-time library | XML streaming API JAR for XmlBeans compilation |
| Internal Maven repo (`ecsvn.office.ecount.com`) | Artifact repository | For deployment of the compiled JAR |

### Downstream Dependencies (what depends on this library)
Not determinable from this repository alone. Any service in the Onbe/eCount platform that performs KYC checks will declare:
```xml
<dependency>
  <groupId>actimizekyc</groupId>
  <artifactId>actimizekyc</artifactId>
  <version>1.0</version>
</dependency>
```
The Maven groupId inconsistency (deploy uses `com.ecount.actimizekyc`, dependency snippet uses `actimizekyc`) means there may be two different published versions of the artifact, or consumers may need to reference either groupId depending on how/when it was published.

## Integration Patterns

**Pattern: RPC-style SOAP over HTTPS (WS-I Basic Profile)**

- Transport: SOAP 1.1 over HTTP/S (`http://schemas.xmlsoap.org/soap/http`)
- Style: Document/Literal (`<soap:binding style="document">`, `<soap:body use="literal">`)
- Authentication: HTTP Basic or service-specific credentials supplied via `secure_id`/`secure_code` from `kyc_profile` table
- TLS: Server-certificate-based mutual authentication using manually managed JVM truststore
- Schema binding: Apache XmlBeans 2.5.0 generates Java types from XSD — caller constructs request objects, serialises to SOAP XML, sends via JAX-WS RI stub

**Batch pattern**: `initiateBatch` accepts file contents as a base-64 string payload, suggesting a file-based bulk-screening integration upstream of the SOAP call.

**Polling pattern**: `getRiskCategoryChanges` accepts `since`/`until` date-time range — the consuming application is expected to periodically poll for changes rather than receive push notifications.

**No async/event-driven patterns**: The entire API is synchronous request-response. There is no JMS, Kafka, message queue, webhook, or callback mechanism.

## Strategic Status

**Status: LEGACY — Maintenance-only; migration candidate**

- The Actimize/Fortent platform being integrated was acquired by NICE Systems and is a mature (2000s-era) AML/KYC platform. Fortent was rebranded into NICE Actimize.
- The library version has been frozen at `1.0` with no evidence of active development.
- All tooling (Java 6, XmlBeans 2.5.0, Ant, JAX-WS RI 2.1.2) is EOL.
- The eCount-branded Maven repository (`ecsvn.office.ecount.com`) and the `ecountcore` database prefix indicate this predates Onbe's rebranding and current platform.
- There is no documented owner, roadmap, or lifecycle plan for this library.

Strategic risk: Any change to the Actimize KYC service contract (XSD/WSDL update, endpoint migration, authentication change) would require a full manual rebuild of this library and re-deployment to all consuming services — with no automated pathway to do so.

## Migration Blockers

| Blocker | Severity | Detail |
|---|---|---|
| Java 6 build dependency | HIGH | `build.xml` hardcodes `D:\c-base\opt\jdk1.6.0_16`. Migration requires rebuilding with Java 11+ and updating the XmlBeans/JAXB binding approach. |
| XmlBeans 2.5.0 EOL | HIGH | Cannot be used with modern Java without compatibility shims. JAXB or a modern code generator (e.g., `wsimport`, `openapi-generator`) must replace it. |
| Hardcoded filesystem paths in `build.xml` | HIGH | Cannot build in any CI/CD system or on any machine without `D:\c-base\` path structure. |
| Binary JAR in Git | MEDIUM | No source code is available in this repo for the compiled classes. Source must be located or the JAR reverse-engineered before migration. |
| Manual truststore management | MEDIUM | Certificate chain for `*.nam.nsroot.net` is managed via manual `keytool` operations. Migration to a modern secrets/cert management system (Vault, AWS ACM) required. |
| Plaintext credential in SQL | HIGH | `secure_code = 'Prepaid1'` in three committed SQL files must be rotated and replaced with vault-managed secrets before any migration or new deployment. |
| SOAP-only API contract | MEDIUM | The Actimize KYC service exposes only SOAP. If Onbe migrates to a REST/JSON API platform (Gen-3), either the Actimize service must expose REST, or an adapter/anti-corruption layer is required. |
| Single version, no semver | LOW | Consuming services pin to `version=1.0`. A migration to a new library version requires coordinated updates across all consumers. |
| `ecountcore` database coupling | MEDIUM | The `kyc_profile` table lives in the legacy `ecountcore` database. Migration requires extracting this configuration into a Gen-3 config store (Kubernetes ConfigMap, Parameter Store, etc.). |
| Internal `.nam.nsroot.net` network dependency | MEDIUM | All endpoints are on an internal corporate network. Cloud or hybrid deployments require network connectivity or API gateway abstraction. |
