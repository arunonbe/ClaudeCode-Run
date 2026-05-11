# Data Architect Report — mpv (My Payment Vault)

## 1. Data Architecture Overview

The `mpv` repository as inspected contains **only mock data** — no application source code, build configuration, or deployment artifacts were found. The repository's `mock-data/` directory and the `locaMockData.js` file represent the front-end's local development mock API layer. This is a JavaScript front-end application (likely React or Angular, given the `.js` mock data loader) that uses a mock server pattern during development to simulate backend API responses.

The real application code is not present in this repository snapshot. The analysis is therefore based entirely on the mock data, which faithfully represents the API contract between MPV and its backend services.

## 2. API Data Contract Analysis

### Authentication Data (`mock-data/login/login.json`)

```json
{
  "cardToken": "eyJjdHkiOiJ0ZXh0XC...",   // JWE encrypted card token
  "authToken": "eyJhbGciOiJIUzI1NiJ9...", // JWT auth token
  "refreshToken": "eyJhbGciOiJIUzI1NiJ9..." // JWT refresh token
}
```

The login response returns three tokens:
- `cardToken`: A JWE (JSON Web Encryption) token — the `eyJjdHkiOiJ0ZXh0XC9wbGFpbiIsImVuYyI6IkEyNTZHQ00iLCJhbGciOiJkaXIifQ` header decodes to `{"cty":"text/plain","enc":"A256GCM","alg":"dir"}`, confirming AES-256-GCM encrypted content using direct key agreement. This suggests card-sensitive data is encrypted within this token.
- `authToken`: A HS256-signed JWT with `sub` containing a member GUID, `iat`, and `exp` (validity window of ~10 minutes based on mock timestamps).
- `refreshToken`: A HS256-signed JWT with a longer `exp` (validity window of ~60 minutes based on mock timestamps).

The **10-minute access token / 60-minute refresh token** window is observable from the mock JWT payloads. This is a short-lived token pattern consistent with modern OAuth2 best practices for consumer-facing applications.

### Card Data (`mock-data/dashboard/dashboardDetails.json`, lines 80-90)

The dashboard API returns card details directly in the response payload:

| Field | Value in Mock | PCI Classification |
|---|---|---|
| `cardNumber` | `5445446585725838` (full PAN) | SAD — must be masked |
| `cvv` | `77` | SAD — must never be stored or returned |
| `expirationDate` | `05/2026` | SAD |
| `balance` | `98567` | Non-PAN cardholder data |
| `accountHolderName` | `Someshkumar Velusamy` | Cardholder data |

The presence of a full PAN and CVV in a dashboard API response is a **critical PCI DSS finding**. PCI DSS Requirement 3.3 prohibits storing SAD after authorization, and Requirement 3.4 requires PAN to be rendered unreadable anywhere it is stored. If the production API mirrors this mock response, this is a Requirement 3 violation. The mock response should be replaced with masked PAN (`555555XXXXXX5838`) and the CVV field removed entirely.

### Claim Code Data (`mock-data/claimCode/validateClaim.json`)

The claim validation response returns `authenticationType`, `authenticationValue`, and `registered` — a minimal response confirming claim code validity without returning the payment amount or recipient details directly. This is a privacy-preserving design.

### Recipient PII Data (`mock-data/registration/submitRegistration.json`, `contact/contactSubmit.json`)

Registration and contact flows collect name, email, address, and phone — standard CCPA/GDPR personal data categories. No SSN, full DOB, or financial account numbers are apparent in the mock registration flow, which is consistent with a registration process that links to an existing claim code (which already carries identity verification).

## 3. Front-End State and Session Architecture

Based on the mock data structure, MPV maintains the following data in client state:
- Auth tokens (likely in `sessionStorage` or a secure HttpOnly cookie)
- Card token (JWE, required for card operations)
- Affiliate/branding configuration (`branding/affiliateVanity.json`)
- Locale/copy tags (`commonData/copyTag.json`)
- Dashboard state (card details, transaction list, unclaimed payments)

## 4. Data Flows to Backend Services

| MPV Feature | Backend Service |
|---|---|
| Login, registration | `nexpay-auth-svc` (Entra External ID) |
| Claim code validation | `nexpay-claim-code-svc` |
| Payment selection/choice | Order orchestrator or claim code svc |
| Card dashboard | `nexpay-cardprocessor-svc` |
| Bank transfer, FX transfer | ACH and cross-border transfer services |
| Push to debit | Push-to-card service |
| PayPal, Venmo | Third-party wallet integration services |
| Profile, contact info | Account management service |
| Notifications/messages | `message-center_SVC` (Gen-2) |

## 5. Data Risks

1. **Full PAN in mock data** (`dashboardDetails.json` line 86): Must be replaced with a test BIN value before any public or shared repository access.
2. **CVV in mock data** (`dashboardDetails.json` line 87): Must be removed. CVV must never appear in any data store, log, or API response.
3. **Hardcoded mock tokens**: The `authToken` and `refreshToken` in `login.json` are JWTs with real-looking (but mock) data — any automated secret scanning tool will flag these as potential leaked credentials.
4. **Unclaimed transaction verification codes**: The `dashboard/dashboardDetails.json` contains `verificationCode` values (lines 97-113) that look like claim codes. These should use obviously synthetic values.
