# Business Analyst View — xsso_SVC

## Business Purpose
xSSO SVC is the Gen-1 Single Sign-On (SSO) service for the eCount/Onbe prepaid card platform. It provides RSA-based token encryption/decryption services that allow partner applications and internal One Platform systems to authenticate cardholders without requiring them to log in again. It acts as the cryptographic gateway for cross-application SSO token exchange.

## Capabilities
- **SSO token decryption (`/tokenManagerServlet`):** Decrypts an RSA-encrypted, Base64-encoded SSO token submitted by a partner; extracts PUID and programId; resolves to a memberId
- **One Platform token encryption (`/encryptOPTokenManagerServlet`):** Encrypts cardholder identity data (userId, memberId, ecardId, programId) into an RSA-encrypted Base64 token for use by One Platform
- **One Platform token decryption (`/decryptOPTokenManagerServlet`):** Decrypts a One Platform token and returns the full XML login payload
- **External token decryption (`/decryptExternalTokenManagerServlet`):** Decrypts an externally-submitted token with affiliate-specific JKS keystore; validates timestamp format; returns decrypted XML
- **Health check endpoint (`/hc`):** Spring MVC health check via `HealthCheck` controller
- **Affiliate name resolution:** Resolves affiliate short name from affiliate ID for keystore selection
- **PUID→MemberId lookup:** `SSOTokenManagerImpl.searchPuid()` queries the JobSvc database to resolve a PUID to an internal memberId

## Key Entities
| Entity | Package | Description |
|---|---|---|
| TokenValue | `com.ecount.one.sso` | Deserialized SSO token payload (puid, programid, timestamp) |
| SSOTokenHandler | `com.ecount.one.sso` | RSA encrypt/decrypt using JKS keystore; per-affiliate keystore selection |
| SSOTokenManagerImpl | `com.ecount.one.sso` | Orchestrates encrypt/decrypt; affiliate name resolution; PUID search |
| DESedeFactory | `com.ecount.one.sso` | 3DES key generation utility (not used in primary SSO flow — see notes) |
| Base64Coder | `com.ecount.one.sso` | Custom Base64 encode/decode |
| EcountContext | `com.ecount.one.value` | Platform configuration context (JKS path, agent, URLs) |
| Affiliate | `com.cbase.business.affiliate` | Client/partner entity (from xplatform_LIB) |

## Business Rules
- Each affiliate has a dedicated JKS keystore file: `{jks.configfile.path}/{affiliateShortName}_keystore.jks`
- One Platform operations use a fixed affiliate name `"oneplatform"` (hardcoded in `EncryptOPTokenManagerServlet` and `DecryptOPTokenManagerServlet`)
- Affiliate short name is resolved from the affiliate ID embedded in the program ID (positions 4–7 of an 8-character program ID string)
- External token decryption validates a timestamp in the token payload using format `MMddyyyyHHmm` — no expiry window enforced (only format validation)
- SSO token XML payload format: `<login><userid/><memberid/><ecardid/><programid/></login>`
- PUID→MemberId resolution queries the JobSvc database via `GetPuid` stored procedure

## Process Flows
### Partner SSO Token Validation
1. Partner submits `Token` (Base64-encoded RSA-encrypted XML) and `ProgramId` via HTTP POST to `/tokenManagerServlet`
2. Service extracts affiliate ID from ProgramId (positions 4–7)
3. Resolves affiliate short name via `AffiliateFactory`
4. Loads JKS keystore for the affiliate
5. RSA-decrypts the token using the affiliate's private key
6. Deserialises XML to `TokenValue` (puid, programid)
7. Queries JobSvc DB for memberId using PUID + programId
8. Returns memberId in HTTP response body

### One Platform Token Encryption
1. Caller submits `userid`, `memberid`, `ecardid`, `programid` via HTTP POST to `/encryptOPTokenManagerServlet`
2. Service assembles XML login payload
3. RSA-encrypts using `oneplatform` keystore public key
4. Returns Base64-encoded encrypted token

## Compliance Relevance
- SSO token payload contains `memberid`, `ecardid`, `userid`, `programid` — sensitive account identifiers
- Affiliate-specific RSA keypairs stored in JKS files on the filesystem — key management is critical (PCI DSS Req 3.7)
- PUID resolution involves querying the JobSvc database — in scope for cardholder data environment (CDE)
- Timestamp-only validation (no expiry window) means a valid token is reusable indefinitely after issuance — replay attack risk
- `keystore.password = [REDACTED — rotate immediately]` and `certificate.password = [REDACTED — rotate immediately]` in the default properties file — weak/default credentials

## Risks
- Default keystore and certificate passwords (`ecount`/`ecount`) committed in properties file — critical credential exposure if not overridden in all environments
- No token expiry enforcement — valid SSO tokens can be replayed indefinitely
- Hardcoded IV in `DESedeFactory.generateInitializationVector()` (`"12345678"`) — a 3DES cipher with a fixed IV is cryptographically broken (if this factory is used in production)
- `SSOFilter.decrypt()` creates a new `SSOTokenHandler` without a keystore — decrypt will fail silently or throw; the filter catches the exception and returns an empty string
- Timestamps validated for format only, not for freshness — no replay protection
