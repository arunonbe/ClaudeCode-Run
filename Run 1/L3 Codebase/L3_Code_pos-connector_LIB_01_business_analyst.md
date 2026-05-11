# pos-connector_LIB — Business Analyst View

## 1. Repository Purpose and Business Context

`pos-connector_LIB` is a legacy Java web application (packaged as a WAR) that provides the connectivity bridge between Onbe's prepaid card platform and Point-of-Sale (POS) terminal networks. Its primary responsibility is to maintain a persistent, always-on TCP/IP connection to a card-present transaction host (identified in code as "fdr" — First Data Resources), send ISO 8583 messages for card-present authorization flows, and relay responses back to internal platform components.

In the broader Onbe payments ecosystem, card-present transactions require a dedicated channel that differs substantially from REST-based card-not-present flows. This component fills that role, acting as the on-premises POS gateway.

## 2. Business Capabilities Provided

| Capability | Description |
|---|---|
| Host Connectivity | Maintains a persistent TCP connection to the FDR (First Data Resources) POS host |
| Login / Logoff Lifecycle | Sends ISO 8583 MTI 0800 sign-on (field 70 = 061) and sign-off (field 70 = 062) messages on connect/disconnect (`MyChannel.java`, lines 120–143) |
| Message Processing | Receives inbound ISO 8583 messages, clones them, sets direction to OUTGOING, and sends acknowledgements (`POSMessageListener.java`, lines 28–59) |
| Keep-Alive / Heartbeat | Sends periodic MTI 0800 network management messages (field 70 = 301) every 120 seconds; detects and recovers from dropped connections (`KeepAlivePos.java`, lines 32–53) |
| Database Connectivity | Provides a JNDI-backed data source (`java:comp/env/jdbc/EcountCoreDataSource`) for any database needs (`pos-connector-context.xml`, line 22) |

## 3. Business Process Flow

1. At application startup (`StartupServlet.init()`), the connector reads host configuration from `D:\c-base\config\posconnector\application-config.properties` (hardcoded path, `StartupServlet.java` line 65).
2. An `ISOMUX` multiplexer is created, connecting to the FDR host on the configured IP and port.
3. On successful TCP connection, an ISO 8583 sign-on message is sent.
4. A background `KeepAlivePos` thread monitors the connection every two minutes; on heartbeat failure, it triggers a reconnect.
5. Inbound POS transaction messages arrive via `POSMessageListener`; they are cloned and an acknowledgement response is issued.
6. On shutdown (`PosShutdownListener`), a logoff message (field 70 = 062) is sent.

## 4. Key Business Rules and Configuration

- **Host endpoint**: Resolved from `fdr.host.ip` and `fdr.host.port` properties in the external config file.
- **Heartbeat interval**: 120 seconds (2 minutes); configurable only by code change.
- **Heartbeat timeout**: 30 seconds wait for pong before declaring link down.
- **Packager**: ISO 8583 `ISO87APackager` (ISO 1987 format A), consistent with first-generation card scheme message formats.
- **Session timeout**: 30 minutes (web.xml line 36), relevant for the management servlet.

## 5. Stakeholder Impact

- **Card Operations**: Any outage of this connector directly impacts card-present (POS) authorization availability.
- **Risk / Compliance**: The connector does not implement any rate limiting or message validation on inbound ISO 8583 payloads, representing a potential compliance gap for PCI DSS requirement 6.4 (protecting public-facing applications).
- **Finance / Settlement**: POS transaction acknowledgements feed downstream settlement processes; failure to ACK can result in transaction reconciliation breaks.

## 6. Gaps and Business Risks

1. **Hardcoded config path** (`D:\c-base\config\posconnector\application-config.properties`): This creates environment coupling and is a deployment risk for containerized or cloud-hosted deployments.
2. **No input validation on ISO 8583 messages**: `POSMessageListener.process()` clones and echoes without validating field content (line 30–43), which could allow malformed messages to propagate.
3. **Commented-out production/staging IP addresses** (`StartupServlet.java` lines 82–84) are present in source code — a PCI DSS concern.
4. **Commented-out hardcoded credentials in Spring XML**: `pos-connector-context.xml` lines 12–13 contain a commented-out username `andrewc` and password `andrewc` for a dev database. Even commented out, this is a credential exposure risk that should be removed.
5. **Legacy dependency versions**: Spring 1.2.7, jPOS 1.5.2, and Log4j 1.2.8 (all from circa 2005–2006) are end-of-life and have known critical CVEs.
