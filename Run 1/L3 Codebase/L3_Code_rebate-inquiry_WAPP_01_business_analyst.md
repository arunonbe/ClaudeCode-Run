# Business Analyst Analysis: rebate-inquiry_WAPP

## Business Purpose
rebate-inquiry_WAPP is a consumer-facing Java EE web application that allows end-users to submit an inquiry about an undelivered rebate card or prepaid debit card. When a cardholder has not received their rebate or prepaid card, they fill in a web form and the application dispatches an email notification to the program's fulfillment/customer-service address so that the issue can be investigated.

The application was originally branded under Citi Prepaid / Northlane / eCount and is now operated by Onbe. It handles two distinct card product types:
- Rebate cards (VZ/Verizon-branded undelivered card inquiry — `RebateCardInquiryAction`)
- Prepaid debit cards (`PrepaidDebitCardInquiryAction`)

## Capabilities
1. Present a web form collecting cardholder name, address, phone, email, state, and free-text comments.
2. Validate form input via Apache Struts 1 Validator.
3. On submission, compose and send an email notification using the legacy `NotificationManagerImpl` (cbase platform library).
4. Support SSL redirect enforcement via `SSLRedirectFilter` (redirect HTTP on port 80 to HTTPS).
5. Populate US state drop-down list from servlet context cache.
6. Load program-specific configuration (member ID, program ID, agent ID, recipient email) from an external properties file at `D:/c-base/config/rebate-cardinquiry/rebate.properties`.

## Key Business Entities
| Entity | Description |
|---|---|
| InquiryForm | Cardholder contact information: name, address1/2, city, state, zip, phone, email, comments |
| RebateCardInquiryForm | Extends InquiryForm; bound to rebate card program |
| PrepaidDebitCardInquiryForm | Extends InquiryForm; bound to prepaid debit card program |
| PropertiesContextListener | Spring bean holding program-level config loaded from properties file: agent, memberId, programId, recipientEmail |

## Business Rules
- SSL check is active (`check=on` in web.xml filter); HTTP requests on port 80 are redirected to HTTPS.
- Session timeout is 20 minutes.
- Email sender address is set to the submitting user's email address (form.getEmail() is used as senderFromEmail).
- Member ID, Program ID, Agent, and recipient email are injected from the external properties file at startup; they are not entered by the user.
- Application is stateless from a card data perspective — no card numbers are stored or transmitted through this application.

## Business Flows
1. User navigates to the inquiry form (`/rebate.do` or `/prepaidDebitCardInquiry.do`).
2. SSLRedirectFilter enforces HTTPS; US states are loaded into servlet context cache.
3. User fills in the form and submits.
4. Struts validator validates required fields.
5. Action class loads program config from Spring context (PropertiesContextListener).
6. NotificationHelper builds an email template and calls `EmailNotification.sendEmail()` via the cbase `NotificationManagerImpl`.
7. On success, user is forwarded to a success page.

## Compliance Relevance
- Collects PII (name, address, phone, email) from cardholders — subject to CCPA, GDPR Article 13 notice obligations.
- Does not collect or transmit PANs, CVVs, or track data — outside direct PCI DSS CDE scope, but is reachable over the internet and must be hardened.
- No authentication mechanism is present; form is publicly accessible.
- External properties file at a hard-coded Windows path (`D:/c-base/config/...`) represents an operational configuration risk.

## Risks (Business Perspective)
- **No CAPTCHA or rate limiting**: The public form is vulnerable to automated spam/abuse.
- **No cardholder identity verification**: Anyone can submit an inquiry for any address; potential for social engineering.
- **Hard-coded file system paths** in both `web.xml` (log4j config) and `applicationContext.xml` (properties file) tie the application to a specific server directory structure.
- **Email spoofing exposure**: Recipient email is configurable only via properties file; mis-configuration could misdirect sensitive inquiry notifications.
