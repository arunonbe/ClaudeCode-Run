# ecap-backend-process_LIB — Solution Architect Report

## Critical Flags

### FLAG-1: Java 7 / EOL Runtime — CRITICAL (PCI DSS)
**File**: `pom.xml` lines 153–154
The library compiles and targets Java 1.7 (EOL July 2019). Running this on a Java 7 JRE means:
- TLS 1.2 is not enabled by default — violates PCI DSS Requirement 4.2.1 (strong cryptography for data in transit)
- No modern JVM security patches
- Potentially no SHA-256 certificate validation support by default

### FLAG-2: log4j 1.2.15 — CVE-2019-17571 (CVSS 9.8)
**File**: `pom.xml` line 45
`log4j:log4j:1.2.15` is affected by CVE-2019-17571 (Log4j 1.x SocketServer RCE). If SocketServer or SMTPAppender is configured, remote code execution is possible.

### FLAG-3: `e.printStackTrace()` — PII Leakage Risk
**File**: `EcapEmailNotificationImpl.java` line 86, multiple catch blocks
```java
log.info("Exception in sendEmailNotificationToRecipient()" + e.getMessage());
e.printStackTrace();
```
`e.printStackTrace()` writes to `System.err`, bypassing log4j. Member IDs, names, and email addresses may appear in uncontrolled system error output. This is a GDPR/CCPA data handling concern and a PCI DSS Requirement 10 (logging) violation.

### FLAG-4: No Idempotency for State Machine Failures
**File**: `EcapCardCreationProcessImpl.java` lines 33–75
If the JVM crashes mid-batch, some card requests may have been partially processed (member created but card not yet created, or card created but not loaded). The `process_counter` mechanism provides partial protection, but there is no distributed transaction rollback. This can result in:
- Duplicate members in eCount core
- Cards created but not loaded (unfunded card issued to recipient)
- Purchaser charged but recipient never notified

### FLAG-5: `SNAPSHOT` Version Never Released
**File**: `pom.xml` line 15: `<version>2.0.0-SNAPSHOT</version>`
The library is deployed as a SNAPSHOT artifact. SNAPSHOT versions are mutable — two builds of the same SNAPSHOT can produce different JARs. This violates PCI DSS Requirement 6.3 (software development lifecycle requires immutable release artifacts for production).

---

## All Classes and Methods — Inventory

### Package: `com.ecount.service.ecap`
| Class | Purpose |
|---|---|
| `CardCreationProcess` | Interface defining `run()` method |
| `EcapCardCreationProcessImpl` | Main batch orchestrator; `run()` iterates requests in batches |
| `EcapCardCreationClient` | Main class; Spring context initialization and `CardCreationProcess.run()` invocation |
| `EcapRequestConsumer` | Consumer thread dispatcher; `processRequest(CardRequest[])` |
| `EcapRequestProducer` | Fetches pending requests from DB; `getRequests()` → `List<CardRequest>` |
| `IRequestConsumer` | Interface for `processRequest(CardRequest[])` |
| `IRequestProducer` | Interface for `getRequests()` |

### Package: `com.ecount.service.ecap.state`
| Class | Purpose |
|---|---|
| `StateMachine` | Drives state transitions; `execute(CardRequest)` |
| `AbstractEcapProcessState` | Base class; `process(CardRequest)`, `getNextState()` |
| `CardRequest` | State carrier; wraps `Recipient` + processing metadata |
| `CreateMemberState` | Creates cardholder member in eCount; calls `EnrollmentManagerImpl` |
| `CreateGiftCardState` | Creates prepaid gift card device; calls `DeviceManagerImpl` |
| `CreateDDAState` | Creates DDA account; calls `DeviceManagerImpl` for DDA device |
| `DDAToDDAFundTransferState` | Executes DDA-to-DDA fund transfer; calls `TransferManagerImpl` |
| `PurchaserRecipientLinkState` | Links purchaser member to recipient; updates association |
| `EndState` | Terminal state; calls `EcapUpdateProcessCounterAndStatusCodeStoreProc` |

### Package: `com.ecount.service.ecap.concurrency`
| Class | Purpose |
|---|---|
| `CardRequestExecutor` | Spring `ThreadPoolTaskExecutor` wrapper; manages concurrent processing |
| `CardRequestHandler` | `Runnable` per card request; drives `StateMachine` for one request |

### Package: `com.ecount.service.ecap.notification`
| Class | Purpose |
|---|---|
| `IEcapEmailNotification` | Interface: `sendEmailNotificationToRecipient()`, `sendFailureConfirmationToPurchaser()` |
| `EcapEmailNotificationImpl` | Implements notification; calls `NotificationManagerImpl` from cbase layer |
| `EmailNotificationToRecipient` | Email object for success notification to recipient |
| `FailureNotificationToCardPurchaser` | Email object for failure notification to purchaser; includes address, amount, shipping |

### Package: `com.ecount.service.ecap.dao`
| Class | Purpose |
|---|---|
| `IEcapRecipientDao` | Interface for recipient data access |
| `EcapRecipientDaoImpl` | JDBC implementation of recipient queries and updates |
| `EcapUpdateProcessCounterAndStatusCodeStoreProc` | Calls stored proc to update counter + status atomically |
| `InsertCommentDAOImpl` | Inserts audit comments into DB |
| `GetCsaInquiryCategoryByInquiryType` | Reads CSA inquiry category config from DB |

### Package: `com.ecount.service.ecap.data`
| Class | Purpose |
|---|---|
| `Recipient` | Data bean: all recipient PII, card value, shipping info, program info |
| `GetCsaInquiryCategoryByInquiryTypeValue` | Value object for CSA inquiry category |

### Package: `com.ecount.service.ecap.comments`
| Class | Purpose |
|---|---|
| `Commentor` | Interface for comment writing |
| `JDBCCommentor` | JDBC-based comment writer; `addComment(memberId, comment, agentId)` |
| `AutoComment` | Business-level comment composer; determines what comment text to generate |
| `AutoCommentException` | Exception type for comment failures |

### Package: `com.ecount.service.ecap.util`
| Class | Purpose |
|---|---|
| `EcapProcessConstants` | Constants: language codes, event names, process states, delivery methods |
| `EcapUtil` | Utility methods: `getCustomerServiceNumber()` for notification |

### Package: `com.ecount.service.ecap.springframework`
| Class | Purpose |
|---|---|
| `ApplicationContextProvider` | Static Spring `ApplicationContext` holder |
| `AppSpringContext` | Spring context initialization helper |

---

## Security Vulnerability Summary

| Vulnerability | File | CVE / Rule | Severity |
|---|---|---|---|
| Java 7 / no TLS 1.2 enforcement | `pom.xml` lines 153–154 | PCI DSS 4.2.1 | Critical |
| log4j 1.2.15 SocketServer RCE | `pom.xml` line 45 | CVE-2019-17571 CVSS 9.8 | Critical |
| Spring 2.0.8 — multiple known CVEs | `pom.xml` line 35 | Various Spring CVEs | High |
| mssql-jdbc 6.4 — outdated TLS support | `pom.xml` line 146 | PCI DSS 4.2.1 | High |
| `e.printStackTrace()` — uncontrolled PII output | `EcapEmailNotificationImpl.java` line 86 | GDPR Art. 25, PCI DSS Req. 10 | High |
| SNAPSHOT artifact in production | `pom.xml` line 15 | PCI DSS 6.3 | Medium |
| No idempotency for partial failures | `EcapCardCreationProcessImpl.java` | PCI DSS 6.2 | High |
| No DLP on exception log messages (member IDs) | Multiple catch blocks | CCPA/GDPR | Medium |

---

## Remediation Priority Matrix

| Item | Priority | Effort |
|---|---|---|
| Upgrade to Java 11 LTS minimum | P1 — 30 days | High (requires Spring upgrade) |
| Replace log4j 1.x with Logback or Log4j2 | P1 — 7 days | Low |
| Replace `e.printStackTrace()` with `log.error(e)` everywhere | P1 — 1 day | Trivial |
| Upgrade Spring to 5.x | P1 — 60 days | High |
| Upgrade mssql-jdbc to 12.x | P1 — 7 days | Low |
| Implement idempotency / distributed transaction IDs | P2 — 60 days | High |
| Convert SNAPSHOT to release versioning | P2 — 14 days | Low |
| Add unit tests for state machine transitions | P2 — 30 days | Medium |
| Replace XML-RPC IPC with REST | P3 — 90 days | High |
