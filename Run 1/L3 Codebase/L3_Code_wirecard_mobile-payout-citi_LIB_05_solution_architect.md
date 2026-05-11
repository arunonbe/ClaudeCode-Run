# Solution Architect — wirecard_mobile-payout-citi_LIB

## Technical Architecture
- **Framework**: React Native (TypeScript) — cross-platform iOS/Android
- **State management**: Redux + redux-persist (offline state persistence)
- **Navigation**: React Navigation (Router component)
- **HTTP client**: OkHttp (Android, via React Native network module) with custom CertificatePinner; iOS equivalent via NSURLSession/AlamoFire (Fastlane-managed)
- **Security**: OkHttpCertPin (Android), SecureFlag module, jail-monkey jailbreak detection
- **i18n**: Custom i18n module with locale loading
- **Storage**: react-native-sensitive-info (Keychain/Keystore), AsyncStorage via redux-persist
- **Icons**: react-native-vector-icons
- **API**: SOAP-initiated client (`ApiClient.initSoapClient()`) — SOAP or SOAP-to-REST gateway backend

## API Surface
The app is a consumer of external APIs; it does not expose APIs. Key outbound:
- `MAIN_ENDPOINT=https://webservice-qa.wirecard.com:4007` (QA)
- Production: `https://webservice.wirecard.com` (from OkHttpCertPin)
- Content URLs (WebView): `login-qa.wirecard.com/xContent/...` for fees, terms, FAQ

## Security Posture

### Authentication / Authorisation
- PIN-based login (InputPIN component)
- Biometric touch ID (`react-native-touch-id`)
- Credentials stored in OS Keychain/Keystore via `react-native-sensitive-info`
- Session token/cookie managed via `ReactCookieJarContainer` in OkHttp

### Certificate Pinning
- Android: `OkHttpCertPin.java` — hardcodes two SHA-256 pin hashes:
  - PROD `sha256/Asq9EpD7IjnZ8UGt8AqmhYL+D8Dz9T81ieb8fdEaW3w=` — comment says "until 20 Dec 2021"
  - QA `sha256/RIZfuX+zJTiHz/395d1NNZh87hTkvHBLg3X/gwqTsxI=` — comment says "until 31 Jul 2021"
- **BOTH PINS EXPIRED** — certificate pinning control is non-functional for any new cert deployed after those dates

### Screen Security
- `SecureFlag` Android module: sets `FLAG_SECURE` on the Activity window — prevents screenshots and screen recording
- Jailbreak/root detection: `jail-monkey` library

### Known CVEs / Security Concerns
| Item | Risk |
|---|---|
| Expired cert pins | API traffic effectively unpinned after cert rotation — MitM risk |
| Chuck interceptor in non-release builds | Full HTTP traffic visible on device; if shipped in beta to external testers, exposes API request/response |
| Release keystore in source (`payoutnam_release.keystore`) | Anyone with repo access can sign APKs as the production app |
| TestFairy API key in build.gradle | Allows unauthorised distribution uploads |
| `connectTimeout(0)` in OkHttp | No connection timeout — DoS/hang vulnerability |
| redux-persist (AsyncStorage) | App state including account data potentially stored unencrypted on device |
| React Native version (estimated 0.59–0.61) | Multiple security CVEs in old RN versions; JSC engine, HTTP module vulnerabilities |

## Technical Debt
1. Estimated React Native 0.59–0.61 — at least 3 major versions behind current (0.73+)
2. Android `appcompat-v7:27.1.0` — AndroidX migration not completed (AndroidX requires `appcompat:1.x`)
3. `com.android.support:design:27.1.0` — deprecated; replaced by Material Components
4. Unit test stages commented out in Jenkinsfile — zero automated test coverage
5. SOAP API client (`ApiClient.initSoapClient()`) — legacy SOAP protocol in a mobile app
6. `connectTimeout(0)` — no timeout configured on OkHttp client
7. `.env.*` files in source root — environment config mixed with source
8. `react-native-blur-overlay`, `jail-monkey` — unmaintained/archived packages
9. Chuck interceptor `de77a28b0ed657e8bfa5af930baf801918c2e400` API key exposed in source

## Gen-3 Migration Requirements
1. Upgrade to React Native 0.73+ with Hermes engine
2. Migrate from SOAP backend to RESTful/GraphQL API
3. Implement runtime certificate pinning with rotatable pins (not hard-coded hashes)
4. Rotate and re-issue Android signing keystore; store in CI/CD secret manager (never in source)
5. Remove debug-only Chuck interceptor from all build types; replace with Sentry/Crashlytics
6. Implement encrypted redux-persist storage (e.g., redux-persist-encrypted)
7. Replace TestFairy with current distribution platform (TestFlight only, or MDM)
8. Migrate from Jenkins to cloud-native CI (GitHub Actions / Azure DevOps)
9. Enable automated unit and E2E tests (Jest + Detox)
10. Migrate from `com.android.support` to AndroidX / Material 3

## Code-Level Risks
| File | Location | Risk |
|---|---|---|
| `android/app/src/main/java/com/wirecard/payoutnam/ecount/OkHttpCertPin.java` | Lines 27-28 | Both cert pin hashes expired; pinning is non-functional |
| `android/app/src/main/java/com/wirecard/payoutnam/ecount/OkHttpCertPin.java` | Line 32 | `connectTimeout(0)` — no timeout |
| `android/app/src/main/java/com/wirecard/payoutnam/ecount/OkHttpCertPin.java` | Line 35 | `ChuckInterceptor` active in non-release builds — HTTP sniffing |
| `android/app/build.gradle` | Line 206 | TestFairy API key hardcoded |
| `android/app/keystore/payoutnam_release.keystore` | (binary) | Production signing key in source control |
| `android/app/build.gradle` | Lines 177-183 | `storeFile`, `storePassword`, `keyAlias`, `keyPassword` read from properties file but keystore itself in repo |
| `App.tsx` | Line 63 | `.catch(this.onApiReady)` — silently swallows SOAP init errors; app continues with potentially unauthenticated state |
