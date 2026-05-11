# Data Architect Analysis: rebate-inquiry_WAPP

## Data Stores
| Store | Type | Purpose |
|---|---|---|
| `D:/c-base/config/rebate-cardinquiry/rebate.properties` | Flat file (filesystem) | Holds program config: agent, memberId, programIds, recipient email addresses, xcontent path |
| `D:/c-base/config/rebate-cardinquiry/log4j.xml` | Flat file (filesystem) | Log4j logging configuration |
| Email transport (JavaMail via cbase NotificationManagerImpl) | Outbound only | Delivers form submissions to configured recipient address |

No relational database tables are read or written by this application directly. The application is entirely stateless from a persistence perspective — it reads config from a properties file at startup and sends emails at runtime.

## Schema / Tables
None. This application does not own any database schema.

It depends on the cbase `NotificationManagerImpl` which may internally reference the cbase/ecountcore database for member lookup (the `Member` object is constructed from a memberId string at `NotificationHelper:36`), but the database interaction is entirely within the cbase library, not owned by this repo.

## Sensitive Data Handled
| Data Element | Classification | Notes |
|---|---|---|
| Cardholder full name | PII | Entered in form, included in notification email body |
| Cardholder address (address1, address2, city, state, zip) | PII | Entered in form, included in email |
| Cardholder phone number | PII | Entered in form, included in email |
| Cardholder email address | PII | Entered in form; also used as the email sender address |
| Program memberId | Internal config | Loaded from properties file; identifies the program/client |
| Recipient email | Internal config | Target address for notification emails |

No PANs, CVVs, SSNs, or account numbers are collected, stored, or transmitted.

## Encryption
- No at-rest encryption is implemented within this application.
- Transport encryption relies entirely on the SSLRedirectFilter enforcing HTTPS (redirect from port 80 to HTTPS).
- The properties file (`rebate.properties`) containing program configuration is stored unencrypted on the local filesystem.
- Log files written via Log4j are unencrypted.

## Data Flow
```
User browser (HTTPS) 
  --> SSLRedirectFilter (HTTP -> HTTPS redirect) 
  --> Struts ActionServlet 
  --> RebateCardInquiryAction / PrepaidDebitCardInquiryAction 
  --> NotificationHelper.sendVZUndeliCardInqNotification() 
  --> EmailNotification.sendEmail() 
  --> NotificationManagerImpl (cbase library) 
  --> JavaMail --> SMTP server --> Recipient mailbox
```
PII entered in the form travels in-process (in-memory) to the email body. No intermediate persistence occurs.

## Data Quality / Retention
- No data retention policy is implemented within this application — form data exists only in-flight (HTTP request scope and email body).
- Email delivery success/failure is caught and logged at error level but not persisted; failed notifications are silently lost (`catch (Exception e) { log.error(...) }` in `RebateCardInquiryAction:91`).
- No duplicate-submission prevention exists.

## Compliance Gaps
1. **CCPA / GDPR Notice**: The form collects PII with no visible privacy notice or consent mechanism in the code.
2. **Data minimisation**: Phone number and address are collected but it is unclear if they are all required to resolve an undelivered card inquiry.
3. **Email as data transport**: PII is transmitted via email without guaranteed encryption in transit (depends on SMTP server TLS configuration outside this repo).
4. **No data deletion pathway**: Collected PII resides in recipient email inboxes with no defined retention or deletion process owned by this application.
5. **Unencrypted properties file**: Recipient email addresses and program identifiers stored in plaintext on the server filesystem.
