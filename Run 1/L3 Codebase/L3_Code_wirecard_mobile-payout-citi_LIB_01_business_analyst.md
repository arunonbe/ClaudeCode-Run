# Business Analyst — wirecard_mobile-payout-citi_LIB

## Business Purpose
A React Native mobile application (iOS and Android) branded as "PayoutNAM" that allows cardholders to access and manage their Wirecard prepaid/payout card issued under the Citi/NAM programme. The app is the cardholder-facing channel for the Northlane/Wirecard NAM prepaid disbursement product.

## Capabilities
- Cardholder authentication (PIN-based login, biometric touch ID)
- Card activation and registration flows
- Dashboard with account overview and balance display
- Transaction history with transaction detail view
- Settings: profile, password change, language selection, ATM locator, contact us, FAQ, fees, terms, privacy policy
- Push notifications (implied by status checker HOC)
- Multi-language / i18n support
- Certificate pinning for API communications (OkHttp CertificatePinner on Android)
- Secure flag for Android screenshots/screen-capture prevention (SecureFlag module)
- Jailbreak / root detection (jail-monkey library)
- Redux-based state management with redux-persist for offline state

## Key Entities / Screens
| Screen | Purpose |
|---|---|
| Login | PIN authentication |
| Activation | Card activation flow |
| RegistrationFlow/Registration | New user registration |
| RegistrationFlow/RegistrationCard | Card registration |
| Dashboard/Overview | Account balance and overview |
| Transactions/TransactionList | List of transactions |
| Transactions/TransactionDetails | Individual transaction detail |
| Settings/Profile | Cardholder profile |
| Settings/ChangePassword | Change PIN/password |
| Settings/AtmLocator | ATM map finder |
| Settings/ContactUs | Support contact |
| Settings/Fees | Fee schedule (WebView) |
| Settings/Terms | Terms and conditions (WebView) |
| Settings/PrivacyPolicy | Privacy policy (WebView) |
| Settings/Faq | FAQ (WebView) |
| Settings/Language | Language picker |
| Settings/AboutLibraries | Open-source licenses |

## Business Rules
1. App must not be usable on jailbroken/rooted devices (jail-monkey enforcement)
2. Screenshots must be blocked on Android (SecureFlag module)
3. All API communication must be over TLS with certificate pinning to `webservice.wirecard.com` (prod) and `webservice-qa.wirecard.com` (QA)
4. App state is persisted locally via redux-persist (implies offline-capable design)
5. Application IDs are environment-scoped: `com.wirecard.payoutnam.ecount` (prod), `.dev` / `.alpha` / `.beta` suffixes for test builds
6. Release builds require production signing keystore (credentials.properties separate from source)
7. Sensitive data storage uses `react-native-sensitive-info` (OS-level secure storage)

## Compliance Relevance
- Certificate pinning directly addresses PCI DSS Requirement 6.5 (secure communications) and OWASP Mobile Top 10
- SecureFlag addresses PCI DSS screen-capture risk on Android
- Jailbreak detection reduces risk of runtime compromise in CDE-adjacent flows
- Privacy policy and terms screens suggest CCPA/GDPR/Reg E consumer disclosures present
- `react-native-sensitive-info` for credential storage addresses PCI DSS Requirement 8 (access controls)
- Pinned certificate expiry dates: PROD cert expired Dec 2021, QA cert expired Jul 2021 — **critical operational risk**

## Risks
1. **Expired certificate pins**: Both pinned certificate hashes have expiry dates in 2021; if not updated, all app communications will fail after cert rotation
2. **Chuck interceptor in non-release builds**: `ChuckInterceptor` (HTTP traffic inspector) included in alpha/beta/dev builds — if accidentally included in release builds, intercepts all API traffic
3. No observed automated unit test execution in Jenkinsfile (test stages are commented out)
4. TestFairy API key hardcoded in `build.gradle` (`de77a28b0ed657e8bfa5af930baf801918c2e400`) — token exposure risk
5. `.env.*` files in source root contain QA endpoint URLs and application IDs — should be gitignored for sensitive envs
6. Keystore file `payoutnam_release.keystore` is stored in the repository under `android/app/keystore/` — release keystore in source control is a critical security risk
