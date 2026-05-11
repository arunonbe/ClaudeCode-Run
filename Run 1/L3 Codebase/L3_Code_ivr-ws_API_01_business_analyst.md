# Business Analyst Analysis — ivr-ws_API

## 1. System Overview

`ivr-ws_API` is the **general-purpose IVR (Interactive Voice Response) web service** for the Onbe prepaid card platform. Per `README.md`: "A cost-effective 24/7 technology that handles high-volume call traffic into our service centers. It also allows cardholders to access their prepaid account information via a telephone keypad." Artifact ID: `ivrws`, version `3.0.2-SNAPSHOT`. Unlike `ivrintegration_API` (check-cashing only), this service covers the full range of cardholder self-service IVR interactions.

This is a multi-module Maven project with three sub-modules:
- `ivrapi-ws` — service implementation layer (Spring/JAX-RPC SOAP services)
- `ivrapi-war` — legacy WAR packaging for Tomcat deployment
- `ivrapi-boot` — modern Spring Boot 3.x packaging for containerized deployment (Docker/Kubernetes)

The parallel presence of `ivrapi-war` and `ivrapi-boot` indicates an **active migration from traditional WAR deployment to Spring Boot container deployment** is in progress.

## 2. IVR Menu Options and Cardholder Functions

The service exposes the following IVR capabilities, mapped directly to GitHub Actions deployment workflows in `.github/workflows/`:

### 2.1 Account Balance Inquiry (`AccountBalanceInquiryServices`)
**File**: `AccountBalanceInquiryServiceImpl.java`
**Method**: `balanceInquiry(application_id, card_number)`

Allows cardholders to check their prepaid card balance via IVR keypad. Returns:
- `balance_available` — available balance
- `balance_ledger` — ledger balance
- `balance_pending` — pending balance

This is the most-used IVR option for prepaid cardholders.

### 2.2 Account Transaction Inquiry (`AccountTransactionInquiryServices`)
**File**: `AccountTransactionInquiryServiceImpl.java`
**Method**: `transactionInquiry(application_id, card_number, journal_detail, start_date, end_date, max_items)`

Returns recent transaction history. Per `AccountTransactionInquiryServiceImpl.java` lines 81–83:
```java
String cardNumber = accountDefinitionECard.getCreditCard().getNumber();
accountTransactionInquiryResponse.getCard().setCard_number("XXXXXXXX" + cardNumber.substring(8));
```
The card number is partially masked (first 8 digits replaced with X, last 4 retained) before returning to the IVR. Returns `TransactionDetail[]` array with `transaction_date`, `transaction_amount`, `transaction_fee`, `transaction_details`, and `transaction_type`.

### 2.3 ACH Account Setup (`AchAccountSetupServices`)
**File**: `AchAccountSetupServiceImpl.java`
**Method**: `achAccountSetup(application_id, card_number, bank_account_type, bank_name, bank_routing_number, bank_account_number)`

Allows cardholders to set up or update a linked bank account (ACH) for direct deposit or fund transfer. Creates or updates the bank account record with:
- `bank_routing_number` — ABA routing number
- `bank_account_number` — bank account number (full)
- `bank_account_type` — checking or savings

**PCI/Regulatory Flag**: Full bank account number is transmitted through the IVR DTMF interface and stored. This is sensitive financial data under NACHA, Reg E, and GLBA. DTMF masking is critical to prevent capture of bank account numbers.

### 2.4 ACH Inquiry (`AchInquiryServices`)
**File**: `AchInquiryServiceImpl.java`

Returns the current linked bank account details for a cardholder.

### 2.5 ACH Transfer Setup (`AchTransferSetupServices`)
**File**: `AchTransferSetupServiceImpl.java`

Allows cardholders to initiate or configure ACH fund transfers from their prepaid card.

### 2.6 Claimable Payment Services (`ClaimableServices`)
**File**: `ClaimablePaymentServiceImpl.java`

Handles "claimable" payments — where a cardholder claims a disbursement (insurance, refund, incentive). The `ClaimDetail` object (`ivrapi-ws/src/main/java/com/ecount/one/ivr/common/ClaimDetail.java`) captures claim-specific data.

### 2.7 Mobile Phone Services (`MobilePhoneServices`)
**File**: `MobilePhoneNumberServiceImpl.java`
**Methods**: 
- `mobilePhoneInquiry(application_id, card_number)` — retrieves registered mobile phone number
- `mobilePhoneUpdate(application_id, card_number, mobile_phone)` — updates mobile phone number

Returns or updates the `MOBILE` phone type from `ExtendedRegistrationPhone`. The area code and number are split and stored separately.

### 2.8 Default / General Account Service
**File**: `AccountServiceImpl.java`, `ServiceImpl.java`

Base class for all account services. Core methods:
- `populateAccount()` — looks up account by card number
- `processDeviceInquiry(member, balance, journal, acl)` — queries eCount Core for device/member data

## 3. Cardholder Authentication in IVR

The `SecurityDetail` class (`SecurityDetail.java`) carries:
- `phoneNumbers` — list of registered phone numbers
- `zipcode` — ZIP code for caller verification

This suggests the IVR uses **ANI (caller ID) match** or **ZIP code entry** as the cardholder authentication factor. No PIN verification is visible in these service classes — PIN verification may occur at the IVR telephony platform layer (DTMF PIN collected and verified separately) or at a different service endpoint not visible in this repository.

**Security Note**: If ANI matching is used as the sole authentication factor, this is insufficient for operations like ACH setup (full bank account number exposure). IVR security for financial operations should require at minimum: card number + PIN or card number + ZIP + last 4 SSN.

## 4. Business Verticals Served

The service handles multiple application IDs (validated by `applicationIdValidator`), each corresponding to a specific prepaid card program or client. The `BrandedCurrencyConfig` in the boot module (`ivrapi-boot/src/main/java/com/citi/prepaid/ivrapi/config/BrandedCurrencyConfig.java`) suggests support for branded currency (rewards points) programs as well as standard prepaid.

## 5. Deployment Environments

App config files in `ivrapi-boot/app-config/`:
- `prod/appsettings.json` — production configuration
- `qa/appsettings.json` — QA configuration  
- `staging/appsettings.json` — staging configuration

## 6. Regulatory Relevance

| Regulation | Applicable Features | Notes |
|---|---|---|
| Reg E | All IVR financial operations | Error resolution, dispute rights must be accessible |
| NACHA | ACH setup and transfer | Account validation, prenote requirements |
| GLBA | All PII/financial data | Safeguards rule applies |
| PCI DSS | Card number, balance inquiry | Card number in-scope; masking applied in `AccountTransactionInquiryServiceImpl` |
| CCPA/GDPR | Mobile phone, name, address data | `mobilePhoneUpdate` updates contact PII |
