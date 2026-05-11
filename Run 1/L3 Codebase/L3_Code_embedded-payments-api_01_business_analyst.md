# 01 Business Analyst — embedded-payments-api

## Overview

`embedded-payments-api` is a **Spring Boot 3.4.x Java 21 microservice** that powers Onbe's Embedded Payments product — a white-label payment disbursement capability that partner companies (clients) can embed in their own web applications. The project is a Maven multi-module parent with groupId `com.onbe`, artifactId `embedded-payments-api-parent`, version `0.0.1-SNAPSHOT` (`pom.xml` lines 7–9). It is the Gen-3 API layer in the Onbe platform.

## Business Purpose — Embedded Payment Disbursements

Onbe's Embedded Payments product allows a partner (e.g., a healthcare insurer, an auto-finance company, a gig-economy marketplace) to disburse funds to their end-users (cardholders/recipients) through a lightweight, iFrame-based payment widget embedded in the partner's own web portal. The partner never handles the payment infrastructure — Onbe manages all payment rails, card issuance, and compliance.

## Payment Capabilities Exposed

The API surface is fully defined by `embedded-payments-open-api/src/main/resources/openapi.yaml`. The following capabilities are exposed:

### Client-Facing APIs (`Embedded Client` tag)

| Endpoint | Operation | Business Purpose |
|---|---|---|
| `POST /embedded/client/authenticate` | `authenticate` | Partner server authenticates to Onbe using `clientId` + `clientSecret` + `programId` + `partnerUserId` (the end-user's ID in the partner system). Returns a short-lived one-time access token. |

### Shim APIs (`Embedded Shim` tag)
The shim is a JavaScript library (`embedded-payments-sdk`) that the partner embeds on their page to load the widget securely.

| Endpoint | Operation | Business Purpose |
|---|---|---|
| `POST /embedded/shim/load-spa` | `loadSpa` | Validates the OTT, checks domain allowlist, returns the SPA HTML. Sets two secure HttpOnly cookies (`OAuth-Token`, `X-Onbe-Session-Token`) used for subsequent widget API calls. |
| `GET /embedded/assets/{fileName}` | `getStaticAsset` | Serves the compiled widget JS/CSS bundles stored as static resources in the Spring Boot app |

### Widget APIs (`Embedded Widget` tag)
All widget APIs are session-authenticated (cookies) and operate on behalf of the cardholder identified by the session.

| Endpoint | Operation | Business Purpose |
|---|---|---|
| `POST /embedded/widget/list-disbursements` | `listDisbursements` | Returns all pending disbursements for the current cardholder session, with amounts, statuses, claim codes, and dates |
| `POST /embedded/widget/modalities` | `getModalities` | Returns payment modalities available for a specific claim code (VIRTUAL=100, CARD=200, ACH=300, CHECK=400, PAYPAL=500, EXPRESS_ACH=600) with fees and final amounts |
| `POST /embedded/widget/accept-terms` | `acceptTerms` | Records T&C acceptance (Generic Terms ID=4, Card Terms ID=5, ACH Terms ID=6) for the session |
| `POST /embedded/widget/disburse` | `executeDisbursement` | **Executes the fund transfer** — takes `claimCode` + `modalityId` and processes the actual payment via EcountCore |
| `POST /embedded/widget/disbursement-info` | `getDisbursementInfo` | Returns **decrypted card details** for display: `cardNumber`, `cvCode`, `expiryMonth`, `expiryYear` — **PCI scope** |
| `POST /embedded/widget/masked-disbursement-info` | `getMaskedDisbursementInfo` | Returns masked card details (`maskedCardNumber`) plus `balance` for already-disbursed cards |
| `POST /embedded/widget/transactions` | `getTransactions` | Returns account transaction history with balance summary |
| `POST /embedded/widget/contact-info` | `getInfo` | Returns cardholder's name, email, phone, and full mailing address |
| `POST /embedded/widget/enabled-wallets` | `getEnabledWallets` | Returns eligible on-device digital wallets (Apple Pay, Google Pay, etc.) for the cardholder's device |
| `POST /embedded/widget/provision-wallet` | `provisionWallet` | Triggers push provisioning of a card to the selected digital wallet via IDI SDK |
| `POST /embedded/widget/logout` | `logout` | Revokes the OAuth token and clears the session |

## Payment Modalities

The API supports 6 disbursement modalities (openapi.yaml lines 447–469):

| Modality ID | Name | Description |
|---|---|---|
| 100 | VIRTUAL | Digital disbursement to a virtual wallet |
| 200 | CARD | Physical card issuance |
| 300 | ACH | Direct bank transfer |
| 400 | CHECK | Paper check disbursement |
| 500 | PAYPAL | PayPal disbursement |
| 600 | EXPRESS_ACH | Express ACH (faster settlement) |

## Key Services (from CLAUDE.md)

| Service Class | Purpose |
|---|---|
| `WidgetService` | Core widget embedding and session logic |
| `ClaimablePaymentsService` | Manages claimable payment workflows |
| `ECountCoreService` | Integration adapter to EcountCore (SOAP/REST) |
| `DomainWhitelistService` | Validates that the embedding domain is on the client's allowlist |
| `ShimService` | Token validation and SPA loading logic |
| `ClientService` | Client/merchant registration and lookup |
| `CacheService` | Ehcache-based caching |
| `CleanupTask` | Scheduled cleanup of expired tokens/sessions |

## Downstream Integrations

| System | Integration Type | Purpose |
|---|---|---|
| EcountCore | REST (Apache CXF) + SOAP | Account lookup, transaction execution, card details |
| CMS | REST | Content management (localized strings, T&C documents) |
| SQL Server (5 datasources) | Spring Data JPA / Hibernate | Primary DB, jobservice, ecountcore read, cbase, cbaseapp |
| Azure App Configuration | Spring Cloud Azure | Runtime configuration |
| Azure AD | OAuth2 (`spring-security-oauth2-client`) | Service-to-service authentication |
| Azure Key Vault | Spring Cloud Azure | Secrets management |
| Wallets APIM (Azure API Management) | REST | Digital wallet provisioning (Apple/Google Pay) |
| XContent / CDN | REST | Widget asset delivery |

## Database Schema (Flyway Migrations)

The primary database schema is managed by Flyway:

| Migration | Tables Created |
|---|---|
| V001.001 | `dbo.themes`, `dbo.disbursement_log`, `dbo.clients` |
| V001.002 | `dbo.one_time_tokens` |
| V001.003 | `dbo.one_time_tokens` + DDA column |
| V001.004 | `partner_user_id` column on tokens |
| V001.005 | Hash column on tokens (OTT hashing) |
| V001.006 | `member_id` column |
| V001.007 | `dbo.revoked_sessions` |
| V001.008 | `expires_at` on revoked sessions |
