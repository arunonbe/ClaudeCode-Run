# Solution Architect Report — petstore-spring-flux-rest-server

## API Surface

The API is defined by the Petstore OpenAPI specification (`petstore/v2/petstore-expanded-openapi.yaml`). The implemented endpoints are:

| Method | Path | Controller Method | Notes |
|---|---|---|---|
| GET | /pets | `findPets()` | Returns all pets as a stream (tags/limit params ignored) |
| POST | /pets | `addPet()` | Creates a new pet |
| GET | /pets/{id} | `findPetById()` | Returns pet by ID |
| DELETE | /pets/{id} | `deletePet()` | NOT IMPLEMENTED — throws NotImplementedException |

All endpoints are served via Spring WebFlux on Netty, published to internal Azure APIM at path prefix `/api/petstoreflux`.

## Security Posture

### Strengths
- CodeQL static analysis active (weekly scheduled + PR-triggered)
- Dapr secret store integration — no hardcoded credentials in YAML
- BlockHound verification (`BlockHoundTests.java`) — ensures no blocking calls in reactive pipeline
- Log correlation testing (`LogCorrelationTests.java`) — ensures distributed trace IDs present in logs
- Internal APIM only — not exposed on external gateway
- Brave tracing injected for distributed trace context propagation
- `@Retryable` on transient R2DBC exceptions — resilient to transient SQL failures

### Critical Finding 1 — Container Vulnerability Scanning Disabled

**File:** `.github/workflows/deployment.yml`, line 39
```yaml
CONTAINER_SCAN: false   # container scan frequently fails, so disabling it temporarily
```
Container scanning is disabled with no remediation deadline. The `bellsoft/liberica-openjre-alpine:21` base image and Alpine OS packages may contain unpatched CVEs that are invisible to the CI pipeline. For a reference application that teams use as a template, this normalizes disabling security scanning.

**PCI DSS mapping:** Req 6.3.3 (security vulnerabilities identified and addressed), Req 11.3.1 (vulnerability scanning).

**Remediation:** Re-enable container scanning. If the container scan tool is unreliable, fix the tool rather than disabling the scan. Consider using `containerscan` with an `allowedlist.yaml` (the file `.github/containerscan/allowedlist.yaml` exists, suggesting this was configured but then the whole scan was disabled).

### High Finding 2 — Double-Retry Anti-Pattern

**File:** `petstore-spring-flux-rest-server-impl/src/main/java/com/onbe/petstore/controller/PetStoreControllerDelegate.java`, line 25 and
`petstore-spring-flux-rest-server-impl/src/main/java/com/onbe/petstore/service/impl/PetServiceImpl.java`, line 60

`@Retryable` is applied at both the controller class level and at the service method level (`getPetById`). For `findPetById`, this creates compounded retry behavior: the controller retries up to 3 times, and for each controller attempt, the service retries up to 3 times — up to 9 total attempts. Under sustained R2DBC transient failures, this could cause extended request queuing and memory pressure.

**Remediation:** Remove `@Retryable` from the controller class and apply it only at the service layer where the transient exception originates.

### High Finding 3 — Floating Docker Base Image Tag

**File:** `petstore-spring-flux-rest-server-boot/Dockerfile`, line 1
```dockerfile
FROM bellsoft/liberica-openjre-alpine:21
```
The `:21` tag is mutable — BellSoft may push a new image under this tag at any time. This means two identical source code versions could produce containers with different JRE contents, violating build reproducibility (PCI DSS Req 6.2) and potentially introducing an unvetted JRE update.

**Remediation:** Pin to a digest: `FROM bellsoft/liberica-openjre-alpine:21@sha256:<digest>` and update deliberately during maintenance cycles.

### Medium Finding 4 — `startup.sh` Executed as Root in Container

**File:** `petstore-spring-flux-rest-server-boot/Dockerfile`, line 15
```dockerfile
CMD ["/bin/bash", "-c", "source ./startup.sh; java $JAVA_TOOL_OPTIONS -jar ./${JAR_NAME}"]
```
No `USER` directive is present in the Dockerfile. The container runs as root (default). Running a JVM application as root in a container is a security risk — container escape exploits have greater impact when the container process is root.

**Remediation:** Add a non-root user:
```dockerfile
RUN addgroup -S app && adduser -S app -G app
USER app
```

### Medium Finding 5 — Information Disclosure via Secret Name in YAML

**File:** `petstore-spring-flux-rest-server-boot/src/main/resources/application.yaml`, line 47
```yaml
dapr:
  secrets:
    secrets:
      - MERCHANTENRICHMENT_TRIPLE_APITOKEN
```
The secret name `MERCHANTENRICHMENT_TRIPLE_APITOKEN` discloses the name of an external vendor integration (Triple, a merchant enrichment service) and the internal naming convention for API tokens. While this is committed to a repository that internal teams can access, it is discoverable by any Onbe employee with repository access. Consider using a more generic placeholder in the reference application (e.g., `EXTERNAL_API_TOKEN`).

### Medium Finding 6 — `AppConfigurationRefresh.refreshConfigurations().block()` on Reactor Scheduler

**File:** `petstore-spring-flux-rest-server-impl/src/main/java/com/onbe/petstore/config/PetStoreConfig.java`, line 55
```java
val refreshed = appConfigurationRefresh.refreshConfigurations().block();
```
`.block()` is called inside a scheduled task. Depending on the `TaskScheduler` implementation, this may execute on a Reactor scheduler thread, which is a blocking call on a non-blocking thread. This is precisely what BlockHound is configured to detect — but the scheduled task may not be exercised by the BlockHound test. Spring's `@EnableScheduling` uses a separate thread pool by default, which may or may not be a virtual thread pool.

**Remediation:** Verify the scheduler is backed by virtual threads or a dedicated blocking thread pool. Add a comment explaining why `.block()` is acceptable in this context.

## Technical Debt

- `findPets()` always delegates to `findAll()` with `delayElements(500ms)` — the production-useful filter/limit logic is commented out. This is a demo artifact that should not be copied into production services.
- `deletePet()` always throws `NotImplementedException` despite a feature flag check — the feature flag check is dead code.
- `pig.template` file at the repository root is a template file for the `io.brachu:pig` (package-info generator) Maven plugin — not a security concern but adds noise.
- Maven wrapper JAR binary committed to source — supply chain risk that should be addressed by migrating to script-based Maven wrapper.

## Recommendations

1. Re-enable container scanning immediately; fix the allowedlist rather than disabling the scan.
2. Add `USER app` to the Dockerfile to run the JVM as a non-root user.
3. Pin the Docker base image to a digest for reproducible builds.
4. Remove duplicate `@Retryable` annotation from the controller class; keep only service-layer retry.
5. Replace `MERCHANTENRICHMENT_TRIPLE_APITOKEN` with a generic placeholder in the reference application YAML.
6. Add explicit warning comments on demo-only code patterns (`findAll()` with `delayElements`, `deletePet()` stub).
