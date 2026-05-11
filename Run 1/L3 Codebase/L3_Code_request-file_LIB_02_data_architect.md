# Data Architect View — request-file_LIB

## Data Models

### JAXB XML Schema Classes (`com.ecount.payment`)

These classes are generated from (or aligned with) an XML Schema Definition for the eCount payment request file format:

**`Requestfile`** — root XML element:
- `creationdate` (XMLGregorianCalendar)
- `batch` (List\<Batchtype>)

**`Batchtype`**:
- `request` (List\<Request>)

**`Request`** — individual payment instruction:
- Contains a specific request type element (one of the following)

**`Cardtype`** — card payment instrument data:
- `cardnumber` (String) — full card number / PAN
- `expmonth` (XMLGregorianCalendar) — expiration month
- `expyear` (XMLGregorianCalendar) — expiration year
- `cardtype` (String) — card network/type code
- `cvcode` (String) — **CVV/CVC code (Sensitive Authentication Data)**

**`Createaccountrequesttype`** — new account creation request
**`Addfundsrequesttype`** — funds addition request
**`Stoppaymentrequesttype`** — stop payment request
**`Spinrequesttype`** — SPIN (Single Payment Instruction Number?) request
**`Ppdtype`** — ACH PPD (Prearranged Payment and Deposit) entry
**`Basicregistrationtype`**, **`Extendedregistrationtype`**, **`Secureprofileaddendatype`** — registration and profile data

### Domain Value Objects (`com.ecount.payment.common`)

- `AccountCreationVO` — account creation data
- `FundsAdditionVO` — amount, currency, target account
- `PaymentStopVO` — stop payment details
- `SpinVO` — SPIN instruction data
- `BatchVO` — batch-level metadata
- `RequestVO`, `RequestFileVO` — aggregate request file data

## Sensitive Data — Critical PCI DSS Finding

**`Cardtype.cvcode`** is the most critical data element in this library.

CVV/CVC (Card Verification Value/Code) is classified as **Sensitive Authentication Data (SAD)** under PCI DSS Req 3.2.1. The PCI DSS Standard states:

> "Do not store sensitive authentication data after authorization (even if encrypted). If sensitive authentication data is received, render all data unrecoverable upon completion of the authorization process."

The `Cardtype` class maps `cvcode` to an XML element without `@XmlTransient`:

```java
// File: requestfile-impl/src/main/java/com/ecount/payment/Cardtype.java, line 52
@XmlElement(namespace = "http://www.ecount.com/")
protected String cvcode;
```

This means that if a `Cardtype` object is populated with a CVV value and `RequestBuilder.createReqFile()` is called, the CVV is written in plaintext to an XML file on the filesystem. This is a direct violation of PCI DSS Req 3.2.1 — SAD stored after authorization (or in the case of batch processing, stored during authorization preparation).

**`Cardtype.cardnumber`** is a PAN (Primary Account Number). Under PCI DSS Req 3.3, PANs must be rendered unreadable wherever stored. A full PAN in plaintext in a batch XML file on a shared filesystem violates this requirement unless the filesystem itself provides strong encryption satisfying PCI DSS Req 3.5.

## Encryption Status

No encryption is applied by this library to the data it serializes. `RequestBuilder.writeXMLToStream()` writes JAXB-marshalled XML directly to a `FileOutputStream` — no encryption wrapper, no secure-delete mechanism. The security of the output files depends entirely on:
1. Filesystem-level access controls on the `REQUEST_FILE_BASE_PATH` directory
2. Filesystem encryption (e.g., BitLocker, LUKS) on the host where the files are written
3. Operational procedures for secure deletion after the processor has consumed the file

None of these are controlled or verified by the library itself.

## Database Schemas

No database access. The library writes to the filesystem only.

## Data Flows

```
[Order Management Service]
    → Creates PaymentData (populates VOlist: FundsAdditionVO, AccountCreationVO, etc.)
    → Populates Cardtype with cardnumber, expmonth, expyear, cardtype, cvcode
    → Calls RequestBuilder.createReqFile()
        → JAXBContext marshals Requestfile to XML
        → FileOutputStream writes XML to REQUEST_FILE_BASE_PATH/{filename}.xml
    → [File-based payment processor pickup]
        → Processor reads XML file, executes payment instructions
        → File should be deleted/archived after processing (not managed by this library)
```

The `cvcode` field travels: in-memory VO → JAXB object tree → XML text → filesystem file. At the filesystem point, it is plaintext SAD on disk.

## Retention Concerns

Batch XML files written by this library contain PANs and potentially CVVs. PCI DSS Req 3.2.1 requires that SAD not be stored at all. PCI DSS Req 3.3 requires PANs to be rendered unreadable wherever stored. The operational process for how these files are retained, secured, and deleted must be assessed independently of this library. The library itself provides no retention or deletion controls.

## PCI DSS Compliance Assessment

| Issue | PCI DSS Requirement | Status |
|---|---|---|
| `cvcode` marshalled to XML without `@XmlTransient` | Req 3.2.1 (no SAD storage) | Violation risk — depends on whether cvcode is populated at runtime |
| `cardnumber` (PAN) in plaintext XML on filesystem | Req 3.3 (render PAN unreadable) | Violation if filesystem lacks strong encryption |
| No application-layer encryption of output files | Req 3.5 (protect cryptographic keys) | Control gap — depends on filesystem security |
| No secure delete mechanism | Req 3.1 (minimize data storage) | Control gap |

The key question for compliance is: **Is the `cvcode` field populated at runtime?** If the calling code never sets `cvcode` on the `Cardtype` object (leaving it null), the XML element will be null or empty, and SAD will not be stored. A runtime audit of all callers of `setCardtype(Cardtype)` and `setCvcode(String)` across the consuming codebase is required to determine actual exposure.
