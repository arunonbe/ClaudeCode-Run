# security-audit-common_LIB — Enterprise Architect View

## Platform Generation
**Gen-1 / Gen-2 transition.** Core library code is Gen-1 (Spring XML context, jTDS, legacy Ecount-lineage patterns). CI/CD has been upgraded to Gen-2 patterns (GitHub Actions, Java 21 compilation, Nexus + GitHub Packages dual publishing, centralised reusable workflows). The VBScript data extract is firmly Gen-1 (Windows BCP, file-based credential injection).

## Business Domain
**Security & Compliance / Audit Logging.** Cross-cutting concern consumed by all customer-facing web applications across the Onbe/Citi Prepaid platform.

## Role in Platform
**Shared security audit library** — provides a single, consistent mechanism for all consumer applications to log security-relevant events to the central audit database. This is a foundational compliance component; without it, PCI DSS Req 10 logging obligations cannot be met for the consuming applications.

## Dependencies
### Consumed by (downstream consumers)
All consumer applications that use `SecurityAuditClientHelper` or `SecurityDataLogger` directly — these include OnePlatform (appId 6, CSI 158929) and ClientZone (appId 10, CSI 159547), and implied others given the breadth of `EventType` entries.

### Depends on (upstream)
| Dependency | Type | Notes |
|---|---|---|
| SQL Server | Data store | Central audit database via `CbaseappDataSource` JNDI |
| `com.parents:prepaid-parent:6.0.13` | Parent POM | Centralised dependency management |
| Spring Framework | Runtime | spring-context, spring-jdbc |
| jTDS | JDBC driver | Microsoft SQL Server connectivity |
| Lombok | Build-time | `@Slf4j` annotation |

## Integration Patterns
- **Library pattern** (JAR dependency): Consumer applications import this library and call `SecurityAuditClientHelper.sendMessage()`.
- **Stored procedure call**: All database writes go through `insert_security_audit_user_data` SP — decouples Java schema from SQL schema.
- **Spring XML bean wiring**: `securityAudit-context.xml` imported by consuming application contexts.
- **JNDI DataSource**: Container-managed connection pooling.

## Strategic Status
**Active and critical — compliance dependency.** Must be maintained for PCI DSS Req 10 compliance across all consuming applications. Current state is operationally functional but architecturally aged.

Strategic improvements needed:
1. Complete the ArcSight CEF stub to enable SIEM forwarding.
2. Replace VBScript export with a proper ETL job or log forwarding agent.
3. Enforce PAN masking at the library boundary before accepting `cardNumber`.
4. Upgrade jTDS to Microsoft JDBC driver (jTDS is unmaintained since 2012).

## Migration Blockers
- JNDI `CbaseappDataSource` — requires Tomcat container configuration; cannot migrate to standalone container (Kubernetes) without replacing JNDI with a Spring DataSource bean or cloud-native secret injection.
- jTDS driver — EOL, not compatible with SQL Server 2016+ encrypted connections.
- VBScript on Windows — not portable to Linux/container environments.
- `com.parents:prepaid-parent:6.0.13` — parent POM must be available in artifact registry.
