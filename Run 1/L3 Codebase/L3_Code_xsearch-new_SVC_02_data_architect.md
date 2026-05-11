# Data Architect View — xsearch-new_SVC

## Data Stores
Same four SQL Server databases as xsearch_LIB, with dynamic Director-based configuration:

| Store | Configuration Method | Notes |
|---|---|---|
| EcountCoreDataSource | Director RPC → `DirectorConfiguredDBCPdatasourceCreator` | Primary member/device data |
| JobSvcDataSource | Director RPC → `DirectorConfiguredDBCPdatasourceCreator` | Job processing records |
| CbaseappDataSource | Context variable `${database}` / `${jobsvcdatabase}` | Secondary member data (same as xsearch_LIB) |
| WebCertOmahaDataSource | Not visible in `dataSourcesContext.xml` | CSA comments — may be provided via Director or separate context |

The `dataSourcesContext.xml` uses Spring DTD-based XML (Spring 2.0 DTD) and delegates actual datasource creation to `DirectorConfiguredDBCPdatasourceCreator` — database connection parameters are fetched from the Director service at runtime using `${agent}`, `${database}`, and `${directorAddress}` placeholders.

## Schema
Same member, device, job, and comment tables as xsearch_LIB. Additional queries:
- Mobile phone lookup: `FindMemberByMobilPhone` — member lookup by phone number
- Device by member ID: `DeviceInquiryByMemberIdSpringDAO` — all devices for a member
- PUID inquiry: `MemberInquiryByPUIDSpringImpl` — member resolution by PUID

## Sensitive Data
Same as xsearch_LIB, plus:
| Data Element | Classification | Location |
|---|---|---|
| Mobile phone number | PII | `FindMemberByMobilPhone` input/output; `MemberInquiryValue` |
| All xsearch_LIB CHD/PII fields | CHD/PII | Inherited from xSearch-impl |

## Encryption
- No encryption applied within the service code
- XML-RPC communication is plaintext XML over HTTP — TLS must be applied at the network/reverse proxy layer
- `dataSourcesContext.xml` uses DBCP connection pool (`DirectorConfiguredDBCPdatasourceCreator`) — TLS to SQL Server depends on JDBC URL and driver configuration set by Director

## Data Flow
```
XML-RPC Client (calling service)
        |  HTTP POST (XML-RPC over HTTP — plaintext unless TLS at proxy)
        v
XSearchXmlRPCServlet (xSearch-xmlrpc)
        |
        v
Spring ApplicationContext (xSearchContext.xml, xmlrpcImplContext.xml, etc.)
        |
        v
XSearchProxy → SearchServiceImpl (xSearch-impl)
        |
   +----+-----+------+-------+
   |         |      |        |
   v         v      v        v
MemberInq  DeviceInq EcapInq  JobAction
SpringDAO  ByMemberId Impl     SpringDAO
   |         |      |        |
   +----+-----+------+-------+
        |
        v
SQL Server (EcountCore / JobSvc / Cbaseapp via Director-configured DBCP)
        |
        v
MemberInquiryValue[] / DevicesInquiryValue (returned as XML-RPC response)
```

## Data Quality and Retention
- Same as xsearch_LIB — no quality rules or retention policies at the library/service level
- Log4j config references `file:///d:/c-base/config/xSearch-xmlrpc/log4j.xml` — hardcoded Windows path; on Linux/container deployments, logging may fail or fall back silently

## Compliance Gaps
- **Plaintext XML-RPC transport:** PAN, SSN, and member data transmitted in unencrypted XML if TLS is not applied at the proxy/network layer — PCI DSS Req 4.2 (protect CHD in transit)
- **Same PAN masking non-compliance** as xsearch_LIB — `MaskCCHelper` in xSearch-common has the same middle-8-mask issue
- **Director service dependency:** Database credentials are fetched from Director via RPC — if Director is compromised, all database credentials are exposed
- **No authentication on XML-RPC endpoint:** Any service with network access to the endpoint can make search requests — no API key, no mutual TLS, no token-based authentication
- **Spring 2.5.4 dependency** in parent POM — this version of Spring is EOL and has multiple known CVEs; the actual runtime version used must be confirmed against the parent POM `com.citi.prepaid.service:service-parent:6`
