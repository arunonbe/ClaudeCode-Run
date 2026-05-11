# DevOps and Operations View — logback-sanitize

## Build System

`logback-sanitize` is a Spring Boot 3.3.5 Maven project. Build configuration (`pom.xml`):

- **Java version**: 21
- **Spring Boot parent**: `3.3.5`
- **Maven Wrapper**: bundled
- **Packaging**: JAR
- **Group ID**: `com.onbe.logging`
- **Artifact ID**: `logback-sanitize`
- **Version**: `0.0.1-SNAPSHOT`

Unlike `log4j2-sanitize`, this project does **not** exclude `spring-boot-starter-logging` and does **not** add `spring-boot-starter-log4j2`. It relies on the default Logback stack bundled with `spring-boot-starter`. The Logback configuration is driven by `logback-spring.xml` which Spring Boot auto-detects.

Single custom dependency:
```xml
<dependency>
    <groupId>org.apache.commons</groupId>
    <artifactId>commons-text</artifactId>
    <version>1.12.0</version>
</dependency>
```

Build command:
```sh
./mvnw clean package
```

## CI/CD Pipeline

No CI/CD pipeline configuration (no `.gitlab-ci.yml`, no `.github/workflows/`). This is consistent with its proof-of-concept status. Requirements for promotion to a production library:

1. GitLab CI or GitHub Actions pipeline for build and test
2. OWASP Dependency Check plugin execution
3. Nexus publication step
4. Semantic versioning via git tag

## Deployment Model

As with `log4j2-sanitize`, this is a proof-of-concept, not an independently deployed service. Intended adoption path:

1. Promote `SanitizedMessageConverter` class to a published Maven library (`com.onbe.logging:logback-sanitize`)
2. Consumer services add the dependency and include `logback-spring.xml` `conversionRule` configuration
3. Or, embed the `SanitizedMessageConverter` directly in the `api-logging-lib` or equivalent shared library

### Spring Boot `logback-spring.xml` Adoption Pattern

The `logback-spring.xml` must be included in the consumer service's `src/main/resources/`. The `conversionRule` must be declared **before** any `<appender>` elements that use the `%m` token:

```xml
<configuration>
    <conversionRule conversionWord="m" class="com.onbe.logging.SanitizedMessageConverter"/>
    <appender name="CONSOLE" class="ch.qos.logback.core.ConsoleAppender">
        <encoder>
            <pattern>%d{HH:mm:ss.SSS} [%thread] %-5level %logger{36} - %m%n</pattern>
        </encoder>
    </appender>
    <root level="INFO">
        <appender-ref ref="CONSOLE"/>
    </root>
</configuration>
```

Note: `%m` in the pattern triggers `SanitizedMessageConverter.convert()`. Any appender using `%msg` (the long form alias) instead of `%m` will also trigger the converter since both resolve to the same `MessageConverter` slot.

## Testing

`LogbackSanitizeApplicationTests.java` contains only the Spring Boot context load test. No unit tests exist for `SanitizedMessageConverter`. Required test coverage:

| Test Case | Expected Behaviour |
|---|---|
| Input: `<script>alert(1)</script>` | Output: `&lt;script&gt;alert(1)&lt;/script&gt;` |
| Input: `\r\n fake log line` | Output: Should strip newlines (not currently done) |
| Input: null | Should not throw NPE (super.convert handles null) |
| Input: `4111111111110000` | Output: Should be masked (not currently done) |
| Input: 2000-char string | Output: Should not cause excessive memory use |

## Dependency Currency

| Dependency | Version | Status |
|---|---|---|
| Spring Boot | 3.3.5 | Current |
| Java | 21 | LTS, current |
| commons-text | 1.12.0 | Current; CVE-2022-42889 resolved |
| Logback | Via Spring Boot BOM (~1.5.x) | Current |
| SLF4J | Via Spring Boot BOM (~2.0.x) | Current |

No known critical CVEs in the declared dependency set.

## Operational Considerations

### Logback Configuration Debug Mode

`logback-spring.xml` line 2:
```xml
<configuration debug="true">
```
The `debug="true"` attribute causes Logback itself to print internal status messages (configuration loading, appender initialisation) to `System.out` on startup. **This should be removed or set to `false` in production** to avoid noisy output in container logs.

### Conversion Rule Ordering

The `conversionRule` must be declared before appenders in `logback-spring.xml`. Placing it after appender definitions can cause Logback to use the default `MessageConverter` for appenders declared before the rule.

### Pattern Compatibility

The `%m` conversion word is being overridden globally. This means any library or framework that uses `%m` in its own Logback pattern (e.g., test frameworks, embedded servers) will also have its log messages HTML-encoded. This is generally acceptable but should be validated in the test environment.

### Spring Boot Profile Support

`logback-spring.xml` (with the `-spring` suffix) allows Spring Boot profile-specific configuration using `<springProfile>` tags. This enables different log levels for dev/qa/prod without separate files.

### Performance

The `SanitizedMessageConverter` adds one `StringEscapeUtils.escapeHtml4()` call per formatted log message. Benchmarks from Apache Commons Text suggest this is sub-microsecond for typical log messages. Under TRACE-level logging in high-throughput services, the cumulative cost could be measurable — async appenders (`ch.qos.logback.classic.AsyncAppender`) are recommended for high-volume services.
