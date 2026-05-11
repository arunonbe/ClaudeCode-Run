# DevOps / Operations View — service-parent_PARENT

## Build System

- **Artifact type**: Maven parent POM (`<packaging>pom</packaging>`)
- **GroupId**: `com.parents`; **ArtifactId**: `service-parent`; **Version**: `9.0.1-SNAPSHOT`
- **Parent**: `com.parents:prepaid-parent:4.0.1` (Onbe's root prepaid parent POM)
- **Purpose**: Provides shared Maven configuration for all Gen-1 and Gen-2 service projects; mainly documentation and repository configuration per the POM description
- **SCM**: GitLab (`gitlab.com/northlane/development/application-development/libraries/service-parent.git`) — this is a Northlane/Gen-2 repository now hosted on GitHub
- **Build extension**: `org.apache.maven.wagon:wagon-webdav:1.0-beta-2` — WebDAV wagon for Maven repository upload; extremely old

## CI/CD Pipeline

- **GitHub Actions**: `.github/workflows/codeql-java.yml` — CodeQL static analysis (Java); though there is no Java source, CodeQL is configured (will produce no meaningful results for a POM-only repo)
- **GitLab CI**: `.gitlab-ci.yml` present — migration from GitLab to GitHub Actions is in progress; dual CI pipelines exist
- **Dependabot**: `.github/dependabot.yml` — automated dependency update PRs
- **No deployment workflow**: Parent POM artifacts are published to the Maven repository when a child project triggers a release; there is no standalone deployment pipeline for this POM.

## Deployment Model

- **Not deployed to runtime**: Parent POMs are build artifacts only. They are published to the internal Nexus/GitHub Packages Maven repository and consumed by child projects via `<parent>` declarations.
- **Version `9.0.1-SNAPSHOT`**: The SNAPSHOT suffix means this is not a stable release. Child projects using `9.0.1-SNAPSHOT` will pick up the latest SNAPSHOT build each time, which can cause non-reproducible builds.

## Runtime

None — this is a build-time-only artifact.

## Secrets Management

- No secrets are managed by a parent POM at runtime
- Build-time: The Nexus repository URL and credentials referenced in the POM are managed by the Maven settings file (`.mvn/wrapper/settings.xml` in child projects), not in the POM itself
- The WebDAV wagon plugin configuration does not contain credentials (externalized to settings.xml)

## Observability

Not applicable — parent POM is not a deployed runtime artifact.

## Known EOL Runtimes and CVEs

- **`wagon-webdav:1.0-beta-2`**: This WebDAV wagon for Maven is extremely old (pre-2010 era). Modern Maven deployments use HTTPS or GitHub Packages. The beta tag indicates this was never a stable release.
- **HTTP repository URLs**: Both the Nexus URL (`http://d-na-stk01.nam.wirecard.sys:8080/nexus/`) and the Codehaus Snapshots URL (`http://snapshots.repository.codehaus.org/`) use unencrypted HTTP. Maven 3.8.1+ enforces HTTPS for remote repositories by default; this POM may cause build failures in modern Maven versions unless `http` blocking is explicitly disabled.
- **Codehaus Snapshots repository**: Codehaus (the open-source hosting organization) shut down in May 2015. The URL `http://snapshots.repository.codehaus.org/` no longer resolves. Any child project attempting to resolve plugins from this repository will encounter network failures or timeouts during builds.
- **`9.0.1-SNAPSHOT` version**: Using SNAPSHOT versions as parent POM versions in production builds violates Maven best practices and the enforcer rules configured in child projects. A release version should be cut and used.
- **GitLab SCM reference**: The `<scm>` block points to `gitlab.com/northlane/...`, which reflects the Wirecard/Northlane era GitLab organization. If this repository is now on GitHub (confirmed by presence of GitHub Actions), the SCM block must be updated to reflect the current repository location.
- **Nexus at Wirecard hostname**: `d-na-stk01.nam.wirecard.sys` is a Wirecard internal hostname. Post-acquisition, this server may no longer be accessible. Child projects depending on artifacts resolved from this Nexus instance may have build failures if the hostname is unreachable.
- **Strategic risk**: Stale repository references and dead plugin repositories in a foundational parent POM can cause cascading build failures across all Gen-1/Gen-2 services that inherit from it. Resolving the dead Codehaus reference and updating repository URLs to current infrastructure is a priority maintenance task.
