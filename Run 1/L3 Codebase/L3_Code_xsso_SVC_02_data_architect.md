# Data Architect View — xsso_SVC

## Data Stores
| Store | Type | Access | Notes |
|---|---|---|---|
| JobSvcDataSource (SQL Server) | Relational | Spring JNDI (`java:comp/env/jdbc/JobSvcDataSource`) | PUID→MemberId lookup via `GetPuid` stored procedure |
| JKS Keystore files (per-affiliate) | Filesystem (JKS) | `FileInputStream` by path | RSA private/public key pairs for each affiliate |
| eCount config file | Filesystem (XML) | EcountContext map | Platform configuration; path set by `CBASE_HOME_URL` environment variable |

## Schema / Key Data Structures

### PUID Lookup (`GetPuid` stored procedure)
- Input: programId, puid
- Output: `GetPuidValue` containing `memberId`

### SSO Token (in-memory XML structure)
```xml
<login>
  <userid>{userId}</userid>
  <memberid>{memberId}</memberid>
  <ecardid>{ecardId}</ecardid>
  <programid>{programId}</programid>
</login>
```
- Encrypted with RSA/ECB/PKCS1PADDING using affiliate's public key
- Base64-encoded for transport

### Affiliate Resolution
- Affiliate ID extracted from ProgramId (substring positions 4–7)
- Affiliate short name fetched from `AffiliateFactory` (cached; backed by eCount Core DB via xplatform_LIB)

### JKS Keystores
- One `.jks` file per affiliate: `{jksConfigFilePath}/{affiliateShortName}_keystore.jks`
- Contains: RSA 2048-bit key pair (public certificate + private key)
- Loaded via `KeyStore.getInstance("JKS")` with `keyStorePassword` and `certificatePassword` from properties

## Sensitive Data
| Data Element | Classification | Location |
|---|---|---|
| RSA private keys (per affiliate) | Cryptographic material | JKS files on filesystem at `${jks.configfile.path}` |
| Keystore password | Credential | `applicationContext-xSSO.properties` — default value `ecount` |
| Certificate password | Credential | `applicationContext-xSSO.properties` — default value `ecount` |
| memberId | Sensitive account identifier | Returned in HTTP response body as plaintext |
| userId, ecardId, programId | Sensitive identifiers | SSO token XML payload |
| PUID | Account identifier | SSO token XML payload; query parameter |
| MAC address | System identifier | `mac.address=00:50:DA:20:19:8F` in default properties — hardcoded |

## Encryption
- **Algorithm:** RSA/ECB/PKCS1PADDING — 2048-bit RSA key pair per affiliate
- **Keystore format:** JKS (Java KeyStore) — legacy format; PKCS12 is the recommended modern format
- **Key storage:** JKS files on the filesystem at a path configured by `${jks.configfile.path}`; not in an HSM
- **3DES infrastructure (DESedeFactory):** 3DES key generation and **hardcoded IV** `"12345678"` present in `DESedeFactory.java:38-40`; this class does not appear to be called in the primary SSO flow, but its presence indicates a legacy 3DES path
- **Base64:** Custom `Base64Coder` implementation rather than `java.util.Base64` (Java 8+) or Apache Commons Codec

## Data Flow
```
Partner HTTP POST → /tokenManagerServlet
        |
        | requestToken (Base64-encoded RSA-encrypted XML)
        | programId (8-char string)
        v
SSOTokenManagerImpl.decrypt(token, affiliateName)
        |
        | loads {affiliateName}_keystore.jks
        v
SSOTokenHandler.decrypt(encryptedBytes)  [RSA/ECB/PKCS1PADDING, private key]
        |
        v
XStream.fromXML(decryptedXml) → TokenValue {puid, programid}
        |
        v
GetPuid stored procedure (JobSvcDataSource)
        |
        v
memberId → HTTP response body (plaintext)

One Platform path → /encryptOPTokenManagerServlet
        |
        | userid, memberid, ecardid, programid (POST params)
        v
SSOTokenManagerImpl.encrypt(..., "oneplatform")
        |
        | loads oneplatform_keystore.jks
        v
SSOTokenHandler.encrypt(jksFilePath, xmlBytes)  [RSA, public key]
        |
        v
Base64Coder.encode(encryptedBytes) → HTTP response body
```

## Data Quality and Retention
- No data validation on token contents beyond XML well-formedness (XStream deserialisation)
- Timestamp validated for format (`MMddyyyyHHmm`) only — no freshness check
- No audit log of token operations
- No token revocation mechanism

## Compliance Gaps
- **Default credentials in properties file:** `keystore.password=[REDACTED — rotate immediately]`, `certificate.password=[REDACTED — rotate immediately]` — PCI DSS Req 8.3.6 (change all vendor-supplied default credentials)
- **JKS files on filesystem (not HSM):** Private keys stored in files — not HSM-grade key protection; PCI DSS Req 3.7 requires key management procedures
- **No token expiry enforcement:** A stolen valid token can be replayed indefinitely — violates principle of time-limited tokens
- **`memberId` returned in plaintext HTTP response body:** Without TLS, memberId is exposed in transit
- **Hardcoded MAC address in properties:** `mac.address=00:50:DA:20:19:8F` — environment-specific value hardcoded in repo properties file
- **JKS keystore format:** JKS is deprecated in favour of PKCS12 since Java 9; migration to PKCS12 is recommended
- **No audit log** of SSO operations — PCI DSS Req 10.2 requires logging of authentication events
