# workflow-service — DevOps / Operations View

## Build
- **Build tool**: Maven (with Maven Wrapper `mvnw`/`mvnw.cmd`)
- **Java version**: Java 21 (`maven.compiler.source=21`, `maven.compiler.target=21`)
- **Packaging**: Multi-module project (POM packaging at root); each module produces a JAR
  - `workflow-common` — shared domain model and interfaces
  - `workflowmanager-svc` — manager implementation with DAO and stored procedure adapters
  - `workflowagent-svc` — agent implementation with JMS listener
  - `workflow-xmlrpc` — XML-RPC endpoint and proxy layer
- **Parent POM**: `com.parents:prepaid-parent:6.0.13`
- **JMS profiles**: TIBCOJMS (default), WEBLOGICJMS, IBMMQ, ACTIVEMQ — selectable at build time
- **Build command (Jenkinsfile)**: `mvnw.cmd clean install -Dmaven.test.skip=true -P IBMMQ`

## Deployment
- **CI/CD**: Jenkinsfile (legacy Jenkins) + GitHub Actions for package publishing and CodeQL
- **Jenkins pipeline**: `Jenkinsfile` at root; builds with `IBMMQ` profile; deploys on `master` branch
- **GitHub Actions**: `github-package-publish.yml` — publishes to GitHub Packages on `main` push
- **GitHub Actions (template)**: Delegates to `Onbe/om-ci-setup/.github/workflows/java-package-publish.yml@main`
- **Target environment**: Not explicitly defined in the visible configs — likely deployed as JARs within an application container (IBM WebSphere/WebLogic inferred from IBM MQ profile default)
- **Java home (Jenkinsfile)**: `D:\\c-base\\JDK-AWS-8` — contradicts `maven.compiler.target=21`; Jenkinsfile was likely not updated when Java version was bumped

## Configuration Management
- **JMS configuration injected via build profile + property files**:
  - `${workflow.agent.queue.hostname}`, `${workflow.agent.queue.port}`, `${workflow.agent.queue.manager}`, `${workflow.agent.queue.transporttype}`, `${workflow.agent.queue.channel}`, `${workflow.agent.queue.name}`
  - `${workflow.agent.queue.username}`, `${workflow.agent.queue.password}`
  - `${workflow.agent.queue.max.msg.consumers}`
- **Workflow configuration keys**: `${workflow.configurationKey}`, `${workflowagent.configurationKey.jobload}`, etc. — resolved from Director service at runtime
- **Notification email**: `${notification.from.email.id}`
- **No Kubernetes or container config visible** — bare-metal/VM deployment assumed

## Observability
- **Logging**: Not directly visible in module POMs; inherited from `prepaid-parent`; likely log4j2 (based on platform patterns)
- **Test logging**: `log4j2-test.xml` present in `workflowmanager-svc/src/test/resources` — confirms log4j2 for tests
- **No APM, distributed tracing, or metrics configuration** visible in this repository
- **Workflow instance log**: Database-level audit log via `dbo.work_instance_get_log`; last_modified timestamp; `failed` flag
- **No health endpoint** defined for the workflow service JARs themselves

## Infrastructure Dependencies
| Dependency | Type | Details |
|-----------|------|---------|
| SQL Server (JobSvcDataSource) | RDBMS | Workflow state, instance, process definitions |
| IBM MQ (default profile) | JMS Queue | Agent task dispatch; `MQQueueConnectionFactory` |
| Director Service | Config service | Runtime workflow configuration via `getAgentSetting()` |
| Profile Service | Remote client | `profile-client` used in workflowagent-svc |
| Repository Service | Remote client | `repository-client` used in workflowagent-svc |
| ecount-core | Remote client | `ecount-core-client` used in workflowagent-svc |
| Event Service | Remote client | `eventserviceclient` used in workflowagent-svc |
| Order XML-RPC | Remote client | `orderxmlrpcclient` used in workflowagent-svc |
| JMS provider (TIBCO/WebLogic/ActiveMQ) | Alternate profiles | Switchable via build profile |

## Operational Risks
1. **Zombie instances**: Must be actively polled; no self-healing if scheduler that calls `turnZombies` goes down
2. **Java 21 in POM, Java 8 in Jenkinsfile**: Version mismatch means CI builds with the wrong JDK — likely produces incorrect bytecode or fails silently
3. **Tests skipped in CI**: `-Dmaven.test.skip=true` in all build stages
4. **IBM MQ credentials in property files**: No vault integration visible; plaintext on server disk
5. **Single consumer queue**: `max.msg.consumers` is externally configured but default profile does not show count — risk of under-provisioning
6. **JMS session is transacted** (`sessionTransacted=true`) — correct for reliability, but requires message broker to support transactions; must be verified against MQ config
7. **No dead-letter queue (DLQ) configuration visible**: Poison messages may block or recycle indefinitely

## CI/CD Pipeline
```
Jenkins (Jenkinsfile — legacy)
  → Build: mvnw.cmd clean install -Dmaven.test.skip=true -P IBMMQ
  → Deploy (master only): mvnw.cmd clean deploy -Dmaven.test.skip=true -P IBMMQ
  → Publishes JARs to Maven repository

GitHub Actions
  → github-package-publish.yml on main push
    → Delegates to Onbe/om-ci-setup java-package-publish.yml@main
    → MAVEN_BUILD_ARGS: "-s .mvn/wrapper/settings.xml -Dmaven.test.skip"
    → Publishes to GitHub Packages
  → codeql.yml: CodeQL security analysis on push/PR
  → dependabot.yml: Automated dependency update PRs
```
