# Enterprise Architect — wirecard_mobile-payout-citi_LIB

## Platform Generation
**Gen-2 (Wirecard/Northlane) — Mobile Channel**. React Native (not Java/Spring Boot), but part of the same Wirecard NAM platform generation. Deployed via Jenkins + TestFairy/TestFlight/Nexus internal infrastructure; API backend at `webservice.wirecard.com` is the same Gen-2 Wirecard backend.

## Business Domain
**Consumer Payments / Cardholder Self-Service** — This is the cardholder-facing mobile interface for the NAM prepaid/payout programme issued under the Citi partnership (programme name "PayoutNAM"). It is the mobile equivalent of a cardholder portal.

## Role in the Wirecard Platform
- End-user channel: cardholders manage their prepaid/payout card via this app
- Consumes the Wirecard NAM backend API (`webservice.wirecard.com`) — likely the same backend served by eCount/CCP systems
- No direct integration with internal Gen-2 microservices (FTC, NAM-bank-agent, etc.) — those are back-office; this is the cardholder UI

## System Dependencies
### Outbound (from app)
| System | Protocol | Operations |
|---|---|---|
| Wirecard API (`webservice.wirecard.com`) | HTTPS (TLS + CertPin) | Login, balance, transactions, card management |

No direct database or messaging dependencies — pure API client.

## Integration Patterns
- **REST/SOAP client**: App initialises via `ApiClient.initSoapClient()` — suggests SOAP interface or SOAP-to-REST gateway on backend
- **Certificate pinning**: Hard-coded pin hashes for prod and QA hostnames
- **Secure local storage**: react-native-sensitive-info for credentials (Keychain/Keystore)
- **State management**: Redux + redux-persist (offline-first state)
- **Security controls**: Jailbreak detection (jail-monkey), SecureFlag (Android screen capture), OkHttp CertPin

## Strategic Status
- **Current**: Deployed mobile app for NAM cardholder programme with Citi partnership
- **Strategic concern**: Certificate pins expired in 2021 — suggests app may no longer be actively maintained or deployed
- **Strategic fit**: A Gen-3 replacement would use a modern React Native version (current is likely RN 0.59–0.61 era based on dependencies), updated API client, and cloud-native backend
- The app's backend (`webservice.wirecard.com`) is a Gen-2 Wirecard infrastructure endpoint — migrating the app requires simultaneous backend migration

## Migration Blockers
1. SOAP/SOAP-to-REST API dependency on `webservice.wirecard.com` — requires replacement with modern REST/GraphQL API
2. Certificate pins hard-coded to `wirecard.com` domain — domain migration requires app update and store submission
3. React Native version likely 0.59–0.61 (based on `appcompat-v7:27.1.0` and other indicators) — significant upgrade required to reach current RN (0.73+)
4. TestFairy distribution dependency — requires migration to modern MDM/distribution platform
5. Internal Nexus and Jenkins dependency — requires migration to cloud CI/CD
6. Android Keystore in source — requires key rotation and migration to secure CI/CD secret management before any future builds
7. `jail-monkey` and `react-native-sensitive-info` packages need version evaluation for current React Native compatibility
