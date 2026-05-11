# DevOps / Operations View — xplatform-library_LIB

## Build System
- **Language / Framework:** Java 21, Maven
- **Parent POM:** `com.parents:prepaid-parent:6.0.13`
- **Artifact:** `com.ecount:xplatformlibrary:4.2.0` (JAR)
- **Compiler target/source:** Java 21
- **Source encoding:** `Windows-1252` (explicitly set in POM — legacy; not UTF-8)
- **Build command:** `mvn clean install -Dmaven.test.skip`
- **Plugins:** `maven-jar-plugin`, `maven-enforcer-plugin` (bans transitive dependencies)
- **Note:** No JaCoCo coverage plugin configured at this level (unlike xplatform_LIB)

## Deployment
- **Deployment model:** Published as a JAR to a Maven repository; consumed as a compile-time dependency
- **Not directly deployed** — infrastructure library only
- **Required by:** `xplatform_LIB` (`xplatformlibrary 4.2.0`) and transitively by all platform services
- **Runtime environment:** JVM 21; Tomcat 10.x (when used in a servlet context)

## Configuration Management
- No externalised configuration specific to this library — configuration is provided by calling code
- `ConfigurationFile` and `ConfigDB` are configuration-loading utilities, not self-configuring
- `RPCTimeout.properties` on the classpath controls RPC timeout behaviour; defaults to internal values if not present (fixed in v4.1.0)
- No in-repo secrets

## Observability
- Custom `SystemLog` / `SystemLogger` framework — not SLF4J / Log4j2 compatible without bridging
- `SwarmCache` via JGroups — JGroups provides its own diagnostic logging
- No JaCoCo, no metrics, no health endpoint
- `CacheManager` provides `getCacheNames()` iterator — basic introspection only

## Infrastructure Dependencies
| Dependency | Version | Notes |
|---|---|---|
| request-context | 2.1.0 | `com.citi.prepaid.module` — Citi-branded request context module |
| swarmcache | Managed | JGroups-based distributed cache (excludes commons-collections, commons-logging) |
| oro | Managed | Apache ORO regex library (legacy, dormant project) |
| regexp | Managed | Another legacy regex library |
| jsafe | Managed | RSA Data Security Jsafe commercial crypto SDK |
| jakarta.servlet-api | Managed (provided) | Servlet API |
| spring-context | Managed | Spring IoC |
| commons-text | Managed | Apache Commons Text |
| commons-pool2 | 2.11.1 | Apache Commons Pool (for SaxParserFactoryPool) |

## Operational Risks
- **`Windows-1252` source encoding** — hardcoded in POM; non-standard for a Java library intended for multi-platform deployment; risk of character encoding issues when building on Linux/Mac CI runners
- **SwarmCache (JGroups multicast)** — multicast-dependent; incompatible with most container network overlays (Kubernetes, Docker bridge networks) without explicit configuration
- **ORO regex library** (`oro`) — Apache project marked "dormant" since 2010; unmaintained; potential for unpatched regex vulnerabilities
- **Jsafe SDK** — commercial legacy crypto library; no public CVE feed; FIPS certification status unknown
- **`request-context` from `com.citi.prepaid.module`** — Citi-branded internal module; provenance and update cadence unclear for an Onbe-operated library
- **`maven.test.skip` default** — tests are routinely skipped; library correctness (especially cryptographic operations) cannot be assumed from CI

## CI/CD
- No GitHub Actions workflow files in this repository
- Expected to follow the central `om-ci-setup` Maven workflow
- Version `4.2.0` is a release version (not SNAPSHOT) — better than xplatform_LIB's SNAPSHOT state
- Change log present in README (v4.1.0, v4.2.0) — version discipline is improving
