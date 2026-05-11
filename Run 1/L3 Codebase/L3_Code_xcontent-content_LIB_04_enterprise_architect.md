# xcontent-content_LIB — Enterprise Architect View

## Platform Generation
**Gen-1** — Definitively legacy.

Evidence:
- Spring 1.2.7 (released 2006) — oldest Spring version in the entire estate
- Lucene 2.0.0 (released 2006)
- Java 1.5 compile target
- JUnit 3.8.1 (pre-annotations; 2002 era)
- Servlet API 2.4 (J2EE 1.4 era)
- Jetty 6 development server
- Wirecard SCM URL (`gitlab.wirecard-cloud.com`)
- Spring 2.x DTD-based bean definitions
- Version `2.0.0-SNAPSHOT` has never been promoted to a release — suggests the library is in a perpetual draft state
- `master` branch (old convention)

## Business Domain
**Content Management — Lucene Library Component**

This library provides the Lucene indexing and content search infrastructure for the Gen-1 xContent service. It is a shared library component, not an independently deployable service.

## Role in Platform
- **Dependency of xcontent_SVC**: The current `xcontent_SVC` has inherited and modernized the application context from this library; this library may still be a transitive dependency
- **Original Gen-1 content management core**: The classes `com.ecount.one.lucene.EcountIndex`, `com.cdbaby.lucene.LuceneIndex`, `com.cdbaby.utils.CMSContext`, `com.cdbaby.utils.CreatePropertyIndex` define the core content management capability
- **No active consumers visible** other than `xcontent_SVC`

## Dependencies
**Inbound consumers:**
- `xcontent_SVC` (consumes `EcountIndex`, `CMSContext` classes via dependency)

**Outbound calls:**
- Filesystem (read only) — no network dependencies

## Integration Patterns
- **Library pattern**: Consumed as a JAR/WAR dependency by the host service
- **Spring XML context**: Bean definitions in `CMSApplicationContext.xml` imported or merged by host application context
- **No network integration**: Pure filesystem + in-memory index

## Strategic Status
**Retire / Superseded**

- `xcontent_SVC` contains a modernized copy of the core application context (using Spring 5.x schemas, Java 21, environment variables)
- This library represents the original Wirecard-era Gen-1 implementation that `xcontent_SVC` was created to replace/modernize
- Should be retired once `xcontent_SVC` completes its dependency cleanup or `xcontent_SVC` is replaced by a Gen-3 content delivery solution
- No evidence of active development; `2.0.0-SNAPSHOT` version has not progressed to release

## Migration Blockers
1. **Source dependency**: `xcontent_SVC` and possibly other services depend on compiled classes from this library (`com.ecount.one.lucene.*`, `com.cdbaby.*`); migration requires either inlining the code or replacing the entire content delivery mechanism
2. **No release artifact**: `2.0.0-SNAPSHOT` means there is no stable artifact version; CI must resolve from the snapshot repository
3. **`com.cdbaby.*` package provenance**: These classes appear to be a third-party adaptation of an ancient open-source Lucene integration; original source may not be available and cannot be upgraded without a full rewrite
4. **Spring 1.2.7**: Cannot be migrated to Spring Boot 3.x without complete rewrite; incompatible API, bean definition syntax, and transaction management
