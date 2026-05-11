# Data Architect — wirecard_mobile-payout-citi_LIB

## Data Stores
| Store | Type | Notes |
|---|---|---|
| Remote Wirecard API (`webservice.wirecard.com`) | REST API (SOAP-initiated) | Account, transaction, and cardholder data; primary data source |
| Redux store (in-memory) | Client-side state | Managed via react-redux; ephemeral per session |
| redux-persist | Local device storage | Persisted subset of Redux state; likely AsyncStorage on device |
| react-native-sensitive-info | OS secure storage (Keychain/Keystore) | Credentials and sensitive tokens |

No local relational database observed. The app is a thin client — all canonical data lives in the Wirecard backend API.

## Schema / Data Model
No ORM or SQL schema defined. Data structures are TypeScript interfaces/types within Redux slices and API response models. Key inferred data shapes:

| Domain | Inferred Fields | Source |
|---|---|---|
| Authentication | username/PIN, session token | Login screen, sensitive-info storage |
| Account | balance, currency, account number, card reference | Dashboard/Overview screen |
| Transaction | transaction ID, amount, currency, date, type, description | TransactionList/TransactionDetails screens |
| Cardholder Profile | name, email, address | Settings/Profile screen |
| Language preference | locale code | Settings/Language, i18n module |
| App state | apiInitialized, popup state, keyboard state | HOC components |

## Sensitive Data on Device
| Data | Storage Mechanism | Risk Level |
|---|---|---|
| Authentication token/session | react-native-sensitive-info (Keychain/Keystore) | Medium — OS-protected |
| PIN / password | In-memory (Redux) during session; not persisted | Low during session |
| Account balance / transaction data | Redux store + redux-persist on device | Medium — encrypted at rest only if device is encrypted |
| Card registration data | Transmitted to API; not persisted locally observed | Low |
| Language preference | redux-persist | Low |

No PAN, CVV, or track-data fields observed being stored locally.

## Encryption
- **In transit**: TLS enforced via OkHttp CertificatePinner on Android (`OkHttpCertPin.java`); iOS assumed equivalent
- **At rest**: redux-persist relies on device storage encryption (AsyncStorage unencrypted by default on older React Native versions unless explicit encryption added)
- **Sensitive credentials**: react-native-sensitive-info uses Android Keystore / iOS Keychain — OS-level hardware-backed encryption where available
- No explicit encryption implementation observed for the Redux persistence layer — data at rest may be unencrypted on unencrypted devices

## Data Flow
```
Cardholder Device
  │
  ├── react-native-sensitive-info (OS Keychain/Keystore)  ← credentials/tokens
  │
  ├── redux-persist (AsyncStorage)  ← app state subset
  │
  └── OkHttp (TLS + CertPin) ──▶ webservice.wirecard.com:4007  ← all payment data
                                         │
                              Wirecard NAM backend API
                              (account, transaction, card data)
```

## Data Quality / Retention
- No local data retention policy; app is a view layer over the Wirecard API
- redux-persist data persists until app uninstall or explicit logout
- No observed data purge/wipe on logout — session tokens may remain in sensitive-info store
- App API client initialises via SOAP (`ApiClient.initSoapClient()`) — SOAP/REST hybrid API interface

## Compliance Gaps
1. redux-persist default (AsyncStorage) stores state in plaintext on device — contains account/transaction data; does not meet PCI DSS Requirement 3.4 encryption-at-rest if device not fully encrypted
2. Expired certificate pins (Dec 2021 / Jul 2021) — certificate pinning control is broken; all traffic effectively unpinned after rotation
3. No observed explicit wipe of sensitive data on logout — session/token data may persist
4. TestFairy API key hardcoded in `android/app/build.gradle:206` — token in source control
5. Release keystore `payoutnam_release.keystore` stored in `android/app/keystore/` — critical: private signing key in source control
6. `.env.*` files in source contain application IDs and QA endpoint URLs — should be excluded from source control for production values
7. Chuck HTTP interceptor in debug/alpha/beta builds — could expose full API request/response to device in non-production builds accessible to testers
