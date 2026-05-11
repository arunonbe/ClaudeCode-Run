# DevOps and Operations Analysis — notification-framework_SVC

## Repository Structure

Multi-module Maven project with four deployable modules:

```
notification-framework_SVC/
├── pom.xml                           — Parent POM (groupId: com.ecount.service.notification)
├── EventHandler/                     — Event handler service
│   ├── notification-event-handler-client/   — XML-RPC client for external callers
│   ├── notification-event-handler-common/   — Shared DTOs
│   └── notification-event-handler-impl/     — Implementation
├── RulesEngine/                      — Notification routing rules
├── Subscriber/                       — MQ subscriber + orchestration
└── Mailer/                           — Template resolution + email delivery
    ├── notification-mailer-common/          — Interfaces and DTOs
    ├── notification-mailer-impl/            — Cache manager, DAO, delivery channels
    └── notification-mailer-service/         — Servlet entry point + health check
```

## CI/CD Pipeline

Four separate GitHub Actions workflows deploy each module independently:

| Workflow | Target | Branch |
|---|---|---|
| `deployment-eventhandler.yml` | `NotificationEventHandlerSVC` | `main`, `feature/CRUS-8027-DelayConfigIssue` |
| `deployment-mailer.yml` | `NotificationMailerSVC` | `main`, `feature/CRUS-8027-DelayConfigIssue` |
| `deployment-rulesengine.yml` | `NotificationRulesEngineSVC` | `main`, `feature/CRUS-8027-DelayConfigIssue` |
| `deployment-subscriber.yml` | `NotificationSubscriberSVC` | `main`, `feature/CRUS-8027-DelayConfigIssue` |

All workflows call the shared workflow `Onbe/om-ci-setup/.github/workflows/java-workflow.yml@feature/CRUS-0000-skip`.

**Finding:** The shared workflow is pinned to `@feature/CRUS-0000-skip` — a feature branch, not a stable tag or SHA. If this branch is deleted or force-pushed, all four deployment pipelines will break simultaneously. Feature branches should not be used as stable CI/CD workflow references.

**Finding:** `MAVEN_ARGS: ' -s ./.mvn/wrapper/settings.xml -Dmaven.test.skip '` — Tests are skipped in all deployment workflows. This means no automated tests run before deployment to any environment. For a regulated payments notification service, this is a significant quality control gap.

## Build Configuration

- **Java version:** 21 (Maven compiler target in parent POM).
- **Build tool:** Maven with Maven Wrapper.
- **APIM publishing:** `PUBLISH_TO_APIM: true`, `INTERNAL_APIM: false`, `EXTERNAL_APIM: false` — The WSDL/API spec is published to an internal APIM gateway but not exposed externally.
- **Pact contract testing:** `VERIFY_PROVIDER_PACT: false` — Provider-side contract testing is disabled.

## Deployment Architecture

Each module deploys as a separate JVM process (standalone jar with embedded servlet for Mailer, or standalone service). The `notification-mailer-service` module main class is `com.ecount.service.notificationmailer.core.NotificationMailerService`.

The `Mailer/notification-mailer-service/src/main/java/.../xmlrpc/NotificationnoMailerServlet.java` suggests the Mailer exposes an XML-RPC endpoint (legacy J2EE servlet pattern), implying deployment in a servlet container (Tomcat). The GitHub workflow uses `DOCKERFILE_PATH: "./Mailer/notification-mailer-service/Dockerfile"` — containerised deployment.

## Container Scanning

`deployment-mailer.yml` does not include container scan configuration. The `.trivyignore` file exists at the repo root, indicating Trivy was previously configured but is not currently integrated into the active workflow.

## Health Check

`Mailer/notification-mailer-service/src/main/java/.../health/HealthCheck.java` — A health check endpoint exists for the Mailer service. The workflow publishes to `BACKEND_SUFFIX: "/services/notificationMailerSVC"`, suggesting it is deployed behind an API gateway.

## Dependency Management

Parent POM includes dependencies on several internal artifacts:
- `com.ecount.service.Core2:ecount-system:4.0.3` — Core platform library
- `com.citi.prepaid.service.core:xmlrpc:3.1.4` — Legacy Citi/Wirecard XML-RPC client (the `com.citi` group ID indicates this is inherited from the Citi-era prepaid platform)
- `com.citi.prepaid.service.core.client:director-client:2.0.2` — Director service client
- `opensymphony:quartz:1.6.3` — Quartz job scheduler version 1.6.3 (from 2007 — very old; current version is 2.3.x)

**Risk:** `opensymphony:quartz:1.6.3` has known vulnerabilities and is severely outdated. The Quartz scheduler in 1.x used serialised Java objects for job persistence which can be exploited via Java deserialization attacks if the scheduler database is accessible.

## Operational Considerations

### Cache Warm-Up Latency
On service startup, `NotificationMailerCacheManagerImpl.init()` calls `refreshTemplates()` which loads up to 65,000 template metadata records into EhCache. With ~500 bytes per entry, this is ~30 MB of cache, but the database query loading 65,000 rows may take 10–60 seconds depending on database performance. During this period, the service cannot process notifications (it will throw "no template found in cache" errors).

**Recommendation:** Implement a readiness probe that returns `503` until cache warm-up completes, preventing the load balancer from routing traffic to the instance before it is ready.

### Thread Safety
`NotificationMailerCacheManagerImpl.updateTemplateInCache()` uses `synchronized (cache)` and `synchronized (notificationServiceDAOFactory)` blocks. The cache refresh loop (`refreshTemplates()`) also acquires `synchronized (cache)`. Under high concurrency, this could cause request queuing behind the synchronised lock during cache refresh.

### Dead-Letter Handling
No dead-letter queue or retry-with-backoff mechanism is visible in the Mailer module. Failed notification deliveries update the `notification_queue` status to `SEND_FAILED` or `TEMPLATE_MERGE_ERROR` via `updateToNotificationMessageStatus()`. How these failed notifications are retried (if at all) is not visible in this repository.
