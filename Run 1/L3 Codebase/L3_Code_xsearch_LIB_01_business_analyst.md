# Business Analyst View — xsearch_LIB

## Business Purpose
xSearch LIB is a Gen-1 Java library providing cardholder and account search capabilities for the eCount prepaid card platform. It enables Customer Service Agents (CSA) and internal tools to look up cardholders by multiple criteria including card number, name, DDA (account) number, SSN, Partner User ID (PUID), eCheck data, and addenda fields. It is the data-access layer for CSA search functionality.

## Capabilities
- **Member search:** Look up cardholder records by last name, first name, card number (16-digit PAN), DDA number, SSN, PUID, XPPD, DFI routing number, ACH account number, addenda fields
- **Device/card search:** Search payment devices (cards) by PUD (payment unit designation) and by member ID
- **eCAP member inquiry:** Retrieve ECAP member records by credit card number
- **DDA-only member inquiry:** Look up members in a DDA-only (no eCard) context
- **eCheck search:** Search members by eCheck claim code or by eCheck account details
- **Redeemable payment search:** Look up redeemable payments by member and by payment ID
- **Job action inquiry:** Search job action records linked to payments
- **Member comment (CSA):** Retrieve CSA comment history for a member
- **PAN masking:** `MaskCCHelper` provides masking of credit card middle digits (first 4 / middle 8 masked / last 4) for display in CSA interfaces
- **SSN masking:** `MaskCCHelper.maskThisSSN()` — first 6 digits masked, last 3 shown
- **ACH account masking:** `MaskCCHelper.maskAchAccountNumber()` — all but last 4 masked

## Key Entities
| Entity | Package | Description |
|---|---|---|
| MemberInquiryValue | `com.ecount.data.member` | Cardholder search result (memberId, name, etc.) |
| DeviceInquiryValue | `com.ecount.data.device` | Card/device search result |
| EcapInquiryValue | `com.ecount.data.member` | ECAP cardholder data |
| RedeemablePaymentVO | `com.ecount.data.device` | Redeemable payment value object |
| CommentHistoryValue | `com.ecount.data.member.csa.comment` | CSA comment record |
| EMemberInquiryValue | `com.ecount.one.service.emember` | Enriched member inquiry result |
| SearchMessage | `com.ecount.one.service.search` | Search request/response wrapper |
| EcountContext | `com.ecount.one.value` | Platform context (agent, config paths) |
| XSearchConstants | `com.ecount.one.value` | Search option constants |

## Business Rules
- Wildcard (`%`) search is restricted for card number, SSN, XPPD, DFI, check account number, and PUID searches — unrestricted wildcards are only permitted for name and DDA searches
- Card numbers are wildcard-prefixed for 10-digit inputs (private label workaround for BUG0006345)
- Check account numbers must be exactly 14 numeric characters with no wildcards (BUG0006138)
- PUID search requires a paired Affiliate ID (4 numeric characters)
- SSN search is restricted to `X`, `O`, and `N` CSA roles (outsourced customer service)
- PAN masking uses a middle-8-digits mask, leaving first 4 and last 4 visible — non-standard PCI masking (PCI DSS requires first 6 / last 4)
- Galileo BIN check: card number prefix `514977` identifies a Galileo-hosted account
- Private label BINs `44815619` (8 digits) and `448184` (6 digits) trigger 10-digit card number extraction

## Process Flows
1. CSA or calling service constructs a `SearchMessage` or `DeviceSearchCriteria` with search criteria and agent context
2. `SearchServiceImpl.search()` routes to `searchWithEcard()` or `searchWithDDA()` based on criteria type
3. Query is validated (wildcard rules, format checks)
4. SQL query executes via Spring JDBC stored procedure or direct Spring DAO
5. Results are returned as `MemberInquiryValue[]` or `List<DeviceInquiryValue>`
6. Calling service (e.g., xsearch-new_SVC) applies masking via `MaskCCHelper` before returning data to client

## Compliance Relevance
- SSN (`nss`) is a search parameter — transmitting and storing SSN search terms in logs would violate PCI DSS and GLBA
- Card number (`cardNumber`) is a search parameter — raw PAN in memory and potentially in logs
- PAN masking implementation (`MaskCCHelper`) retains first 4 AND last 4 digits — this is non-compliant with PCI DSS Req 3.3 which permits display of only first 6 / last 4
- Wildcard search restrictions protect against broad data harvesting attacks but are enforced in application logic only

## Risks
- Raw PAN passed as a search parameter through `SearchServiceImpl` — PAN in memory and potentially in debug logs
- SSN as a search parameter — SSN values may appear in application logs at DEBUG level
- PAN masking leaves 8 non-masked digits (first 4 + last 4) — exceeds PCI DSS display limits
- No rate limiting or search volume controls at the library level — bulk harvesting of member data requires only a calling service with no restrictions
