# Enterprise Architect View — CONFIG_ci-templates

## Platform Generation
**Generation 2 (Gen-2)** — Legacy GitLab CI/CD automation layer. Uses on-premises Nexus artifact repository, Windows-based Tomcat application servers (via SMB deployment), and JDK 8. Represents the CI/CD foundation for the legacy monolithic application platform.

## Business Domain
**DevOps / Platform Engineering** — This repository is infrastructure/tooling, not a business domain service. It supports all payment platform domains by providing the build and delivery pipeline used by consumer-facing web applications, APIs, and batch services.

## Role in Platform
Central shared CI template library — the single source of truth for how Java applications are built, tested, and deployed in the DEV and QA environments. All application teams consume these templates rather than maintaining individual Jenkinsfiles or CI configurations.

Note: The repo name `CONFIG_jenkins-file` exists separately but contains only a README; Jenkins is referenced as a legacy mechanism. These GitLab CI templates are the active delivery automation.

## Dependencies
| Dependency | Type | Notes |
|------------|------|-------|
| GitLab CI/CD | Platform | Pipeline execution environment |
| Nexus Repository Manager | Artifact store | `d-na-stk01.nam.wirecard.sys` — legacy Wirecard DNS |
| ci-scripts repo (`northlane/infrastructure/scripts/ci-scripts`) | Runtime script dependency | Fetched at deploy time |
| `dperson/samba` Docker image | Deploy tool | SMB for Windows host file copy |
| `maven:3.6.3-jdk-8` Docker image | Build runtime | Docker Hub public image — supply chain risk |
| `alpine` Docker image | Verify runtime | Docker Hub public image |
| Mend/WhiteSource SaaS | SCA scanning | External service, opt-in |
| Target Tomcat hosts (`d-na-*`, `q-na-*` hostnames) | Deploy targets | Legacy on-prem infrastructure |

## Integration Patterns
- **Template inclusion**: Applications use `include: project:` to pull versioned templates from this repo
- **Parent-child pipelines**: `deployBridge.gitlab-ci.yml` implements GitLab parent-child pipeline pattern for multi-service deployments
- **Artifact passing**: JUnit reports and deployment metadata passed between stages as GitLab artifacts
- **Variable injection**: All environment-specific configuration (hosts, credentials) injected via GitLab CI variables at the project or group level

## Strategic Status
**Active but legacy.** This repo is the current CI/CD foundation for the Gen-2 Java platform. It is NOT designed for containerised or cloud-native workloads. A Gen-3 migration would replace these Tomcat deploy templates with Kubernetes/Helm or container registry pipelines.

The branch `SQ-4057-deploy-configuration-files` is referenced by CONFIG_qa's `.gitlab-ci.yml`, indicating active feature development on this repo.

## Migration Blockers
- Tight coupling to Windows Tomcat deployment via SMB (`dperson/samba`) — requires re-architecture for container-based delivery
- JDK 8 runtime — migration to JDK 17/21 required for modern Spring Boot and PCI DSS TLS compliance
- Nexus on `wirecard.sys` DNS — must migrate to new artifact registry before legacy DNS decommission
- Deploy scripts in separate `ci-scripts` repo — no version pinning; a breaking change to ci-scripts breaks all pipelines
- No Helm, Docker build, or container registry push steps — cannot deploy to Kubernetes without new templates
