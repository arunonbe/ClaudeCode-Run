# 01 Business Analyst — ecount-core_SVC

## Overview

`ecount-core_SVC` is the **EcountCore microservice** — Onbe's central payment processing platform deployed as a WAR (Web Application Archive) on Apache Tomcat 10. It is a multi-module Maven project with groupId `com.ecount.service.core.ecountcore`, artifactId `ecountcore`, version `3.1.9-SNAPSHOT` (`pom.xml` lines 12–14). The service underpins a broad range of payment capabilities across the Onbe prepaid card platform, serving both internal services and external partners.

## Business Purpose

EcountCore is the **transaction engine and account management platform** for Onbe's prepaid card products. It exposes both legacy XML-RPC interfaces (through `eCoreWar`) and modern REST endpoints (through `ecountCoreRestController` / `ecount-core-rest-api`) to support:

1. **Member (cardholder) management**: Creating, updating, and querying cardholder accounts
2. **Card management**: Device (card) issuance, status changes, and lifecycle management
3. **Transaction processing**: Electronic funds transfers, balance queries, transaction history
4. **FDR debit processing**: Integration with First Data Resources (FDR) for card-present and card-not-present transactions
5. **Job/order management**: Scheduled batch jobs and card order workflows
6. **KYC (Know Your Customer)**: Actimize KYC integration for identity verification
7. **Recipient screening**: Sanctions/AML screening for payment recipients
8. **StrongBox integration**: Secure key management for cryptographic operations
9. **ACH and IEFT processing**: Bank transfer workflows
10. **Country/regulation management**: Regulatory rule enforcement per jurisdiction
11. **Audit logging**: Web request logging and event auditing
12. **Caching**: Ehcache-based performance caching for frequently accessed data

## Module Structure

| Module | Artefact ID | Purpose |
|---|---|---|
| `common` | `common` | Shared constants, utility classes, base exceptions |
| `ecountCoreDAO` | `ecount-core-dao` | Data access layer — stored-procedure wrappers for all DB operations |
| `MQLibrary` | `mq-library` | IBM MQ messaging integration |
| `ecountCoreLibrary` | `ecount-core-library` | Core business logic library |
| `ecountCoreService` | `ecount-core-service` | Service layer — business workflow orchestration |
| `eCoreWar` | `ecore-war` | Web application module — Tomcat WAR; wires all modules; exposes XML-RPC and REST endpoints |
| `ProcessorServices` | (sub-modules) | FDR debit service integration |
| `ecountCoreRestController` | `ecount-core-rest-controller` | Spring MVC REST controllers |
| `ecount-core-rest-api` | `ecount-core-rest-api` | REST API model/interface definitions |
| `ecountCoreDocumentation` | `ecount-core-documentation` | API documentation |
| `jacoco-aggregate-coverage` | — | JaCoCo code coverage aggregation |

## Deployed Service Interfaces

### XML-RPC Services (Legacy — Gen-1/2)
Exposed via Spring XML-RPC servlet. Service beans defined in individual XML files:

| XML File | Service | Purpose |
|---|---|---|
| `EMemberXMLRPC.xml` / `EMemberService.xml` | EMemberService | Cardholder account operations |
| `EManageXMLRPC.xml` / `EManageService.xml` | EManageService | Card/account management |
| `EDeviceXMLRPC.xml` / `EDeviceService.xml` | EDeviceService | Card device operations |
| `ETransferXMLRPC.xml` / `ETransferService.xml` | ETransferService | Fund transfer operations |
| `EventXMLRPC.xml` / `EventService.xml` | EventService | Audit event logging |
| `EWebRequestLogService.xml` | EWebRequestLogService | Web request audit logging |
| `ACHDeviceLibrary.xml` | ACH | ACH bank transfer device library |
| `IEFTDeviceLibrary.xml` | IEFT | Interbank EFT device library |
| `FDRDebitServices.xml` | FDR Debit | First Data Resources debit processing |
| `KYCService.xml` | KYC | Actimize Know-Your-Customer service |
| `RecipientScreeningService.xml` | Recipient Screening | AML/sanctions screening |
| `StrongBoxService.xml` | StrongBox | Cryptographic key management |
| `CountryRegulationLibrary.xml` | Country Regulation | Jurisdiction-specific rules |
| `AuditActivityLibrary.xml` | Audit | Audit trail |
| `GlobalRequestID.xml` | Request ID | Distributed request correlation |
| `HealthMonitor.xml` | Health | Service health monitoring |

### REST Endpoints (Modern — Gen-2/3)
Exposed via Spring MVC (`ecountCoreRestController`). Used by `embedded-payments-api` and other downstream services.

## Key Downstream Consumers

- `embedded-payments-api` — calls EcountCore REST API for disbursement execution and card detail retrieval
- `emboss-extract_LIB` — queries EcountCore database directly via stored procedures for embossing data
- Various batch services, client-zone applications, and internal workflows

## PCI DSS Scope

EcountCore processes and stores cardholder data (PAN, expiry, cardholder names) and cryptographic key references (StrongBox). It is firmly within the CDE as both an account-management system and a transaction processor.
