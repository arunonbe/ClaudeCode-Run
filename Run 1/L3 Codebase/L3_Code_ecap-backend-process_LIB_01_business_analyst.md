# ecap-backend-process_LIB — Business Analyst Report

## Repository Overview

`ecap-backend-process_LIB` is the **ECAP (Electronic Card Activation Portal) backend processing library**, a Java library that provides the core business logic for multi-threaded batch card creation and activation. The library is responsible for the end-to-end orchestration of creating prepaid gift card accounts, loading them with value, linking purchasers to recipients, and sending success or failure email notifications.

The artifact is `ecap-card-creation-impl` version `2.0.0-SNAPSHOT` (`pom.xml`, line 15), inheriting from `com.citi.prepaid:prepaid-parent:3` — indicating this was originally developed under a Citibank/prepaid sponsorship context and has been maintained as part of the Onbe East platform.

The library is a Gen-1 component compiled for Java 1.7 (`pom.xml`, lines 153–154) using Spring 2.0.8 (`pom.xml`, line 35) and communicates with SQL Server via JTDS JDBC (legacy) and the Microsoft JDBC 6.4 driver.

---

## Business Purpose

### Core Function: Batch Gift Card Creation and Activation
The library processes **card creation requests** in a batched, multi-threaded manner. The business scenario is:
1. A purchaser (parent/sponsor) submits a request to issue a prepaid gift card to a recipient
2. The ECAP system queues that request
3. This library processes the queue: creates a DDA (Demand Deposit Account) or gift card account, creates the member profile, loads the card value, links the purchaser to the recipient, and notifies both parties

### Key Business Capabilities

1. **Card Account Creation** — `CreateGiftCardState.java` creates the actual prepaid card account in the eCount core system
2. **DDA Account Creation** — `CreateDDAState.java` creates a demand deposit account variant
3. **Member Creation** — `CreateMemberState.java` creates the cardholder member profile
4. **Fund Transfer** — `DDAToDDAFundTransferState.java` handles DDA-to-DDA fund transfers (likely for rewards/reload scenarios)
5. **Purchaser-Recipient Linking** — `PurchaserRecipientLinkState.java` associates the card purchaser with the recipient for notification and audit purposes
6. **Email Notifications** — `EcapEmailNotificationImpl.java` sends success notifications to recipients and failure notifications to purchasers
7. **Automated Comments** — `AutoComment.java` / `JDBCCommentor.java` write workflow audit comments to the database
8. **CyberSource Integration** — Test class `CyberSourceCheckTest.java` indicates payment validation against CyberSource (Visa's payment gateway) is part of the workflow

---

## Business Workflow

The library implements a **state machine pattern** (`StateMachine.java`, `AbstractEcapProcessState.java`) for card creation. The execution flow:

```
EcapCardCreationClient.main()
    └─► EcapCardCreationProcessImpl.run()
           └─► IRequestProducer.getRequests() → fetch pending card requests
               └─► For each batch of CardRequests:
                      └─► IRequestConsumer.processRequest()
                             └─► CardRequestHandler (per thread)
                                    └─► StateMachine transitions:
                                           1. CreateMemberState
                                           2. CreateGiftCardState OR CreateDDAState
                                           3. DDAToDDAFundTransferState (if applicable)
                                           4. PurchaserRecipientLinkState
                                           5. EndState
                                    └─► On success: sendEmailNotificationToRecipient()
                                    └─► On failure: sendFailureConfirmationToPurchaser()
```

---

## Data Entities Processed

### Recipient (Core Entity)
`Recipient.java` (lines 14–51) carries all cardholder-facing data:
- Personal: `first_name`, `middle_name`, `last_name` (PII)
- Address: `address1`, `address2`, `city`, `zip_code`, `state_code`, `country_code` (PII)
- Contact: `email_id` (PII)
- Card: `card_value`, `card_type`, `emboss_message`
- Logistics: `shipping_method`, `plastic_fee`, `shipping_fee`, `ship_to`
- Program: `affiliate_id`, `program_id`, `locale`, `locale_id`
- Control: `status_code`, `process_counter`, `access_level`

### CardRequest (Process State Carrier)
`CardRequest.java` — wraps a `Recipient` plus processing metadata: `parent_member_id`, `parent_email_lang`, processing state flags.

---

## Business Rules

1. **Multi-language Notification** — The library supports English and Spanish email notifications based on `email_language` field. `EcapEmailNotificationImpl.java` (lines 52–68) branches on `LANGUAGE_CODE_ENGLISH` vs Spanish.
2. **Ship-To-Me vs Ship-To-Recipient** — Different delivery method text is applied based on `shipTo` field (`EcapProcessConstants.SHIP_TO_ME`). This drives physical card shipping workflow.
3. **Batch Size Control** — `EcapCardCreationProcessImpl.java` (line 50) processes requests in configurable batches, controlled by `batchsize` property.
4. **Thread Pool Execution** — `CardRequestExecutor.java` uses Spring's `ThreadPoolTaskExecutor` for concurrent card processing, with queue capacity dynamically set to the number of pending requests.
5. **Process Counter Tracking** — `Recipient.process_counter` tracks retry count for each request; `EcapUpdateProcessCounterAndStatusCodeStoreProc.java` updates this in the database.
6. **Comment Automation** — `AutoComment.java` writes audit trail comments to the database for each state transition, supporting regulatory audit trail requirements.
7. **CSA Inquiry Category** — `GetCsaInquiryCategoryByInquiryType.java` / `GetCsaInquiryCategoryByInquiryTypeValue.java` indicates Customer Service Agent (CSA) inquiry categorization is part of the workflow.

---

## Regulatory Relevance

### PCI DSS
- The library creates card accounts in the eCount core system — it is part of the Card Data Environment (CDE) boundary.
- `Recipient.java` holds full name and address but not PANs. PANs are handled by the downstream eCount core system.
- `EcapRecipientDaoImpl.java` (9,641 bytes — largest DAO) executes SQL queries against the recipient data store. PCI DSS Requirement 6.2 (secure development practices) and Requirement 10 (logging) apply.

### Reg E
- Card load events processed by this library constitute electronic fund transfers under Reg E. Error handling (failure notifications via `FailureNotificationToCardPurchaser.java`) must provide sufficient detail for Reg E §1005.11 error resolution.

### GLBA
- Name, address, and email of cardholders processed by this library constitute nonpublic personal information (NPI) under GLBA, requiring appropriate safeguards during processing.

### NACHA
- DDA creation (`CreateDDAState.java`) and DDA-to-DDA fund transfers (`DDAToDDAFundTransferState.java`) involve ACH-linked accounts. NACHA Rules apply to authorization and transfer processing.
