# clientzone-help_SVC — DevOps & Operations View

## Build & Packaging

**Build tool**: Apache Maven 3.9.1 (enforced via Maven Wrapper — `.mvn/wrapper/maven-wrapper.properties`, line 17: `distributionUrl=.../apache-maven/3.9.1/apache-maven-3.9.1-bin.zip`).

**Artifact**: WAR file named `ClientZoneHelp.war` (pom.xml `<finalName>ClientZoneHelp</finalName>`, line 137), under the `jetty` profile which is active by default.

**Coordinates**:
- `groupId`: `com.citi.prepaid.web.clientzone`
- `artifactId`: `ClientZoneHelp`
- `version`: `1.0.4-SNAPSHOT`
- `packaging`: `war`

**Parent POM**: `com.citi.prepaid.web:webapp-parent:10.0.0` — this parent provides the base build configuration including Java compilation settings, plugin management, and likely the main Tiles definitions. The parent POM is not present in this repository; it must be resolvable from the Nexus or GitHub Packages repository.

**Key build dependencies** (all resolved at compile/runtime from Nexus/Maven Central):
- `com.ecount.web.tags:eccm:1.1.0` — ecount custom tag library providing `EccmSimpleInitializer` and content management tags
- `com.citi.prepaid.spring-dbctx:spring-dbctx-container:1.0.6` — Citi Prepaid Spring DB context container
- `com.citi.prepaid.springutils:springutils-generic:1.0.9`
- `org.springframework:spring:2.0.8` — Spring Framework 2.0.8 (extremely old)
- `struts:struts-el:1.2.8` — Apache Struts 1.2.8 (end-of-life since 2013)
- `taglibs:standard:1.1.2` + `javax.servlet:jstl:1.1.2`
- `log4j:log4j:1.2.14` (scope: provided)

**Maven plugins**: `maven-eclipse-plugin:2.4` for Eclipse WTP integration. No Maven Surefire, Failsafe, or Compiler plugin configurations are explicitly declared — these are inherited from `webapp-parent`.

**Maven Wagon**: `wagon-webdav:1.0-beta-2` extension is declared for artifact deployment via WebDAV.

**No Java source code to compile**: `src/main/java/.ignore` is the only file under the Java source root. The build produces a WAR that is purely a web artifact (JSPs, XML config, static content) plus declared dependency JARs.

## Deployment

**Target runtime**: Java Servlet 2.4 container (declared in `web.xml`, line 4: `web-app_2_4.xsd`). Tomcat is the implied target (references to Tomcat cluster in `struts-config.xml` comment, line 61: "a Serializable Multipart Request Handler to handle file upload in the tomcat cluster").

**Context path**: `/ClientZoneHelp` (declared in `META-INF/context.xml`, line 2: `<Context path="/ClientZoneHelp" privileged="true">`). The `privileged="true"` attribute gives this webapp access to container-internal resources in Tomcat.

**Welcome file**: `index.jsp`, which immediately redirects to `getHelp.do` (index.jsp, line 3: `<c:redirect url="getHelp.do" />`).

**Distributable**: The `web.xml` declares `<distributable/>` (line 9), indicating the application is designed to be deployable in a clustered/distributed servlet container. This requires that all session-stored objects be `Serializable`, which is why `com.ecount.one.struts.upload.SerializableCommonsMultipartRequestHandler` is used (struts-config.xml, line 64).

**External configuration dependency**: The application requires `${CBASE_HOME_URL}` to be set as a system/environment property at container startup. Without this, the `PropertyPlaceholderConfigurer` in `applicationContext.xml` will fail to resolve:
- `${CBASE_HOME_URL}/config/cz/clientzone.properties`
- `${CBASE_HOME_URL}/config/xContent/applicationContext-xContent.properties`
The `ignoreResourceNotFound=true` (line 18) and `ignoreUnresolvablePlaceholders=true` (line 19) guards mean the application may start but silently use empty/null values for all externally-sourced properties.

**Local development**: Jetty is configured as the default development server via the `jetty` Maven profile (pom.xml, lines 127-154) listening on port `${jetty.port}` defaulting to `8080`.

## Configuration Management

**Environment configuration pattern**: Properties are injected at runtime from files located at `${CBASE_HOME_URL}/config/`. This follows the Citi Prepaid/ecount convention of externalising environment config to a well-known filesystem path per deployment environment. No environment-specific Maven profiles (dev/test/prod) are defined in this POM beyond the `jetty` local-dev profile.

**Key configurable properties** (all resolved by `applicationContext.xml`):
- `ecount.InternationalType` — distinguishes international (EMEA) vs US instance
- `clientzone.help.context` — context path for the help application (injected into `helpApplicationContext` bean)
- `clientzone.context` — context path used for affiliate resolution in `affiliateContext.xml`
- `clientzone.agent` — agent identifier for affiliate config
- `clientzone.appId` — application identifier
- `cms.service.url`, `cms.service.context`, `cms.content.context`, `cms.name` — CMS backend connection

**ECCM rules**: `src/main/resources/eccm-rules.properties` configures the content management tag rule classes:
- `default-rule`: `ParameterIndexedImageRule` using `programid` request parameter
- `site-style`: `ParameterIndexedStyleRule`
- `header-image`: `SimpleTestRule`
- `image-list`: `SimpleTestMultiResultRule`
- `tac-include`: `ParameterIndexedIncludeRule`

**Maven repository configuration** (`.mvn/wrapper/settings.xml`):
- Active Nexus profile resolves internal artifacts from `https://d-na-stk01.nam.wirecard.sys:8081/nexus/content/groups/public/` (Wirecard internal Nexus — domain reflects Wirecard/STP lineage pre-Onbe).
- GitHub Packages: `https://maven.pkg.github.com/onbe/onbe_maven_releases` (line 111) — this is the current Onbe package registry.
- Credentials for Nexus and release repositories are stored in plaintext in this settings file.

## Observability

**Logging**: `log4j:1.2.14` is declared as a `provided` dependency, meaning it is supplied by the container. No `log4j.properties` or `log4j.xml` configuration is present in this repository — logging configuration is inherited from the container or parent application classloader.

**Application logging**: The only explicit logging call visible in source is `request.getSession().getServletContext().log("set affiliate.name to " + lAndf)` in `global_error.jsp` (line 19). This uses the servlet container's built-in log mechanism, not Log4j.

**Metrics/APM**: No metrics instrumentation, health check endpoints, or APM agent configuration is present in this repository.

**Tracing**: No distributed tracing configuration (no Jaeger, Zipkin, or OpenTelemetry) is present.

**Error visibility**: Errors are routed to the `global_error.jsp` page, which renders exception details to the browser. No structured error logging to a log aggregator is implemented within this WAR.

**Health endpoint**: No `/health` or `/actuator` endpoint is defined. The only entry point to assess liveness is whether the WAR deploys and `index.jsp` redirects without error.

## Infrastructure Dependencies

1. **Servlet Container**: Tomcat (version not specified; Servlet 2.4 minimum, Servlet 3.0+ compatible). Must support `<distributable/>` for clustered deployments.
2. **${CBASE_HOME_URL}**: A filesystem path accessible to the JVM process at startup where `config/cz/clientzone.properties` and `config/xContent/applicationContext-xContent.properties` are mounted.
3. **Nexus Repository Server** (`d-na-stk01.nam.wirecard.sys:8081`): Must be reachable at build time to resolve `com.citi.prepaid.*`, `com.ecount.*` internal artifacts.
4. **GitHub Packages** (`maven.pkg.github.com/onbe/onbe_maven_releases`): Required for newer Onbe Maven artifacts.
5. **CMS Service**: An external HTTP service at `${cms.service.url}` is wired as `cmsService` bean in `cmsContext.xml`. If the CMS service is unavailable at startup (and Spring requires eager initialisation), the application will fail to start.
6. **Parent POM** (`com.citi.prepaid.web:webapp-parent:10.0.0`): Must be resolvable from the Maven repository. This POM drives the entire build lifecycle, compiler settings, and likely Tiles definitions.
7. **Adobe Flash browser plugin** (end-user): Flash Player must be installed and enabled in the user's browser for `.swf` help videos to render. Flash reached end-of-life December 31, 2020 and all major browsers have removed support.

## Operational Risks

1. **Flash EOL — all video content non-functional**: Every SWF file in the `helpContent/` tree is unrenderable in any supported browser as of 2021+. The primary help delivery channel is broken in production.
2. **Spring 2.0.8 and Struts 1.2.8 — multiple known CVEs**: Both frameworks are severely outdated and unsupported. Struts 1.x reached end-of-life in 2013. Spring 2.0.8 is from 2008. Known remote code execution and cross-site scripting CVEs affect both.
3. **Log4j 1.2.14**: Log4Shell (CVE-2021-44228) primarily affects Log4j 2.x, but Log4j 1.x has its own set of unpatched CVEs (e.g., CVE-2022-23302, CVE-2022-23305) and has been EOL since 2015. The `provided` scope means the actual Log4j version is determined by the container, but if any Log4j 1.x is on the classpath, these CVEs apply.
4. **No automated tests**: No test source files exist (`src/test` tree is empty or absent). Deployments cannot be validated by a test suite.
5. **SNAPSHOT versioning in production**: `1.0.4-SNAPSHOT` is a non-stable, mutable artifact identifier. Two builds at the same version could produce different binaries, making deployments non-reproducible.
6. **Privileged Tomcat context**: `META-INF/context.xml` sets `privileged="true"`, which gives this web application access to Tomcat's internal MBeans and Valve objects. This is broader access than a help application requires.

## CI/CD

**GitHub Actions — CodeQL** (`.github/workflows/codeql.yml`):
- Triggered: manually (`workflow_dispatch`) or on a weekly schedule (Thursdays at 06:20 UTC: `cron: 20 6 * * 4`)
- Reuses shared workflow: `Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main`
- Runner: `self-hosted`, `X64`, `Linux`, `ubuntu-docker`
- Secrets: inherited from repository
- Language: Java (implied by `java-runner` parameter)
- **No build CI** (no compile/test/package workflow is defined). CodeQL is the only automated pipeline.

**Dependabot** (`.github/dependabot.yml`):
- Ecosystem: `maven`
- Directory: `/` (root `pom.xml`)
- Schedule: weekly
- Dependabot will raise PRs for dependency version updates but cannot resolve Citi/ecount internal artifacts that are not in Maven Central.

**No deployment pipeline**: There is no CD workflow defined. No Docker build, no Kubernetes manifest, no deployment script. Deployment mechanism is assumed to be an out-of-band WAR deployment to Tomcat (likely managed by a separate infra/ops pipeline).

**SVN origin**: The SCM section in `pom.xml` (lines 24-28) points to a Subversion repository at `http://ecsvn.office.ecount.com/svn/...`. The repository has been migrated to Git/GitHub but the `pom.xml` SCM block was not updated. This is a configuration artefact that may confuse Maven Release Plugin if invoked.
