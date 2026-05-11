# Business Analyst Report — dfapi-client_LIB

## 1. Business Purpose
dfapi-client_LIB is a **Java client library** for integrating with the **Dodd-Frank API (DFAPI)** — a Citi/Citigroup-origin SOAP web service that provides international wire-transfer fee disclosure quotes as required by the **Dodd-Frank Wall Street Reform and Consumer Protection Act (Section 1073)**. The library abstracts the protocol transport (SOAP over HTTP or IBM MQ/JMS) and provides a simple Java interface for callers to obtain a fee/disclosure quote for a given international payment.

**Regulatory context**: Dodd-Frank Section 1073 (Remittance Transfer Rule, Reg E §1005.31) mandates that remittance transfer providers disclose fees, exchange rates, and delivery dates to consumers before executing international transfers. This library provides the mechanism for obtaining those disclosures.

---

## 2. Capabilities

| Capability | Class | Protocol |
|---|---|---|
| Get fee disclosure quote (SOAP/HTTP) | `HTTPHandler` | SOAP over HTTPS via Apache Axis |
| Get fee disclosure quote (JMS/MQ) | `JMSHandler` | IBM MQ via `MQJMS` |
| Common client interface | `DFAPIClient` / `DFAPIClientImpl` | Protocol-agnostic |

Single operation: `execute(QuoteRequest request) → QuoteResponse` (`DFAPIClient.java` line 10).

---

## 3. Key Business Entities

### 3.1 QuoteRequest (`com.citi.prepaid.dfapi.request.QuoteRequest`)

| Field | Type | Description |
|---|---|---|
| `clientId` | String | Citi client identifier |
| `subEntityId` | String | Sub-entity within client |
| `destinationCountry` | String | Payment destination country (ISO) |
| `destinationState` | String | Destination state |
| `destinationCity` | String | Destination city |
| `bankCode` | String | Beneficiary bank code |
| `bankCodeType` | `BankCodeTypeXSType` | Code type (SWIFT, ABA, etc.) |
| `paymentMethod` | `PaymentMethodXSType` | Payment rail (wire, ACH, etc.) |
| `paymentCurrency` | String | Currency of payment (ISO) |
| `fundingCurrency` | String | Funding currency (ISO) |
| `paymentCurrencyAmount` | BigDecimal | Amount in payment currency |
| `nonSTPFlag` | `NonSTPFlagXSType` | Straight-through processing flag |
| `isBeneDeduct` | `IsBeneDeductXSType` | Whether fee deducted from beneficiary amount |
| `beneDeductFeeType` | `BeneDeductFeeTypeXSType` | Fee type if bene-deduct |
| `estimatePercentile` | BigInteger | Estimate percentile for disclosure |
| `chargeCode` | `ChargeCodeXSType` | Charge code |
| `daysToSettle` | BigInteger | Settlement days |
| `releaseTime` | Date | Payment release time |
| `nostroCountry` | String | Nostro account country |
| `isOurDeduct` | String | Whether our-deduct applies |
| `valueDate` | Date | Value date |
| `flagFutureDated` | String | Future-dated flag |
| `flagODE` | String | ODE flag |

### 3.2 QuoteResponse (`com.citi.prepaid.dfapi.response.QuoteResponse`)

| Field | Type | Description |
|---|---|---|
| `disclosureDate` | String | Date of disclosure |
| `otherFees` | BigDecimal | Other applicable fees |
| `feeType` | `FeeTypeXSType` | Fee type |
| `totalTaxes` | String | Total tax amount |
| `deliveryDate` | XMLGregorianCalendar | Expected delivery date |
| `uniqueIdentifier` | String | Unique transaction/quote ID |
| `returnCode` | String | Success/error code |
| `returnMessage` | String | Human-readable result message |
| `chargeCodeUsed` | String | Charge code applied |
| `beneDeductUsed` | String | Whether bene-deduct was applied |
| `ourDeductUsed` | String | Whether our-deduct was applied |
| `additionalParameters` | List<AdditionalParameter> | Extended response fields |

---

## 4. Business Rules

1. If `nonSTPFlag` is set, the payment bypasses straight-through processing and may incur different fees.
2. `isBeneDeduct` and `beneDeductFeeType` control whether fees are deducted from the beneficiary's received amount.
3. `isOurDeduct` — fee absorbed by the sending entity.
4. `flagFutureDated` — enables future-dated payment disclosures.
5. `estimatePercentile` — required by Dodd-Frank to show estimated fees at a given percentile.
6. The library supports two transport mechanisms; callers select HTTP or JMS via Spring/XML configuration (not via code).

---

## 5. Business Flows

### 5.1 HTTP (SOAP) Flow
```
Caller → DFAPIClientImpl.execute(QuoteRequest)
  → HTTPHandler.getDFAPIResponse(QuoteRequest)
    → Convert QuoteRequest to WSDL-generated QuoteRequestType
    → Invoke DFAPIWSDLSOAPBindStub.getDFData(null, DFAPIRequest)
      [SOAP call to Citi DFAPI endpoint via Apache Axis]
    ← DFAPIResponse → QuoteResponseType
    → Convert to QuoteResponse
  ← QuoteResponse
```

### 5.2 JMS (MQ) Flow
```
Caller → DFAPIClientImpl.execute(QuoteRequest)
  → JMSHandler.getDFAPIResponse(QuoteRequest)
    → XMLHandler.getXML(QuoteRequest) [serialize to XML]
    → MQJMS.executeSendMessage(xml, props, jmsHeaderVO)
      [PUT to IBM MQ queue: queueMgr=GU00, queue=CPS.DF.RQ1]
    → MQJMS.executeReceiveMessage(correlationId) [GET response]
    → XMLHandler.getResponse(responseXML) [deserialize XML]
  ← QuoteResponse
```

---

## 6. Compliance Relevance

- **Dodd-Frank / Reg E §1005.31**: Core purpose — this library is the implementation vehicle for international remittance disclosure compliance.
- **PCI DSS**: No card data in this library; financial amounts and routing codes only.
- **OFAC**: Destination country/bank routing data flows through this API; the upstream service (Citi DFAPI) is expected to perform OFAC screening.

---

## 7. Risks

| Risk | Severity | Detail |
|---|---|---|
| Citi DFAPI dependency | Critical | Library connects to `citigroupsoa.citigroup.com` — an external Citi Group endpoint; Onbe's operational continuity depends on Citi's API availability |
| TrustAllSSLSocketFactory in WSDL stub | High | `TrustAllSSLSocketFactory.java` in `dfapiclient-impl` disables SSL certificate verification for the SOAP connection — violates PCI DSS Req 4.2.1 |
| Test properties contain internal endpoints | Medium | `httpclient.properties` contains `http://dflnxswapu.nam.nsroot.net:7990/` and `https://citigroupsoa.citigroup.com/` — committed to repo |
| IBM MQ credentials not in repo | Low | JMS properties contain hostname/port/queue but no username/password visible; credential management unknown |
| Apache Axis 1.x (end-of-life) | High | WSDL stub generated with Apache Axis 1.4 (2006); Axis 1.x is EOL; no security patches available |
| JAXB generated 2013 — stale | Medium | `QuoteRequest.java` generated 2013-04-22; WSDL changes would not be automatically reflected |
