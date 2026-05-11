# CZ-OTP — Data Architect View

## Repository Status
The `CZ-OTP` repository is empty — no source files, configuration files, or schema definitions are present in the working tree at `E:\OnbeEast363\repos\CZ-OTP`.

## Data Store Assessment
Cannot be performed — no code or configuration to analyse.

## Anticipated Data Elements (inferred from name)
For a ClientZone OTP service, typical data elements would include:

| Element | Sensitivity | PCI/Privacy Concern |
|---|---|---|
| OTP seed / secret | HIGH | Key material — must be under HSM or key vault |
| OTP code (time-limited) | MEDIUM | Short-lived; must not be stored post-validation |
| Delivery target (phone/email) | HIGH | Cardholder PII — CCPA, GLBA, GDPR |
| OTP attempt log | MEDIUM | Audit trail for failed attempts (brute-force detection) |
| Session/correlation ID | LOW | Links OTP to originating session |

## Encryption Requirements (anticipated)
- OTP seeds must be encrypted at rest under a managed key (Azure Key Vault or equivalent).
- OTP delivery over SMS requires TLS to SMS gateway provider; email delivery requires TLS to SMTP relay.
- No cleartext storage of OTP values post-issuance.

## Compliance Gaps
- Cannot assess actual compliance gaps — repository is empty.
- Recommend ensuring that any OTP implementation includes:
  - Time-based expiry (TOTP per RFC 6238 or server-enforced short TTL).
  - Rate limiting and lockout on failed attempts (PCI DSS Req 8.3).
  - Audit logging of all OTP generation and validation events.

## Action Required
Populate the repository with source code and re-run analysis, or confirm that the CZ-OTP service resides under a different repository name.
