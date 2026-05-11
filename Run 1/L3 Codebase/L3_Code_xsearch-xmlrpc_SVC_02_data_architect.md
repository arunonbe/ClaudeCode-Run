# xSearch XML-RPC SVC — Data Architect View

## 1. Data Model Overview

xSearch is a read-oriented service — it does not own any writeable tables. Its role is to aggregate and project cardholder identity data from the underlying ecount/cbase platform databases. The data model manifest within this service is therefore a set of transfer objects (TOs) and value objects (VOs) that represent the query inputs and response shapes.

### Primary Response Object: `MemberInquiryValue`

**File:** `xsearch-common/src/main/java/com/ecount/data/member/MemberInquiryValue.java`

| Field | Java Type | PCI/PII Classification | Notes |
|---|---|---|---|
| `memberId` | `String` | PII (internal ID) | Platform member identifier |
| `cardNumber` | `String` | **PAN — PCI Req 3** | Full card number if populated by impl |
| `privateLabelCardNumber` | `String` | **PAN — PCI Req 3** | Alternate PAN reference |
| `deviceId` | `String` | Internal | eCard device ID |
| `ebn` | `String` | Internal | Product identifier code |
| `firstName`, `lastName`, `middleName` | `String` | PII | Cardholder name |
| `city`, `state`, `postal`, `country` | `String` | PII | Address components |
| `role` | `String` | Metadata | User role code |
| `userStatus` | `String` | Metadata | Account status indicator |
| `accountStatus` | `String` | Metadata | Account lifecycle status |
| `productName` | `String` | Metadata | Derived from EBN |
| `eCapFeature` | `String` | Metadata | ECAP feature flag |
| `programId` | `String` | Internal | Program/affiliate code |
| `plasticMemberId` | `String` | Internal | Physical card member ID |
| `packageId` | `String` | Internal | Package identifier |

The `getCardNumberMasked()` method (line 75-77) calls `MaskCCHelper.maskThisCC(cardNumber)` which masks the middle 8 digits. However, `getCardNumber()` (line 59-61) returns the raw unmasked value. Both getter methods are public. The caller determines which method to invoke when serializing the response over XML-RPC.

### Extended Response Object: `ExtendedRegistrationValue`

**File:** `xsearch-common/src/main/java/com/ecount/data/member/ExtendedRegistrationValue.java`

This object is returned by the `execute(String memberId)` method on `EMember`. While the source file was not examined in detail, the method signature indicates it retrieves fuller member registration profile data for a known `memberId`.

### Device Query Objects

**Files:** `xsearch-impl/src/main/java/com/ecount/data/device/`

The `DeviceInquiryValue` class represents card/device-level lookup results, including redeemable payment values (`RedeemablePaymentVO`). Device lookups include:
- Search by member ID (`SearchDeviceByMemberId`)
- Search by claim code (`SearchMemberByClaimcode`, `SearchEcheckByClaimcode`)
- Search by credit card (`SearchEcapMemberByCreditCard`)
- Search by eCheck (`SearchMemberByECheck`)
- Redeemable payments by member (`SearchRedeemablePaymentsByMember`, `SearchRedeemablePaymentByIdAndMember`)

## 2. Query Input Model

### `EMember.find()` Method Signatures

The `EMember` interface defines five progressive overloads of `find()`, each adding more search parameters. The most complete signature (`EMember.java`, lines 33-38) accepts:

```
agent, lastName, firstName, cardNumber, ddaNumber, affiliateId,
ppd, nss, puid, xppd, dfi, routingNum, accountNum,
email, city, home_phone, mobile_phone, productsCategory, memberIds,
address1, state, zipCode, country, prgPrefix
```

This is a 24-parameter method, indicating organic API evolution rather than planned API design. The presence of `cardNumber` as a search parameter means the service also supports PAN-based lookup in addition to PAN as a return value.

### XML-RPC Exposed Input: `FindMemberByMobilPhone`

**Files:**
- `xsearch-xmlrpc/src/main/java/com/ecount/services/xsearch/xmlrpc/proxy/input/FindMemberByMobilPhone.java`
- `xsearch-client/src/main/java/com/ecount/services/xsearch/client/xmlrpc/input/FindMemberByMobilPhone.java`

The XML-RPC input object carries `agent` and `mobilePhone` as fields. The mobile phone number is passed as a plain `String` — there is no documented hashing or partial-masking of the phone number on the wire.

## 3. Data Flow Architecture

```
Calling Service (CSA/Workbench)
        |
        | HTTP POST (XML-RPC over HTTP)
        v
XSearchXmlRPCServlet  [xsearch-xmlrpc module]
        |
        v
XSearchProxy.FindMemberByMobilPhone()
        |
        | delegates to EMember.find(agent, ..., mobilePhone, ...)
        v
EMember implementation (cbase/ecount-system)
        |
        | SQL queries via Spring JDBC / StoredProc
        v
Underlying CDE database (ecountcore / cbaseapp SQL Server)
        |
        v
MemberInquiryValue[] returned up the chain
        |
        v
XML-RPC serialization back to caller
```

The `XSearchProxy` (`XSearchProxy.java`, line 54) calls `find()` with 22 positional arguments, the majority of which are empty strings. This means every mobile phone lookup executes a broad search with mobile phone as the only discriminating filter, and the backend stored procedure must handle this sparse input pattern.

## 4. Data Masking Implementation

`MaskCCHelper.java` provides four static masking methods:

- **`maskThisCC(String ccToMask)`** — masks the middle 8 digits of a card number, leaving first N and last N characters visible. The calculation at lines 34-35 is: `startMasking = (length - 8) / 2`, `endMasking = length - startMasking`. For a 16-digit PAN, this masks positions 4-11, leaving positions 0-3 and 12-15 visible — a "first 4 / last 4" exposure pattern. **Note:** PCI DSS Req 3.3.1 permits display of first 6 / last 4 digits maximum; displaying first 4 / last 4 digits of a 16-digit PAN is non-standard and may over-expose the BIN range in some contexts.
- **`maskThisSSN(String ssnToMask)`** — masks the first 6 digits of a 9-digit SSN, showing only the last 3 digits. This is more aggressive masking than the regulatory minimum (last 4) but is non-standard (usually last 4 is shown, not last 3).
- **`maskAchAccountNumber(String accountNumberToMask)`** — masks everything except the last 4 digits of an ACH account number.
- **`galileoCheckCC(String ccToCheck)`** — BIN detection for Galileo-issued cards using hardcoded BIN prefix `514977` (line 66).
- **`privateLabelCCNumber(String ccToCheck)`** — private label BIN detection for prefixes `44815619` and `448184` (lines 95-96). Returns the last 10 digits (strips the BIN). These hardcoded BIN values constitute embedded business rules that are brittle if card programs change BINs.

## 5. Serialization Technology

The service uses Apache XML-RPC (`com.citi.prepaid.service.core:xmlrpc:3.0.2`) for wire serialization. XML-RPC transmits all data as XML over HTTP. This has implications:
- **No native encryption at the application layer** — transport-level TLS is the only protection for PANs in transit
- **No schema validation** — the XML-RPC protocol does not enforce field-level constraints; any downstream parsing is implementation-dependent
- **Verbose payloads** — XML is significantly larger than binary or JSON alternatives, affecting throughput when returning large `MemberInquiryValue[]` arrays

## 6. Service Discovery Data Flow

The `XSearchXMLRPCClient` uses `SimpleXSearchServiceLocationResolvingCache` to discover the xSearch endpoint via a Director service. The cache TTL is exactly 1 hour (`1000 * 60 * 60` ms, `XSearchXMLRPCClient.java` line 90). The `director-client` version `2.0.1` is consumed for this purpose. The Director service URL is the only external configuration dependency for clients — all xSearch endpoint resolution flows through it.

## 7. Database Technology

The `pom.xml` references `com.microsoft.sqlserver:mssql-jdbc:12.5.0.jre11-preview` as a Tomcat library dependency (in xsso, and by implication in the overall platform). The underlying data store is Microsoft SQL Server. DAO patterns in the `xsearch-impl` module use Spring JDBC (`StoredProcedure` subclasses) suggesting that all database interaction goes through stored procedures — a pattern consistent with the CDE's need to limit ad-hoc SQL.

## 8. PCI Data Classification Summary

| Data Element | Present in Response | Masked by Default | PCI DSS Relevance |
|---|---|---|---|
| Full PAN (`cardNumber`) | Yes — field exists in `MemberInquiryValue` | No — masking is optional; `getCardNumber()` returns raw | Req 3.3.1 — must be masked in display |
| Cardholder name | Yes | No | Req 3 — SAD if combined with PAN |
| Address (city/state/zip/country) | Yes | No | PII / CCPA |
| SSN (via `maskThisSSN`) | Helper exists; field not directly in `MemberInquiryValue` | Partial (shows last 3) | CCPA / GLBA |
| ACH account number | Helper exists; not directly in `MemberInquiryValue` | Last 4 shown | GLBA / NACHA |
| Mobile phone | Used as search input | Not masked in logs | PII |
