# Business Analyst View — xsearch-new_SVC

## Business Purpose
xSearch New SVC is the Gen-2 modernisation of the xSearch search service. It exposes cardholder and account search functionality via an XML-RPC HTTP endpoint, replacing the Gen-1 xsearch_LIB library's direct in-process API with a networked service. It is consumed by CSA (Customer Service Agent) tools and internal platform services that need to search for cardholders by multiple criteria.

## Capabilities
- All search capabilities of xsearch_LIB (which it bundles as its implementation layer) plus:
  - **Mobile phone search:** `FindMemberByMobilPhone` — new search dimension not present in xsearch_LIB
  - **Device search by Member ID:** `SearchDeviceByMemberId` — look up all cards for a given member
  - **Member search by PUID (PUD inquiry):** `MemberInquiryByPUID` — search by Partner User ID
  - **Plastic-only card member search:** `MemberByPlasticOnlyCard`, `MemberByPUIDPlasticOnlyCard`
  - **XML-RPC client library:** `xSearch-client` module provides an XML-RPC client for consuming services
- **XML-RPC transport:** Service is exposed as a single XML-RPC servlet (`XSearchXmlRPCServlet`) handling all method calls over HTTP POST

## Modules
| Module | Artifact | Purpose |
|---|---|---|
| xSearch-common | Common value objects | Shared `MemberInquiryValue`, `DevicesInquiryValue`, `EMember`, `MaskCCHelper` |
| xSearch-client | XML-RPC client | `XSearchXMLRPCClient` — client stub for consuming the service |
| xSearch-impl | Core implementation | All DAO and service logic (mirrors and extends xsearch_LIB) |
| xSearch-xmlrpc | WAR / servlet | XML-RPC servlet, Spring context wiring, web deployment descriptor |

## Key Entities (same as xsearch_LIB plus additions)
| Entity | Module | Notes |
|---|---|---|
| DevicesInquiryValue | xSearch-common | Device inquiry result (plural — device list) |
| FindMemberByMobilPhone | xSearch-client/xmlrpc | New: mobile phone search input/output |
| MemberInquiryByPUID | xSearch-impl | New: PUID-based member lookup |
| MemberByPlasticOnlyCard | xSearch-impl | New: plastic-only card member search |
| PudInquiry / PudInquiryValue | xSearch-impl | New: PUD-based inquiry |

## Business Rules
- All search rules from xsearch_LIB apply (wildcard restrictions, check number format, PUID + affiliate ID requirement)
- Mobile phone search is an additional search dimension with no wildcard restrictions mentioned
- XML-RPC all-inclusive servlet maps to `/*` — any XML-RPC method call is routed through one servlet
- Director-configured datasource (`DirectorConfiguredDBCPdatasourceCreator`) allows dynamic database connection configuration without redeployment

## Process Flows
1. Client service calls `XSearchXMLRPCClient.findMember(criteria)` (or similar method)
2. XML-RPC client serialises the request as an XML-RPC message and sends HTTP POST to the service
3. `XSearchXmlRPCServlet` receives and deserialises the XML-RPC call
4. Spring `searchService` bean executes the search via the xSearch-impl data-access layer
5. Results are serialised back as XML-RPC response and returned to the client

## Compliance Relevance
- Same PCI DSS scope as xsearch_LIB — PAN, SSN, and DDA searches are in-scope for CHD handling
- XML-RPC transport is plaintext XML over HTTP unless TLS is configured at the reverse proxy layer
- `MaskCCHelper` in xSearch-common retains the same non-PCI-compliant masking logic (first 4 + last 4)
- Director-based dynamic datasource configuration means database credentials are managed externally — positive for secrets management but the Director service must also be secured

## Risks
- XML-RPC is an older protocol with no built-in authentication or TLS — security depends entirely on network controls and reverse proxy configuration
- The parent POM `com.citi.prepaid.service:service-parent:6` uses Spring 2.5.4 (a very old version) — see Technical Debt
- Log4j configuration references a hardcoded local path `file:///d:/c-base/config/xSearch-xmlrpc/log4j.xml` in `web.xml` — this will fail in any environment other than the developer's Windows machine
- All search methods exposed via a single servlet with no method-level access control
