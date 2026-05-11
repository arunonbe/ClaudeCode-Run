# pos-connector_LIB — Solution Architect View

## 1. Solution Overview

`pos-connector_LIB` is a single-purpose Java EE web application that implements an ISO 8583 channel management solution for Onbe's card-present transaction path. The solution uses the open-source jPOS library to manage the TCP/IP socket lifecycle, multiplex multiple concurrent request/response message pairs, and handle network management (sign-on/sign-off/echo) with the FDR POS processing host.

## 2. Key Components and Their Responsibilities

| Class | Package | Role |
|---|---|---|
| `StartupServlet` | `com.ecount.web` | Servlet lifecycle: reads config, builds `ISOMUX`, starts keepalive thread |
| `MyChannel` | `com.ecount.web` | Extends jPOS `PostChannel`; adds login/logout ISO 8583 flows on TCP connect/disconnect |
| `POSMessageListener` | `com.ecount.web` | `ISORequestListener` implementation; receives messages, sends ACKs |
| `KeepAlivePos` | `com.ecount.web` | `Runnable`; sends periodic heartbeats; triggers reconnect on failure |
| `PosShutdownListener` | `com.ecount.web` | `ServletContextListener`; graceful shutdown / logoff |
| `ServiceServlet` | `com.ecount.web` | Diagnostic HTTP servlet showing MUX connection status |
| `DBConnectionTestDAO` | `com.ecount.service.db` | Unused/scaffold DAO for DB connectivity testing |

## 3. Protocol Implementation Details

### ISO 8583 Message Flow
The packager used is `ISO87APackager` (ISO 8583:1987 format A), meaning messages are fixed-length bitmap-based. The `PostChannel` transport uses a 2-byte length prefix header, consistent with the POST/VISA II gateway protocol.

**Sign-on flow** (`MyChannel.login()`, lines 120–131):
- Sends MTI `0800` with field 7 (date/time), field 11 (STAN=`000001`), field 70 (`061`)
- Expects response MTI `0810` with field 39 = `0` (approved)

**Keepalive flow** (`KeepAlivePos.run()`, lines 32–48):
- Sends MTI `0800` with field 70 = `301` every 120 seconds
- Waits 30 seconds for response; on timeout, calls `mux.getISOChannel().reconnect()`

### Limitations in Current Implementation
- **STAN is always `000001`** (fields 11 in both login and keepalive): Proper ISO 8583 requires a unique STAN per transaction for interchange reconciliation. This is a significant protocol defect.
- **No response code validation on keepalive**: The pong response is checked for null but field 39 is not inspected, meaning the host could return a non-zero response code and the connector would treat it as healthy.

## 4. Configuration Management

The connector reads a single external properties file at a hardcoded path (`StartupServlet.java` line 65):
```
D:\c-base\config\posconnector\application-config.properties
```

Expected properties (inferred from `StartupServlet.java` lines 78–79):
```properties
fdr.host.ip=<IP address of FDR POS host>
fdr.host.port=<TCP port>
```

This hardcoded path couples the application to the Windows filesystem layout of the deployment host. A proper solution would use Spring's `@PropertySource` with environment variable overrides or an external configuration service (Spring Cloud Config or Azure App Configuration, as used by `prepaid-parent_PARENT`).

## 5. Spring Context Configuration

The Spring 1.x application context (`pos-connector-context.xml`) declares:
- A JNDI-backed `BasicDataSource` via `JndiObjectFactoryBean` pointing to `java:comp/env/jdbc/EcountCoreDataSource` (line 21–23) — container-managed connection pooling.
- A `DBConnectionTestDAO` bean wired to that data source (line 26–28).

The `web.xml` loads this Spring context via `ContextLoaderListener` and registers:
- `PosShutdownListener` as a shutdown hook
- `StartupServlet` (load-on-startup=0) for initialization
- `ServiceServlet` (load-on-startup=0, URL pattern `*.do`) for diagnostics

## 6. Thread Safety Considerations

| Component | Threading Concern |
|---|---|
| `ISOMUX` | Manages its own thread internally; thread-safe per jPOS design |
| `KeepAlivePos` | Single dedicated thread at `MAX_PRIORITY` — may starve other threads in Tomcat JVM |
| `POSMessageListener.process()` | Called from jPOS MUX thread; `m.clone()` makes a copy but exception handling (`//blah`, `//blah2`) is empty, silently swallowing errors |

## 7. Solution Modernization Blueprint

A recommended modernization path would:

1. **Replace jPOS 1.5.2 with jPOS 2.x** and upgrade Spring to Spring Boot 3.x (as standardized in `prepaid-parent_PARENT` version 6.0.13).
2. **Externalize configuration** using Spring Boot `application.yml` + Azure App Configuration or GitHub Secrets.
3. **Implement structured logging** with SLF4J + log4j2 (inherited from `prepaid-parent_PARENT`), masking sensitive ISO fields before logging.
4. **Add metrics** via Micrometer (message rate, error rate, reconnection count).
5. **Implement proper STAN generation** — a thread-safe incrementing counter (mod 999999) persisted in Redis or database.
6. **Add integration tests** using jPOS's `ISOServerTestCase` or WireMock to simulate the FDR host.
7. **Containerize** and deploy via Kubernetes with liveness probes checking MUX connectivity.

## 8. Security Solution Controls Required

For PCI DSS compliance, the following security controls must be implemented as part of any solution update:

1. **TLS 1.2/1.3** on the outbound TCP socket to FDR (replace `PostChannel` with jPOS `TLSChannel`).
2. **Log masking**: Replace `m.dump(System.out)` with a field-level log method that masks field 2 (PAN) as first6/last4 and suppresses fields 35, 36, 52, 55.
3. **Remove commented-out credentials** from `pos-connector-context.xml` (lines 12–13).
4. **Remove commented-out IP addresses** from `StartupServlet.java` (lines 82–84).
5. **Vulnerability remediation**: Upgrade all dependencies to versions without known CVEs (see 03_devops_operations.md).
