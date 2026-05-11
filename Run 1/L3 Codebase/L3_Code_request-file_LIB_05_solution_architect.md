# Solution Architect View — request-file_LIB

## API Surface

The library is a consumed JAR, not a service. Its API surface consists of:

**Primary entry point**:
- `RequestBuilder.createReqFile()` — marshals `PaymentData` to an XML file on disk
- `RequestBuilder.writeXMLToStream(OutputStream)` — marshals to any output stream

**Data population API**:
- `PaymentData` — aggregate data holder; populated via setters for `batchType`, `createAccReq`, `registration`, `reqFileType`, `reqList`, `fileName`
- `Cardtype` — card data; setters for `cardnumber`, `expmonth`, `expyear`, `cardtype`, `cvcode`
- `Requestfile`, `Batchtype`, `Request` — JAXB-annotated XML tree objects
- `ObjectFactory` — JAXB factory for creating XML schema objects
- Domain VOs: `AccountCreationVO`, `FundsAdditionVO`, `PaymentStopVO`, `SpinVO`, `BatchVO`, `RequestVO`

## Security Posture

### Critical Finding: CVV Marshalled to XML Without @XmlTransient

**File**: `requestfile-impl/src/main/java/com/ecount/payment/Cardtype.java`, lines 51–52

```java
@XmlElement(namespace = "http://www.ecount.com/")
protected String cvcode;
```

The `cvcode` field (CVV/CVC) in the `Cardtype` class is annotated with `@XmlElement`, which includes it in JAXB marshalling. When `RequestBuilder.writeXMLToStream()` marshals a `Requestfile` that includes a `Cardtype` with a populated `cvcode`, the CVV value is written in plaintext to the output XML.

Per PCI DSS Req 3.2.1:
> "Do not store sensitive authentication data after authorization. This applies even if there is no PAN in the environment."

The XML file written to disk by `RequestBuilder.createReqFile()` constitutes storage of SAD (CVV) in plaintext.

**The PCI DSS violation is conditional**: It occurs only if `Cardtype.setCvcode(String value)` is called with a non-null, non-empty value before `createReqFile()` is invoked. A full audit of all callers of `Cardtype.setCvcode()` in the consuming codebase is required to determine if this is a live violation.

**Remediation** (two options):
1. **Immediate**: Add `@XmlTransient` to the `cvcode` field — this suppresses JAXB marshalling of the field regardless of its value:
   ```java
   @javax.xml.bind.annotation.XmlTransient
   protected String cvcode;
   ```
2. **Schema removal**: If CVV is not required by the eCount processor for batch file processing (which it typically should not be — CVV is required only at point-of-sale authorization, not for batch disbursements), remove the `cvcode` field entirely from `Cardtype`.

### Secondary Finding: `e.printStackTrace()` in Production Code

**File**: `requestfile-impl/src/main/java/com/ecount/payment/common/RequestBuilder.java`, lines 53, 63

```java
} catch (Exception e) {
    e.printStackTrace();
    log.error("{}", e);
    reqFileStat.setStatus(RequestFileStatus.REQUEST_FILE_GEN_FAILED);
}
```

`e.printStackTrace()` writes the stack trace to `System.err` rather than through the SLF4J logger. In a containerized or application-server environment, `System.err` may not be captured by the structured log aggregation system. The `log.error("{}", e)` call immediately after does log via SLF4J, but the `e.printStackTrace()` is redundant and potentially writes sensitive exception data (including file paths, partial XML content in the stack trace) to uncontrolled output streams.

Additionally, the `os.close()` in the `finally` block has the same `e.printStackTrace()` pattern and swallows the exception by only setting a status:
```java
} catch (Exception e) {
    reqFileStat.setStatus(RequestFileStatus.REQUEST_FILE_GEN_FAILED);
    e.printStackTrace();
}
```
This means an I/O failure during stream close (e.g., incomplete file write) sets a failure status but does not re-throw, potentially leaving a partially-written XML file on disk that appears complete to the processor.

### XStream CVE Risk

**File**: `requestfile-impl/pom.xml`, dependency on `com.thoughtworks.xstream:xstream`

XStream has a documented history of critical Remote Code Execution vulnerabilities when deserializing untrusted XML input (CVE-2021-29505, CVE-2020-26258, CVE-2019-10173, and others). The specific version used (inherited from `prepaid-parent:6.0.12`) is unknown from the visible files. If XStream is used to deserialize any external or user-influenced XML in the consuming services, this is a critical vulnerability. Even if XStream is used only for object serialization (not deserialization of untrusted input), the library must be version-audited and kept patched.

## Technical Debt

1. `@XmlElement` on `cvcode` — must be `@XmlTransient` (PCI DSS Req 3.2.1 risk)
2. `e.printStackTrace()` — replace with SLF4J logging throughout
3. XStream dependency — audit version and usage pattern; migrate to Jackson or JAXB-only if possible
4. `com.sun.xml.bind:jaxb-*` — migrate to `org.glassfish.jaxb:*` (standard Jakarta EE artifacts)
5. `commons-lang:commons-lang` — migrate to `org.apache.commons:commons-lang3`
6. No unit tests for the marshalling path — `RequestBuilderTest.java` exists but its coverage of the `cvcode` marshalling scenario is unknown

## Code-Level Findings Summary

| Finding | File | Line | Severity |
|---|---|---|---|
| `cvcode` (CVV) marshalled to XML via `@XmlElement` | `Cardtype.java` | 51–52 | Critical — PCI DSS Req 3.2.1 |
| `cardnumber` (PAN) marshalled to XML in plaintext | `Cardtype.java` | 43–44 | High — PCI DSS Req 3.3 |
| `e.printStackTrace()` in production error handling | `RequestBuilder.java` | 53, 63, 64 | Medium |
| Partially-written file risk on close exception | `RequestBuilder.java` | 61–64 | Medium |
| XStream dependency with CVE history | `pom.xml` | xstream dependency | High — CVE risk |
| `com.sun.xml.bind:jaxb-*` legacy artifacts | `pom.xml` | jaxb dependencies | Low |
| No `@XmlTransient` on any SAD field | `Cardtype.java` | all fields | Critical |
