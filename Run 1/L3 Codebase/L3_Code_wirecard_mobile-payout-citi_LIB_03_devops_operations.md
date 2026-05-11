# DevOps / Operations — wirecard_mobile-payout-citi_LIB

## Build System
- **Mobile framework**: React Native (TypeScript)
- **iOS**: Fastlane lanes (`buildAlpha`, `buildBeta`, `buildRelease`, `testfairyAlphaUpload`, `testflightUpload`)
- **Android**: Gradle (`assembleAlpha`, `assembleBeta`, `assembleRelease`); proguard enabled for beta/release
- **Node/Yarn**: `yarn install --ignore-engines`, `yarn run loadLang`, `yarn run updateNpmDependencies`, `yarn run releaseTransform` / `yarn run developTransform`
- **Android build variants**: dev, alpha (debuggable), beta (minified/debug-signed), release (minified/release-signed)
- **iOS build variants**: Alpha → TestFairy; Release → TestFlight

## CI/CD Pipeline (Jenkins — Jenkinsfile)
| Stage | Platform | Description |
|---|---|---|
| Initialize | Both | Unlock keychain (`~/unlock_kchain`) |
| Checkout | Both | Git shallow clone; parse version from `package.json` |
| Setup | Both | yarn install; apply releaseTransform or developTransform; copy `local.properties` (Android) |
| Unit Test | Both | **Commented out** — no automated tests run in CI |
| Build | iOS | `fastlane build{Flavor}` |
| Build | Android | `./gradlew assemble{Flavor}` (+ stash/unstash signing keys from Jenkins master for Release) |
| Upload | Both | Parallel: Nexus artifact upload + TestFairy upload; master branch also uploads to TestFlight |
| Post | Both | `deleteDir()` workspace cleanup |

Branch naming drives build flavor:
- `feature/*`, `bugfix/*`, `chore/*`, `experiment/*` → Alpha (manual trigger only)
- `develop` → Alpha (automatic)
- `release/*`, `hotfix/*` → Beta
- `master` / `masterTest` → Release

## Artifact Management
- **iOS**: ZIP of `ios/output` uploaded to Nexus (`d-issrepo-app01.wirecard.sys:8081`) under `issuing-mobile-artifacts-snapshot/payout-nam-mobile/ios/`
- **Android**: ZIP of `android/app/build/outputs/apk` uploaded to same Nexus
- **Distribution**: TestFairy for alpha/beta; Apple TestFlight for production iOS
- **Android TestFairy**: `testfairy{Flavor}Upload` Gradle task

## Configuration Management
- Environment config via `.env.{dev|alpha|beta|prod}` files loaded via `react-native-config`
- Android signing: `android/app/keystore/credentials.properties` (excluded from source on a real project — but `payoutnam_release.keystore` IS in source)
- iOS signing: Fastlane manages provisioning profiles; signing keys stashed from Jenkins master under `signKeys/mobile-payout-citi`
- Environment-specific API endpoints defined in `.env.*` files

## Observability
- **Error handling**: `ErrorHandler` HOC wraps entire app — catches React errors
- **HTTP inspection**: Chuck interceptor (all non-release builds) — real-time HTTP logging on device
- **Crash / analytics**: Not explicitly observed; TestFairy may provide crash reporting
- **No application-level logging framework** observed (no Logback/Log4j equivalent for React Native)
- **Status checking**: `StatusChecker` HOC — purpose not fully readable without deeper component inspection but likely checks API/server connectivity

## Infrastructure Dependencies
| Dependency | Platform | Notes |
|---|---|---|
| `webservice.wirecard.com:4007` | Both | Production API endpoint |
| `webservice-qa.wirecard.com:4007` | Both | QA/dev API endpoint |
| Nexus `d-issrepo-app01.wirecard.sys` | CI/CD | Internal artifact store |
| TestFairy `wirecard-public.testfairy.com` | CI/CD | Beta distribution |
| Apple TestFlight | CI/CD | iOS production distribution |
| Jenkins (master node) | CI/CD | Signing key storage and job orchestration |

## Operational Risks
1. **No automated tests in CI** — unit test stages are commented out; no regression safety net
2. **Expired certificate pins** — both prod and QA pins expired in 2021; app communications may fail or fall back to unverified TLS
3. **Release keystore in source** — `payoutnam_release.keystore` in `android/app/keystore/`; requires immediate rotation if repository is/was accessible externally
4. **TestFairy API key in source** — `android/app/build.gradle:206`; key may allow unauthorised app uploads
5. Nexus dependency on internal hostname — builds fail outside Wirecard network
6. Jenkins `~/unlock_kchain` shell script dependency — brittle; not version-controlled
7. `credentials.properties` reference implies an external file dependency that is not validated in CI — silent signing failures possible
8. No observed iOS code-signing revocation/rotation process
