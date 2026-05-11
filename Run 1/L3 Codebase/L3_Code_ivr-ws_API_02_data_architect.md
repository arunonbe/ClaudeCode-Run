# Data Architect Analysis — ivr-ws_API

## 1. Database Architecture

The `ivr-ws_API` service accesses **one primary database** via JNDI datasource:

**`CbaseappDataSource`** (`ivrapi-ws/src/main/resources/datasourceContext.xml`):
```xml
<bean id="CbaseappDataSource" class="org.springframework.jndi.JndiObjectFactoryBean">
    <property name="jndiName">
        <value>java:comp/env/jdbc/CbaseappDataSource</value>
    </property>
</bean>
```
The `cbaseapp` database is the Gen-1 cardholder authentication and account database. In the `ivrapi-boot` module, the datasource is configured via Spring Boot externalized config (`application.yml` lines 12–16).

The majority of data access goes through the **eCount Core XML-RPC service layer** (not directly to SQL Server), via the `xplatform` library. The `ivrapi-boot` module also connects to the **Director service** for dynamic endpoint resolution (`director-client.yaml`).

## 2. Domain Model

### 2.1 Common Data Transfer Objects (`ivrapi-ws/src/main/java/com/ecount/one/ivr/common/`)

**`BalanceDetail`** — Account balance data:
- `balance_available` — available balance (decimal)
- `balance_ledger` — ledger balance
- `balance_pending` — pending balance

**`CardDetail`** (`CardDetail.java`) — Card account information:
- `card_number` — **PCI SENSITIVE: card PAN** — partially masked in `AccountTransactionInquiryServiceImpl.java` line 83: `"XXXXXXXX" + cardNumber.substring(8)` (last 4 shown)
- `account_status` — card status (active/closed/frozen/lost)
- `expiration` — card expiry date (`expMonth + "/" + expYear`) — **PCI SENSITIVE**
- `created_date` — card creation date
- `last_plastic_date` — last physical card issued date
- `program_id` — program identifier (integer)
- `puid` — partner user ID (employer-assigned employee identifier)

**`AchDetail`** — ACH bank account data:
- Contains bank account type, routing information
- **NACHA SENSITIVE**: Bank routing and account numbers

**`SecurityDetail`** (`SecurityDetail.java`) — IVR caller authentication data:
- `phoneNumbers` — ArrayList of registered phone numbers — **PII**
- `zipcode` — cardholder ZIP code — **PII**

**`TransactionDetail`** — Transaction history entry:
- `transaction_date`
- `transaction_amount` — **FINANCIAL**
- `transaction_fee` — **FINANCIAL**
- `transaction_details` — description
- `transaction_type` — type code

**`PPDDetail`** — Payment/transaction addenda (key-value pairs from ACH addenda)

**`ClaimDetail`** — Claimable payment details

**`Response`** / `ResponseStatus` — Base response with completion code and message

### 2.2 Service Response Objects (`ivrapi-ws/src/main/java/com/ecount/one/ivr/service/response/`)

| Response Class | Key Data Returned |
|---|---|
| `AccountBalanceInquiryResponse` | `BalanceDetail` (available, ledger, pending balances) |
| `AccountTransactionInquiryResponse` | `CardDetail` (masked card number) + `TransactionDetail[]` array |
| `AchAccountSetupResponse` | Setup result code |
| `AchInquiryResponse` | ACH account detail |
| `AchTransferSetupResponse` | Transfer setup result |
| `ClaimablePaymentResponse` | Claim detail |
| `MobilePhoneInquiryResponse` | `mobile_phone` string |
| `MobilePhoneUpdateResponse` | Update result |
| `ServiceResponse` | Base with response code and message |

## 3. PCI/Sensitive Data Flags

### 3.1 CRITICAL: Card Number in Memory

`CardDetail.card_number` holds the **full card PAN** as received from eCount Core (`AccountTransactionInquiryServiceImpl.java` line 82: `String cardNumber = accountDefinitionECard.getCreditCard().getNumber()`). While the PAN is masked before returning to the IVR caller (line 83), the full PAN exists in application memory during the request lifecycle. This requires the application server to be within the CDE under PCI DSS scope.

### 3.2 HIGH: Card Expiry Date

`CardDetail.expiration` is set with `expMonth + "/" + expYear` (line 93) — full card expiry. Expiry date is Sensitive Authentication Data (SAD) under PCI DSS Requirement 3.3. Its presence in the IVR response means the IVR system and cardholder receive the expiry date. This is acceptable for card self-service but the data must not be stored or logged.

**Check for logging**: The `CardDetail.toString()` method (lines 213–229) includes `<expiration>` in the string representation. If any logging uses `CardDetail.toString()`, the expiry date appears in logs.

### 3.3 HIGH: Bank Account Number in ACH Setup

`AchAccountSetupServiceImpl.java` receives `bank_account_number` as a plain string parameter (line 20). This is transmitted from the IVR (via DTMF keypresses) through this service to eCount Core. Full bank account numbers are **sensitive financial data** under NACHA Rule ODFI requirements. They must not appear in logs.

**Log risk**: `AchAccountSetupServiceImpl.java` lines 29–33 show commented-out debug log statements for `bank_Account_Number` and `bank_Routing_Number`. These were previously being logged and were commented out — confirming that log exposure of bank data was a past practice. Audit all other log points for similar issues.

### 3.4 HIGH: Mobile Phone Number

`MobilePhoneNumberServiceImpl.java` line 196:
```java
Object[] parameters = {getLogger().getName(), card_number, mobilePhoneNumber};
logSysMessage("mobilephone.syslog.update.message", parameters);
```
The mobile phone number is logged in a system log message (along with card_number) when a mobile phone update occurs. Card number + phone number combination is PII + CHD in the same log entry.

### 3.5 MEDIUM: `SecurityDetail` Authentication Data

`SecurityDetail` holds phone numbers and ZIP code used for IVR authentication. This data is retrieved from eCount Core and used for caller verification. If logged, phone numbers and ZIP codes appear in logs. Confirm that `SecurityDetail.toString()` (which includes `phoneNumbers` and `zipcode`) is not passed to any logger.

## 4. Data Flow

```
IVR Telephony System (cardholder on phone)
    → DTMF input: card_number, PIN (telephony layer), bank_account_number, etc.
    → SOAP call to ivr-ws_API (ivrapi-ws SOAP services via JAX-RPC)
        → Input validation (validator.xml beans)
            → ServiceImpl / AccountServiceImpl / AchServiceImpl
                → populateAccount() → XML-RPC to eCount Core
                → processDeviceInquiry() → XML-RPC to eCount Core
                → memberManager.InquiryBasic/Extended() → XML-RPC
                → deviceManager.createACH/updateACHBankInfo() → XML-RPC
                    → eCount Core Databases (cbaseapp, ecountcore)
```

## 5. Datasource Configuration

In `ivrapi-boot` (Spring Boot module):
- `application.yml` lines 12–16: datasource credentials via `url-from-app-config` / `username-from-app-config` / `password-from-app-config` — externalized to Azure App Configuration at runtime
- `CbaseAppDataSourceAutoConfiguration.java` — auto-configures the cbaseapp datasource in the Spring Boot context
- `DataSourceConfig.java` — additional datasource configuration

In `ivrapi-war` (legacy WAR):
- `META-INF/context.xml` — Tomcat context with JNDI DataSource configuration
- `datasourceContext.xml` — Spring JNDI lookup

## 6. JAX-RPC WSDL / Service Contracts

`wsdl.xml` at repo root — the WSDL contract for the IVR SOAP web services. This defines the formal contract between the IVR telephony platform and this service. The WSDL is published to Azure API Management (APIM) per the deployment workflow.

JAX-RPC service endpoint classes in `ivrapi-ws/src/main/java/com/ecount/one/ivr/service/jaxrpc/`:
- `JaxRpcAccountBalanceInquiryService`
- `JaxRpcAccountTransactionInquiryService`
- `JaxRpcAchAccountSetupService`
- `JaxRpcAchInquiryService`
- `JaxRpcAchTransferSetupService`
- `JaxRpcClaimablePaymentService`
- `JaxRpcMobilePhoneService`

These are the JAX-RPC endpoint implementations that bridge the SOAP layer to the service implementations.
