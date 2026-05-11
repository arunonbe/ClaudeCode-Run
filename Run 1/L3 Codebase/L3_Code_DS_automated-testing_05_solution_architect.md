# Solution Architect View — DS_automated-testing

## Architecture Summary
Java 8 Maven project using TestNG + Selenium for UI and REST-Assured for API testing. Organized into a layered structure: page-object UI layer, API-client layer, database-connection layer, and common utilities. The test executor is Maven Surefire driven by XML suite files. No CI server integration exists; Windows batch scripts provide manual execution wrappers.

## Component Map
```
src/main/java/com/qa/
  ├── api/DMT/          — DMT REST API clients (API base, ConfigAPI, SystemAPI, UserAPI)
  ├── api/Ecount/       — Legacy Ecount account management (SOAP)
  ├── apps/page/        — Page Object Model for ClientZone and OnePlatform UI
  ├── common/           — Assert, FileOperations, General, Log, MultiOutputStream,
  │                       TestCaseWriter, WS/SOAP
  ├── common/credentials/ — Credentials, Crypt, Encrypt, Decrypt (AES)
  ├── database/mongodb/ — MongodbConnection
  └── database/SQL/     — SQLDBConnection, SQLUtilities

src/test/java/com/qa/test/
  ├── DMT/api/          — ConfigAPITest, SystemAPITest, UserAPITest
  ├── DMT/db/           — MongoDBTest
  ├── DMT/ui/           — DMTLoginTest
  ├── OnePlatform/      — OnePlatformLoginTest, OPPaymentLoginTest
  └── samples/          — LegacyDBTest, AddAndLoadAccounts, TestScriptTest
```

## API Integration Surface
| API | Base URL | Auth | Note |
|-----|---------|------|------|
| DMT REST | `http://localhost:5000/` | Cookie + CSRF token | Login → POST `/login`; subsequent calls use session cookies |
| Ecount SOAP | `https://webservice-qa.wirecard.com:4005/...` | Embedded in SOAP body | Legacy; domain may be inactive |
| MongoDB | `mongodb://localhost:27020` | Username/password (hardcoded) | dmt-web database |
| SQL Server | JDBC string in source | Username/password (hardcoded) | sandbox database |

## Security Assessment
| Finding | Severity | Detail |
|---------|---------|--------|
| Plaintext password `At1234567890` in `Prerequisites.java` | Critical | Hardcoded automation user password |
| MongoDB password `secret` hardcoded | Critical | `Prerequisites.java` |
| SQL Server credentials hardcoded | High | `LegacyDBTest.java` (commented-out but still in source) |
| AES encryption key `123456789012345678901234` used in `Credentials.main()` | High | Test/demo key — symmetric key material in source |
| Selenium 3.141.59 | Medium | Older release; browser compatibility risk |
| No HTTPS enforcement for DMT API | Medium | `http://localhost:5000` — plaintext in transit |

## Technical Debt
1. **Hardcoded credentials** throughout source — immediate remediation required; should use environment variables or a secrets manager.
2. **Mixed MongoDB driver versions** — `mongo-java-driver 3.12.8` and `mongodb-driver-core 4.2.2` in the same classpath can cause `ClassCastException`s.
3. **No test isolation** — tests share and modify shared state in MongoDB and SQL Server.
4. **Wirecard-branded URLs** — all legacy endpoint URLs reference `wirecard.com`/`wirecard.lan`; post-rebrand migration has not been completed in this repo.
5. **Static state** — `API.C` (cookies) and `API.XCSRFtoken` are static fields, causing cross-test contamination in parallel runs.

## Gen-3 Migration Recommendations
1. Move all credentials to a secrets manager (HashiCorp Vault, AWS Secrets Manager) and inject via environment variables at runtime.
2. Upgrade Selenium to 4.x and adopt WebDriver BiDi for more reliable UI automation.
3. Replace hardcoded MongoDB/SQL connection strings with test-container-based ephemeral databases for isolation.
4. Add the test suite to a proper CI pipeline (GitHub Actions) with environment matrix for DEV/QA/UAT.
5. Replace Wirecard-branded endpoint references with current Onbe-branded equivalents.
