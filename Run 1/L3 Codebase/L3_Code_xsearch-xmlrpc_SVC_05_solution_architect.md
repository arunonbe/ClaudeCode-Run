# xSearch XML-RPC SVC — Solution Architect / Security View

## 1. Security Architecture Overview

xSearch XML-RPC is a high-value target from an adversarial perspective: it provides authenticated lookup of cardholder PAN, name, and address data across the entire Onbe prepaid platform. Its security architecture must be evaluated with the understanding that a successful attack could expose large volumes of cardholder data in a single automated sweep.

This section documents the actual implemented security controls, their gaps, and specific file/line references.

## 2. Authentication and Authorization — Critical Finding

### What Exists
The XML-RPC protocol used by xSearch has **no built-in authentication mechanism**. The only identity parameter passed in requests is the `agent` string (e.g., `B2CTEST`), which is a platform routing/context identifier, not an authentication credential.

In `XSearchProxy.java` (line 54), the `find()` call passes `input.getAgent()` as the first parameter. In `XSearchXMLRPCClient.java` (line 30-31), the agent is set at client construction time — it is a configuration value, not a per-request credential.

**There is no evidence in the codebase of:**
- Session token validation on incoming XML-RPC requests
- API key or client certificate authentication
- OAuth2 token verification
- IP allowlisting at the application layer (may exist at network/WAF layer, but not in code)

### Implication
Any network-reachable entity that can construct a valid XML-RPC `FindMemberByMobilPhone` request with a known agent string can query xSearch. The `RPC_INTERFACE_NAME = "xSearch.xSearch"` and `RPC_FIND_METHOD_NAME = "FindMemberByMobilPhone"` values are constants visible in the compiled JAR and published client library. If the xSearch service is accessible from a non-trusted network segment, this represents a critical CDE boundary violation under PCI DSS Req 7 and Req 8.

**Recommendation:** Verify that xSearch is isolated to an internal network segment and that network-level controls (firewall rules, security groups) are the actual authentication boundary. Document this as a compensating control if mTLS or application-level auth cannot be added in the near term.

## 3. What Data a Lookup Returns — PCI DSS Critical Assessment

### PAN Exposure Risk
`MemberInquiryValue.java` contains a `cardNumber` field (line 15) with a public `getCardNumber()` getter (line 59-61) that returns the raw value. The `getCardNumberMasked()` getter (line 75-77) exists as an alternative. Whether the raw or masked value appears on the XML-RPC wire depends entirely on which getter the EMember implementation and the XML-RPC serialization framework uses.

**The risk:** If the XML-RPC serializer reflects all JavaBean properties (which is the standard behavior for most XML-RPC frameworks), both `cardNumber` and `cardNumberMasked` are serialized and transmitted. The response consumer receives the raw PAN.

Under PCI DSS Req 3.3.1, the primary account number (PAN) must be rendered unreadable anywhere it is stored. PAN transmitted over the network falls under Req 4 (protect PAN in transit with strong cryptography). If xSearch is operating over plain HTTP internally (no TLS), every mobile-phone lookup that returns a record exposes a PAN in cleartext on the internal network.

### SSN Exposure Path
`MaskCCHelper.maskThisSSN()` (line 122-152) provides SSN masking, indicating that SSN values flow through the platform search infrastructure. While SSN is not a field in `MemberInquiryValue`, it may be present in the underlying `EMember` implementation's database query results. The existence of `maskThisSSN()` in the shared common module is a strong indicator that SSN data is accessible through the search infrastructure in some configurations.

### Mobile Phone in Logs — PII Risk
`XSearchProxy.java` lines 43-45 log the mobile phone number at INFO level:
```java
logMessage.append(" MobilePhone = " + input.getMobilePhone());
log.info(logMessage.toString());
```
Mobile phone numbers are PII under CCPA/GDPR. Logging them without masking creates a PII exposure in log aggregation systems (Elasticsearch/Logstash/Kibana). Recommended fix: mask the middle digits before logging (e.g., log only last 4 digits).

## 4. Input Validation

No input validation is visible in the XML-RPC layer for the `FindMemberByMobilPhone` operation. The `mobilePhone` string is passed directly through the proxy to the EMember implementation. The EMember implementation (in the ecount-system dependency) is responsible for any sanitization. If the underlying stored procedure uses dynamic SQL rather than parameterized queries, this creates an SQL injection risk on the mobile phone search path. The stored procedure approach (as suggested by the `StoredProcedure` subclasses in `xsearch-impl`) provides parameterization for all queries that go through Spring JDBC stored procedure wrappers, which mitigates injection risk for those paths.

## 5. Dependency Vulnerabilities

| Dependency | Version | Known Risk Category |
|---|---|---|
| Apache Commons HttpClient | 3.x (implied) | EOL; multiple historical CVEs |
| Apache XML-RPC | 3.0.2 (via `xmlrpc:3.0.2`) | Legacy; no active maintenance |
| `commons-discovery:0.2` | 0.2 | Very old; EOL |
| `commons-logging:1.1.1` | 1.1.1 | Old; patched versions available |

The Trivy scan configuration (`.trivyignore`) may be suppressing alerts for these libraries. The security team should review `.trivyignore` contents and ensure no critical/high CVEs are suppressed without documented business justification.

## 6. Hardcoded Business Logic in Security-Adjacent Code

`MaskCCHelper.java` contains:
- BIN `514977` hardcoded as the Galileo account BIN check (line 66). If Galileo BINs change, the code silently produces incorrect results.
- Private label BINs `44815619` and `448184` (lines 95-96). These are card program BINs that should be configuration-driven, not embedded in source code.

Hardcoded BINs in a masking utility are a compliance risk: if a card program adds a new BIN range, the masking logic may fail to apply the correct handling, potentially leading to unmasked PAN being returned.

## 7. API Surface and Attack Surface

The XML-RPC servlet (`XSearchXmlRPCServlet`) is mapped to `/*` or equivalent (the specific URL mapping depends on the WAR deployment descriptor, which was not reviewed). The `IXSearchProxy` interface exposes:
- `FindMemberByMobilPhone` — the only currently implemented operation in the XML-RPC server

The full `EMember` interface (24-parameter `find()` methods) is exposed to internal Java callers via the client library. The XML-RPC protocol limits the remote attack surface to `FindMemberByMobilPhone`, but internal service-to-service calls using the client library have broader access.

## 8. PCI DSS Req 6 — Secure Development

| PCI DSS Req | Status |
|---|---|
| 6.2.4 — Prevent common vulnerabilities | Partial — stored procedures mitigate SQLi; input validation absent at RPC layer |
| 6.3.3 — Security patching | At risk — EOL dependencies in use |
| 6.4.1 — WAF for public-facing web apps | Unknown — WAF presence depends on infrastructure, not documented in code |
| 6.5 — Change management | PACT contract testing present but provider verification disabled |

## 9. Remediation Recommendations

**Critical (address before next audit):**
1. Implement application-level authentication on the XML-RPC endpoint (client certificate or API key validation in `XSearchXmlRPCServlet`)
2. Verify that `MemberInquiryValue.cardNumber` is never transmitted in raw form over the XML-RPC wire; enforce masking at serialization time
3. Confirm xSearch is not network-reachable from untrusted segments; document network controls as compensating controls if present

**High:**
4. Remove mobile phone number from INFO-level logs; apply last-4-digit masking before logging
5. Upgrade or replace Apache Commons HttpClient 3.x and the Apache XML-RPC 3.0.2 library
6. Enable provider-side PACT verification (`VERIFY_PROVIDER_PACT: true`) and remove `-Dmaven.test.skip` from CI

**Medium:**
7. Replace hardcoded BIN values in `MaskCCHelper.java` with configuration-driven lookups
8. Add XML-RPC input validation and sanitization in the servlet layer
9. Review `.trivyignore` suppressions and document justifications for each suppressed CVE
