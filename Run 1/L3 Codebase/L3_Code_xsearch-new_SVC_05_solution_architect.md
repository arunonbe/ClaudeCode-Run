# Solution Architect View — xsearch-new_SVC

## Technical Architecture
- **Language:** Java; compiler version set by parent POM `service-parent:6` (not visible in this repo — likely Java 8 or 11 based on Servlet 2.5 usage)
- **Build:** Maven multi-module; Maven wrapper present
- **Packaging:** xSearch-xmlrpc builds a WAR; others build JARs
- **Architecture style:** XML-RPC service over HTTP; Spring 2.5 XML application context wiring
- **Module layout:**
  - `xSearch-common` — shared value objects (MemberInquiryValue, DevicesInquiryValue, EMember, MaskCCHelper)
  - `xSearch-client` — XML-RPC client (`XSearchXMLRPCClient`, `XSearchXMLRPCClientUtils`, `IXSearchServiceLocationResolver`)
  - `xSearch-impl` — full implementation (mirrors xsearch_LIB + PudInquiry, MemberByPlasticOnlyCard, MemberByPUIDPlasticOnlyCard, MemberInquiryByPUID, SearchDeviceByMemberId)
  - `xSearch-xmlrpc` — WAR containing `XSearchXmlRPCServlet`, Spring contexts, web.xml

## API Surface
XML-RPC method calls over HTTP POST to `/*`:
- All methods exposed via Spring-registered beans in `xmlrpcImplContext.xml` (not directly readable but inferred from proxy classes)
- `IXSearchProxy` — proxy interface defining the XML-RPC operation contract
- `XSearchProxy` — implementation delegating to Spring application context beans
- Explicit new method: `FindMemberByMobilPhone` (input/output classes in both client and xmlrpc modules)
- XML-RPC client endpoint resolved via `IXSearchServiceLocationResolver` / `SimpleXSearchServiceLocationResolvingCache`

## Security Posture

### Authentication
- **None detected at the service level.** The `web.xml` has no security constraints, no authentication filters, and no servlet security declarations.
- Access control depends entirely on network-level controls (firewall, VPN, private network segment)
- `XSearchXMLRPCClient` takes a URL parameter — any client with connectivity can make calls

### Transport Security
- XML-RPC over HTTP — plaintext unless TLS is terminated at a load balancer or reverse proxy
- PAN, SSN, member data, and phone numbers are transmitted in XML in the clear if TLS is not applied
- No mutual TLS (mTLS) for service-to-service authentication

### Data Masking
- `MaskCCHelper` in xSearch-common is identical to the version in xsearch_LIB
- **Same PCI DSS non-compliant masking** (first 4 + last 4 instead of first 6 + last 4)

### XML-RPC Security
- XML-RPC messages are XML — XXE (XML External Entity) injection is a risk if the XML parser is not hardened
- The `XSearchXmlRPCServlet` delegates to `XmlRPCServlet` (internal xmlrpc framework `1.0.9`) — the XXE configuration of this internal servlet is not visible in this repo

### CVE Exposure
- **Spring 2.5.4** (root POM) — EOL; multiple high-severity CVEs including Spring4Shell-era vulnerabilities. If this version is actually on the classpath, it is a critical security finding.
- **`javax.servlet` imports** in `XSearchXmlRPCServlet.java:7` — confirms this module is compiled against `javax.servlet` (not `jakarta.servlet`), which means it requires Tomcat 9 or earlier; incompatible with Tomcat 10+
- **junit 4.4** (test) — very old JUnit; CVE exposure exists but test-scope only
- **Spring mock 2.0.4** (test) — very old test framework

## Technical Debt
| Item | Severity | Detail |
|---|---|---|
| Spring 2.5.4 in root POM | Critical | EOL 2009; multiple known CVEs; runtime version must be confirmed from effective POM |
| `javax.servlet` imports | Critical | `XSearchXmlRPCServlet.java:7` — incompatible with Tomcat 10 / Jakarta EE; blocks container modernisation |
| No authentication on XML-RPC endpoint | Critical | Any network-reachable service can query PAN/SSN data without credentials |
| Hardcoded Log4j path in web.xml | High | `file:///d:/c-base/config/xSearch-xmlrpc/log4j.xml` in `web.xml:35` — breaks all non-developer deployments |
| `xPlatform 2014.1.1` in root POM | High | 2014-vintage version; major version mismatch with current 6.x xplatform_LIB |
| XML-RPC protocol | High | Legacy protocol; no standard security controls, no observability tooling |
| PAN masking non-compliant | High | Same as xsearch_LIB — inherited into xSearch-common |
| Log4jConfigListener (deprecated) | Medium | Spring's Log4j config listener deprecated since Spring 3.x |
| `javax.servlet.http` in XmlRPCServlet | High | Namespace incompatibility with modern Tomcat |
| No deployment workflow | Medium | No GitHub Actions deployment; release process unclear |

## Gen-3 Migration Requirements
1. Replace XML-RPC with a REST API (Spring Boot, OpenAPI/Swagger specification)
2. Implement API authentication (OAuth 2.0 / API key / mTLS) on all search endpoints
3. Migrate from `javax.servlet` to `jakarta.servlet` for Tomcat 10 compatibility
4. Resolve `xPlatform 2014.1.1` root POM version to align with current `xplatform_LIB:6.x`
5. Fix PAN masking in xSearch-common (first 6 + last 4 per PCI DSS Req 3.3.1)
6. Externalise Log4j configuration path
7. Implement search audit logging (who, when, what criteria, result count)
8. Implement rate limiting and result set size limits

## Code-Level Risks
| Risk | File:Line | Detail |
|---|---|---|
| `javax.servlet` import | `XSearchXmlRPCServlet.java:7-8` | Non-Jakarta namespace; incompatible with Tomcat 10 |
| No auth filter or security constraint | `web.xml:1-51` | No `<security-constraint>` or auth filter declared |
| Hardcoded log path | `web.xml:35` | `file:///d:/c-base/config/xSearch-xmlrpc/log4j.xml` |
| Same PAN masking issue | `xSearch-common/MaskCCHelper.java:26-47` | Inherited non-PCI-compliant masking |
| Spring DTD-based XML context | `dataSourcesContext.xml:2` | Spring 2.0 DTD — very old; no namespace validation |
| `Log4jConfigListener` | `web.xml:27-30` | Deprecated Spring listener; may produce silent failures |
