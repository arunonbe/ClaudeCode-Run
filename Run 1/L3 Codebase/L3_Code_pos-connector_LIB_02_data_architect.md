# pos-connector_LIB — Data Architect View

## 1. Data Model Overview

`pos-connector_LIB` does not define or own a persistent data model. It is a message-routing component whose data surface is entirely transient — ISO 8583 message objects in memory. The one database integration that exists (`DBConnectionTestDAO.java`, `StoredProcSampleDAO.java`) appears to be scaffolding / test code rather than production logic, relying on the JNDI data source `java:comp/env/jdbc/EcountCoreDataSource`.

## 2. Message Data Structures (ISO 8583)

All business data is carried in ISO 8583 message structures managed by the jPOS library (`org.jpos.iso`). Relevant fields in use:

| ISO Field | Purpose | Location in Code |
|---|---|---|
| MTI (Message Type Indicator) | Message type, e.g. `0800` (network management) | `MyChannel.java` lines 124, 137; `KeepAlivePos.java` line 32 |
| Field 7 | Transmission date/time (format `MMDDhhmmss`) | `MyChannel.java` line 126; `KeepAlivePos.java` line 34 |
| Field 11 | System trace audit number (STAN), hardcoded `000001` | `MyChannel.java` lines 127, 139; `KeepAlivePos.java` line 35 |
| Field 39 | Response code (expected `0` = approved) | `MyChannel.java` line 86 |
| Field 70 | Network management information code (`061`=sign-on, `062`=sign-off, `301`=echo/keepalive) | `MyChannel.java` lines 128, 140; `KeepAlivePos.java` line 36 |

### PCI DSS Data Classification Note
ISO 8583 financial messages can contain:
- **Field 2**: Primary Account Number (PAN) — classified as cardholder data (CHD), highest sensitivity
- **Field 35/36**: Track 2 / Track 3 data — classified as Sensitive Authentication Data (SAD)
- **Field 52**: PIN data block — classified as SAD

The current implementation in `POSMessageListener.process()` calls `m.dump(System.out,"message")` (line 35) and `reply.dump(System.out,"reply")` (line 42). **This can log full ISO 8583 message content, including PAN and track data, to standard output** — a critical PCI DSS violation (Requirement 3.3: SAD must not be stored post-authorization; Requirement 10.3: log protection).

## 3. Data Sources and Connections

| Data Source | Connection Type | Details |
|---|---|---|
| FDR POS Host | TCP/IP socket via jPOS `PostChannel` | IP/port from `application-config.properties` |
| EcountCore Database | JDBC via JNDI | `java:comp/env/jdbc/EcountCoreDataSource` (container-managed) |
| SQL Server (dev, commented out) | JDBC via jTDS | `vsqldev1`, database `jobsvc_test` — credentials in commented XML |

## 4. Data Flow Diagram (Narrative)

```
POS Terminal Network
      |
      | (TCP/IP, ISO 8583)
      v
 MyChannel (PostChannel extension)
      |
      |-- connect() --> sends MTI 0800 sign-on
      |-- receive() --> hands to ISOMUX
      v
 ISOMUX (multiplexer)
      |
      v
 POSMessageListener.process()
      |-- m.dump(System.out)      <-- PCI RISK: may log CHD/SAD
      |-- reply.setResponseMTI()
      |-- source.send(reply)
      v
 (response back to POS terminal)

 [Parallel thread]
 KeepAlivePos.run()
      |-- every 120s: sends MTI 0800 echo
      |-- on no response: reconnect
```

## 5. Data Retention and Privacy

- **In-flight messages only**: No persistent storage of transaction data is observed in the active (non-commented) code paths.
- **Log4j console output**: The `dump()` calls (`POSMessageListener.java` lines 35, 42; `MyChannel.java` line 83) write ISO 8583 message content to `System.out`. In a servlet container, this typically maps to server logs. If those logs are retained, they may contain PAN, track data, and PIN blocks, violating PCI DSS Requirements 3.2 and 3.3.
- **No encryption in transit configuration visible**: The `PostChannel` / `MyChannel` does not implement TLS wrapping. Connections to FDR host appear to be plain TCP, requiring compensating controls at the network layer (MPLS, dedicated line, IPSec) to satisfy PCI DSS Requirement 4.2.

## 6. Database Schema Artifacts

The `DBConnectionTestDAO.java` and `StoredProcSampleDAO.java` files exist but contain no business SQL or meaningful schema references. They appear to be developer scaffolding. The commented-out XML in `pos-connector-context.xml` references `jobsvc_test` on `vsqldev1`, suggesting this DAO was originally wired to a job service database.

## 7. Risks and Recommendations

| Risk | Severity | Recommendation |
|---|---|---|
| ISO 8583 `dump()` to stdout may expose CHD/SAD | Critical (PCI DSS) | Replace `dump()` calls with masked logging; never log raw ISO fields 2, 35, 36, 52 |
| STAN hardcoded to `000001` | High | STAN must be unique per transaction for proper interchange reconciliation |
| No TLS visible for FDR channel | High | Confirm compensating network-layer encryption; document in PCI DSS network diagram |
| Commented credentials in Spring XML | Medium | Remove all commented credential strings from version control |
