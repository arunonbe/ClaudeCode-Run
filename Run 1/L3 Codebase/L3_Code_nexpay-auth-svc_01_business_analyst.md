# Business Analyst Report — nexpay-auth-svc

## 1. Service Identity and Business Purpose

`nexpay-auth-svc` is the **authentication and identity management service** for the NexPay Gen-3 platform. Its primary business purpose is to provide a secure, managed user identity layer for NexPay consumers (cardholders) by delegating identity storage and authentication to **Microsoft Entra External ID** (formerly Azure AD B2C / CIAM). This service acts as an integration facade between the NexPay platform and the Microsoft Entra identity system, abstracting away the Graph API complexity from other NexPay services.

The service description (`pom.xml` line 18): *"Authentication service that communicates with Entra External ID"*.

## 2. Business Capabilities

Based on the implemented `UsersApiDelegateImpl.java`, the service exposes three primary operations:

| Endpoint | Method | Business Function |
|---|---|---|
| `POST /users/check-username` | `checkUsername` | Check if an email address is available for registration (pre-registration validation) |
| `POST /users` | `createUser` | Create a new cardholder identity in Entra External ID |
| `GET /users/{externalId}` | `getUserByExternalId` | Retrieve cardholder identity details by Entra object ID |

These three operations support the **cardholder onboarding and identity management lifecycle**:
- During registration, MPV calls `checkUsername` to provide real-time feedback to the cardholder before form submission.
- Upon successful registration, MPV calls `createUser` to provision the identity.
- Internal services can call `getUserByExternalId` to retrieve cardholder identity details for downstream operations.

## 3. Entra External ID (CIAM) Integration Model

The service uses a **service-to-service integration** pattern with Microsoft Entra External ID via the Microsoft Graph API:
- Authentication to Graph API: OAuth 2.0 client-credentials grant (`EntraGraphTokenProvider.java` line 71: `grant_type: client_credentials`)
- The service acts as a trusted internal service with `User.ReadWrite.All` scope implied by the Graph operations it performs
- User identities are created with `signInType: "emailAddress"` (line 143 in `EntraGraphClient.java`), meaning cardholders sign in with their email address

This architecture means:
- **Onbe does not store passwords**: all credential storage is managed by Microsoft Entra
- **Self-service password reset**: Entra External ID provides built-in SSPR (Self-Service Password Reset) capability
- **MFA**: Entra External ID can enforce MFA policies centrally without changes to this service

## 4. Idempotency Behaviour

`UsersApiDelegateImpl.createUser` (lines 87-90) implements an idempotency check: if a user with the same email already exists, it returns the existing user rather than raising an error. This is important for:
- Retry safety: if the MPV front-end or BFF retries a failed registration request, it will not create duplicate users
- Integration resilience: upstream services can call `createUser` without tracking whether they already called it

## 5. Username Availability Business Rules

`checkUsername` in `UsersApiDelegateImpl.java` (lines 52-58) enforces:
1. **Null/blank check**: Returns `INVALID_FORMAT` reason
2. **Must contain `@`**: Enforces email format
3. **Minimum length 3**: Basic length guard
4. **Normalized**: Email is lowercased and trimmed before lookup (line 60)

These rules are minimal. The service relies on downstream Entra validation for full email format verification. Business analysts should note that this lightweight pre-validation reduces unnecessary Graph API calls for obviously invalid inputs.

## 6. Regulatory and Compliance Business Context

- **GLBA / Reg E**: Consumer identity is foundational to all financial transactions. This service is the identity anchor for all NexPay cardholder operations.
- **GDPR / CCPA**: User creation stores PII (email, display name) in Microsoft Entra. Subject access requests and erasure requests must include the Entra identity store. Entra External ID provides data residency controls at the tenant level.
- **OFAC screening**: This service does not perform OFAC/sanctions screening. That responsibility lies upstream in the order/claim orchestration flow.
- **PCI DSS Req 8**: This service implements the identity management controls required by PCI DSS Requirement 8 (identification and authentication). Entra External ID's built-in MFA, password policies, and audit logging support compliance with Req 8.
