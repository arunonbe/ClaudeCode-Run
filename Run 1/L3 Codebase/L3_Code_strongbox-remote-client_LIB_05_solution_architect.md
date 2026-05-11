# Solution Architect Report: strongbox-remote-client_LIB

## API Surface

This is a library; its "API surface" is the Java interface `IStrongboxRemoteService`:

```java
String writeObject(Object o, WriteMapXmlRemoteCall writeObjectRemoteCall)
String writeMap(Map<String, Object> map, WriteMapXmlRemoteCall writeObjectRemoteCall)
Map<String, Object> readMap(String reference, ReadMapXmlRemoteCall readMapXmlRemoteCall)
Object readObject(String reference, Object target, ReadMapXmlRemoteCall readMapXmlRemoteCall)
```

All methods throw `StrongBoxServiceException`. The library is consumed programmatically by other services — no HTTP endpoints are exposed.

## Security Posture

**High risk — handles most sensitive data with outdated security posture.**

The library is responsible for transporting the platform's most sensitive material (cryptographic keys, passphrases) using a pattern with multiple security weaknesses:

1. **Secrets handled as Java Strings**: PGP passphrases, symmetric key values, and private key material returned by `readMap`/`readObject` are returned as `Map<String, Object>` values — in practice, Strings. Java Strings cannot be zeroed from memory; secrets remain on the heap until GC collects them, accessible in heap dumps
2. **Unverified deserialisation**: `XmlRPCToObjectMapper.toObject(mapXml, target, logger)` deserialises XML-RPC responses into Java objects. XML-RPC deserialisation is subject to the same class of vulnerabilities as Java object deserialisation; if the StrongBox server or the network path is compromised, a malicious XML-RPC response could be used for exploitation
3. **No audit logging**: The library logs nothing at security-relevant events (successful secret read, failed read, connection error). The placeholder logger name `"SomeLoggerClassName"` (`StrongBoxRemoteServiceImpl.java`, line 23) means even generic log messages would not be attributable to this library

## Critical Findings

1. **EOL Spring Framework 4.3.27** (`pom.xml`, line 37):
   - Spring 4.x EOL since December 2020; known CVEs include Spring4Shell (CVE-2022-22965)
   - As a library, this version propagates into consuming services' dependency tree unless they explicitly override it; consuming services must check for this transitive dependency

2. **Java 8 compile target** (`pom.xml`, lines 74–75):
   - `<source>8</source>`, `<target>8</target>` — Java 8 EOL (Oracle), no recent security patches available for all distributions
   - Java 8 uses older TLS defaults (TLS 1.0/1.1 may be enabled); Java 11+ defaults to TLS 1.2 minimum

3. **Placeholder logger name** (`StrongBoxRemoteServiceImpl.java`, line 23):
   - `LogFactory.getLog("SomeLoggerClassName")` — clearly a development placeholder never corrected
   - Security events from this class will be invisible in log analysis and SIEM rules that filter by class name
   - PCI DSS Requirement 10 requires audit trails; a broken logger breaks the audit trail

4. **SNAPSHOT dependency** (`pom.xml`, line 33):
   - `<xmlrpc.version>2.0.0-SNAPSHOT</xmlrpc.version>` — snapshot dependency on an internal Citi-era XML-RPC library
   - Build is non-reproducible; the snapshot artifact version at build time depends on the last published snapshot to the (now likely defunct) Wirecard Nexus
   - Maven build may silently fail or use a stale cached snapshot

5. **Legacy Nexus distribution URL** (`pom.xml`, lines 20–28):
   - `http://d-na-stk01.nam.wirecard.sys:8080/nexus/` — HTTP (not HTTPS) distribution to the old Wirecard Nexus server
   - If the Nexus is still accessible, artifacts are published without transport encryption; if it's not accessible, this library cannot be published at all via the configured mechanism

## Technical Debt

- **No null safety**: `StrongBoxRemoteServiceImpl` performs no null checks on the inputs to its public methods; a null `reference` or null `readMapXmlRemoteCall` will cause a `NullPointerException` rather than a meaningful `StrongBoxServiceException`
- **Raw type usage**: `readObject` returns `Object` rather than a generic `<T>` return type; callers must cast unsafely
- **No retry logic**: The library provides no retry mechanism; transient network failures to the StrongBox service cause immediate exception propagation. Retry responsibility is on the caller's lambda implementation
- **`1.0.0-SNAPSHOT` version**: The library has never had a release version; this suggests it has been in a perpetual "draft" state, never formally released and reviewed
- **Apache Commons Logging**: Uses `org.apache.commons.logging.Log` (Spring's preferred facade) rather than SLF4J; this is inconsistent with modern Spring services that use SLF4J uniformly and creates potential double-logging or configuration issues in consumers that use SLF4J/Logback
