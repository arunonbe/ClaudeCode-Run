# 04 Enterprise Architect — reminder-notification_LIB

## Platform Generation
Gen-1 / Legacy. Java 6, Spring 2.5.6, Spring Batch 2.1.1, Windows batch launcher, XML-only Spring configuration, Director-resolved DBCP connections. All characteristics of the original ecount/Northlane platform generation.

## Business Domain
Cardholder Engagement / Notification Services. Supports digital enrollment funnel for prepaid card programmes.

## Role
Reusable batch library: provides the "enrollment reminder" capability that can be embedded in programme-specific batch deployments. Not a standalone service; consumed by programme-specific job configurations that supply the Spring context XML and job name.

## Dependencies
| Dependency | Direction | Coupling |
|---|---|---|
| Director service | Outbound | Hard — all DB connections routed through it |
| ecountcore SQL Server DB | Outbound | Hard — member eligibility data |
| batchrepodatabase SQL Server | Outbound | Hard — Spring Batch job repository |
| cbaseapp SQL Server DB | Outbound | Hard — programme data |
| xPlatform (`com.ecount:xPlatform:2.5.35`) | Compile | Hard — email send, system config |
| xAffiliateService (`1.0.6`) | Compile | Hard — affiliate/programme lookup |
| director-client (`1.0.11`) | Compile | Hard — Director connection factory |

## Integration Patterns
- **Batch / schedule**: triggered by Windows Task Scheduler via `.bat`/`.vbs` launchers
- **Spring Batch chunk-oriented processing**: Reader (JDBC cursor) → Processor (none explicit) → Writer (notification send + history update)
- **Stored-procedure integration** for history writes; plain JDBC `PreparedStatement` for reads
- **Director pattern**: centralised connection registry decouples JDBC URL management from the application

## Strategic Status
**Sunset candidate.** The library is built on a Java 6/Spring 2.5 stack that is over 10 years past EOL. It performs a narrow function (enrollment reminder emails) that should be absorbed by a Gen-3 notification micro-service or a campaign management platform. Active business value is moderate (cardholder engagement), but the risk of running EOL components handling PII outweighs the cost of replacement.

## Migration Blockers
- Tight coupling to Director service for DB connections must be replaced with a Gen-3 secrets-managed JDBC connection pool
- xPlatform email dispatch must be replaced with a modern email service (e.g., SendGrid, AWS SES, Azure Communication Services)
- Spring Batch job metadata schema migration required when upgrading to Spring Batch 5.x
- No automated test coverage observed; migration requires test authorship before re-platforming
