# xSearch XML-RPC SVC — Business Analyst View

## 1. Service Identity and Business Purpose

xSearch XML-RPC (`xsearch-new`, artifact version `4.0.2-SNAPSHOT`) is the platform-wide cardholder and account lookup service for the Onbe Gen-1 prepaid payments platform. Its primary business function is to allow internal Onbe operator tooling — principally the Customer Service Application (CSA) and Workbench — to search the member/card database using a variety of cardholder identifiers. Every time a customer service agent, compliance analyst, or dispute handler needs to locate a cardholder account, this service is the first stop.

The README.md states the purpose directly: _"Xsearch is a mechanism that allows us to look up account information on CSA from the database."_

The service is consumed indirectly by every support workflow that touches cardholder identity resolution, including:
- Customer service agent account look-up
- Dispute and chargeback initiation workflows
- Cardholder identity verification for password reset and self-service
- Mobile phone search for CSR tooling
- Cross-program cardholder searches for fraud and compliance operations

## 2. Supported Search Dimensions

The `EMember` interface (`xsearch-common/src/main/java/com/ecount/one/service/emember/EMember.java`) defines seven overloaded `find()` method signatures. Collectively they support lookup by:

| Search Parameter | Interface Field | Notes |
|---|---|---|
| Last name | `lastName` | Plain text |
| First name | `firstName` | Plain text |
| Card number (PAN) | `cardNumber` | Used to locate the physical card |
| DDA number | `ddaNumber` | Bank DDA / checking account |
| Affiliate / Program ID | `affiliateId` / `programId` | Scopes the search to a program |
| NSS / PPD identifiers | `nss`, `ppd`, `xppd` | Internal program codes |
| PUID | `puid` | Platform-unique identifier |
| Email address | `email` | Extended signature |
| City, state, postal, country | address fields | Extended signature |
| Mobile phone | `mobile_phone` | Used in XML-RPC endpoint |
| ACH routing + account | `routingNum`, `accountNum` | DDA identification |
| Member IDs | `memberIds` | Bulk lookup |

The XML-RPC-exposed endpoint (`XSearchProxy.java`) currently only exposes `FindMemberByMobilPhone`, meaning the primary externally callable operation is mobile-phone based member search. The full `EMember.find()` family is available to internal Java callers via the client library.

## 3. Data Returned to Callers

`MemberInquiryValue` (`xsearch-common/src/main/java/com/ecount/data/member/MemberInquiryValue.java`) is the response object returned from all search operations. It contains:

- `memberId` — platform internal member identifier
- `cardNumber` — the raw prepaid card number (PAN) field exists in the object; `getCardNumberMasked()` applies middle-8 masking but the underlying field is present
- `privateLabelCardNumber` — alternate card reference
- `deviceId` — internal device identifier
- `firstName`, `lastName`, `middleName`
- `city`, `state`, `postal`, `country`
- `role`, `userStatus`, `accountStatus`
- `productName`, `eCapFeature`, `ebn`
- `programId`, `plasticMemberId`, `packageId`

The `MaskCCHelper` class (`xsearch-common/src/main/java/com/ecount/one/service/emember/MaskCCHelper.java`) provides `maskThisCC()`, `maskThisSSN()`, and `maskAchAccountNumber()` utility methods. These masking routines are available as helpers, but the raw values also exist in the `MemberInquiryValue` object. The extent to which raw versus masked values are transmitted over the XML-RPC wire depends on the backend `EMember` implementation's decision about which setter it calls. **This is a critical PCI observation: the `MemberInquiryValue` object has a `cardNumber` field that carries the full PAN if the upstream implementation populates it without masking.**

## 4. Business Scope and Client-Facing Impact

The service underpins zero-latency customer service resolution for Onbe's B2C disbursement programs. Any degradation in xSearch availability directly affects:

- Mean handle time (MHT) at the CSA call-center tier
- Automated cardholder verification in IVR flows
- Compliance-driven account freeze and investigation workflows
- Dispute management for prepaid card programs

The `FindMemberByMobilPhone` XML-RPC operation has particular business significance in markets where mobile number is the primary account identifier for B2C payout cardholders.

## 5. Multi-Product Scope

The `MemberInquiryValue.setEbn()` method (`MemberInquiryValue.java`, lines 101–117) contains product-classification logic based on EBN prefix codes:
- `0101` → Webcertificate
- `0201` → Ecount Classic
- `0301` → Private Buy
- `0501` → Branded Currency
- ECAP feature flag → ECAP product
- Default → B2C

This means a single xSearch deployment resolves cardholders across all Onbe prepaid product lines, making it a shared-service dependency with platform-wide blast radius.

## 6. Dependency Landscape

The service depends on `xPlatform` (version `6.1.8`), `ecount-system` (version `4.0.2`), `director-client` (version `2.0.1`) for service discovery, and an internal `xmlrpc` library (`com.citi.prepaid.service.core:xmlrpc:3.0.2`). The director-client dependency means xSearch participates in the platform's service registry pattern — clients discover the xSearch service endpoint dynamically rather than via static configuration. The 1-hour service-location cache (`SimpleXSearchServiceLocationResolvingCache`, constructed with `1000 * 60 * 60` ms TTL) in `XSearchXMLRPCClient.java` means that if the xSearch service moves, it can take up to one hour for dependent services to detect the new location.

## 7. Change Log and Roadmap Signals

The `README.md` includes a prominent advisory note: _"Has dependencies on Core2 that need to be removed."_ This signals a known technical debt item that is part of the broader Gen-1 to Gen-2 migration roadmap. The `prepaid-parent` version `6.0.12` aligns this service with the current platform parent POM baseline used across all Gen-1 services in this analysis cohort.

## 8. Regulatory and Compliance Relevance

Because xSearch can return card numbers and PII for cardholder lookup, it operates within the Onbe CDE boundary from a PCI DSS v4.0.1 perspective. The service must be treated as an in-scope system under:
- **PCI DSS Req 3** — protection of stored cardholder data (indirectly, as the service retrieves from the CDE database)
- **PCI DSS Req 6** — secure development for in-scope systems
- **PCI DSS Req 7/8** — access control to CDE data, since any authenticated caller can retrieve full card records
- **CCPA / GDPR** — retrieval of name, address, and account status constitutes processing of personal data

The lack of documented caller-level authorization (beyond the agent identifier passed in the `find()` calls) is a compliance risk requiring investigation — see the Security Architect view.
