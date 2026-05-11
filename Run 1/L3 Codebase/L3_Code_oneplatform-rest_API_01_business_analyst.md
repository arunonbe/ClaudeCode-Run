# Business Analyst — oneplatform-rest_API

## Business Purpose
The OnePlatform REST API is the primary backend BFF (Backend-for-Frontend) for the MyPaymentVault cardholder self-service portal (mypaymentvault.com). It enables prepaid card recipients to authenticate, view their card balance and transaction history, and execute a wide variety of payment disbursement and fund-access flows including ACH bank transfer, push-to-debit, PayPal, Venmo, Western Union, Ria, IEFT (International Electronic Funds Transfer / cross-border), web-to-wallet provisioning, and card ordering/activation.

## Capabilities
- **Authentication**: Login, logout, SSO login, forgot username/password, MFA (OTP) generation and validation, OTP grace period management.
- **Registration**: Card validation, user registration, extended registration, cardholder profile management.
- **Dashboard**: Card status display, card status change notifications.
- **Transactions**: Transaction history, unclaimed transaction history, display formatting.
- **Claimable Choice**: First-time payment selection (prepaid card, ACH, PayPal, Venmo, push-to-debit), returning user re-selection, claim code redemption.
- **Payment Hub (Choice)**: Multi-rail payment method orchestration for claimable payouts.
- **Bank Transfer (ACH)**: Save bank details, one-time and automatic ACH transfer initiation and confirmation.
- **Debit Transfer (Push-to-Debit)**: Push funds to a debit card via Tabapay, OTT (one-time token) flow, recurring push-to-debit.
- **Off-Card Transfer (PayPal / Venmo)**: OAuth connection, payout initiation, status callback via Dapr pub/sub outbox.
- **IEFT**: International bank transfer (cross-border), FX rate inquiry, IBAN validation, bank search, auto-claim allotments.
- **RIA Money Transfer**: Token save and initiation.
- **Western Union**: Transfer integration.
- **Card Activation**: Card activation, PIN change.
- **Order**: Order card, order check, request check response, update address.
- **Disclosures**: Display program disclosures and properties.
- **My Account / My Profile**: Profile detail retrieval, state list, country list.
- **Web-to-Wallet**: Apple Pay / Google Pay push provisioning.
- **GeoIP**: IP geolocation check via Dapr-invoked `geoipservice`.
- **BioCatch**: Behavioral biometric risk scoring integration.
- **Google reCAPTCHA Enterprise**: Anti-bot validation for login and registration.
- **Feature flags**: Azure App Configuration-based feature flag evaluation.

## Key Entities
- **Affiliate / Skin**: Program-branded configuration (read from Redis, written by admin service).
- **Card**: Prepaid card details, status, balance, token.
- **User / Cardholder**: Authentication context, profile, terms & conditions, ecard ID.
- **Transaction**: History records, display formatting, unclaimed payments.
- **Bank Details**: ACH routing and account numbers (DDA).
- **Payment Selection**: Claimable choice options (card, ACH, PayPal, Venmo, Debit, IEFT, etc.).
- **Claim Code**: Redemption tokens for claimable disbursements.
- **Program Setup**: Currency, bank, international flag, platform (read from Redis via programSetting key).
- **JWT Token**: Access token (10-minute expiry) and refresh token (60-minute expiry), HS256.

## Business Rules
- OTP is required on login (`security.otpRequired=Y`) with a 30-minute grace period.
- JWT access tokens expire in 10 minutes; refresh tokens in 60 minutes.
- IEFT accounts limited to 6 per cardholder (`ieft.acountLimit=6`); minimum 90 days before removal eligibility.
- BioCatch behavioral risk scoring applied; accounts denied if score reaches 1000.
- Google reCAPTCHA Enterprise score threshold: 0.6 (reject below).
- Mobile app token version list controls which app versions are accepted.
- ACH prepaid account masking enabled in IEFT flows (`ieft.maskPrepaidAcount=true`).
- Western Union integration uses a static shared key (`westernunion.statickey` — see security risks).
- PayPal and Venmo operator IDs differ between environments.

## Key Flows
1. **Login**: `POST /login` → validate credentials via xplatform/ecount → check OTP grace period → issue JWT access + refresh token.
2. **Payment Selection (Claimable)**: `POST /claimableChoice/onload` → read affiliate from Redis → resolve available payment rails → present options → `POST /claimableChoice/selection` → record choice via Dapr or XMLRPC.
3. **ACH Transfer**: `POST /bankTransfer/saveDetails` → `POST /bankTransfer/oneTimeTransfer` → `POST /bankTransfer/confirm`.
4. **PayPal Payout**: Redirect to PayPal OAuth → `POST /offCard/paypal/payout` → Dapr sidecar invokes `ompaypalredemptionsvc`.
5. **IEFT Cross-Border**: FX rate inquiry → bank search / IBAN validation → `POST /ieft/performOTT` → confirm via `cbtsClient`.
6. **Card Activation**: `POST /cardActivation/activate` → PIN submission via `POST /cardActivation/submitPin`.

## Compliance Relevance
- Directly handles cardholder authentication — PCI DSS Req 8 (identity management), Reg E (electronic fund transfers).
- Processes payment method selection and fund disbursement triggers — PCI DSS Req 6, NACHA (ACH), Reg E.
- BioCatch and reCAPTCHA integrate fraud controls — supports GLBA and AML/KYC risk posture.
- OTP/MFA is enforced for sensitive operations.
- AES encryption for mobile DDA data (`mobileApp.ddaEncrypt=Y`).
- IEFT (international transfers) subject to OFAC screening upstream.
- SSO profile URL integrates with `xSSO` service for external token decryption.

## Risks
- Western Union static shared key (`westernunion.statickey: cy*$s19kup`) hardcoded in `application.yaml` — credential exposure risk.
- Azure App Configuration connection string with secret embedded in `application.yaml` (line 12: `Secret=WKFBxxRd...`) — hardcoded secret in source.
- CBTS (Cross-Border Transfer Service) credentials (`UserName`, `Pass`) hardcoded in `application.yaml` (lines 168-169).
- Redis cache key in `application.yaml` (line 218: `cachekey: [REDACTED — rotate immediately]`) — Base64-encoded key in source.
- CSRF protection disabled globally (`csrf.ignoringRequestMatchers("/**")`).
