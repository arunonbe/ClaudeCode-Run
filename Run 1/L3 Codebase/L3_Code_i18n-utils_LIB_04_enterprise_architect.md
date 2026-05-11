# Enterprise Architect Report — i18n-utils_LIB

## 1. Platform Generation Assessment

`i18n-utils_LIB` is the **oldest-generation library** in the analyzed Onbe portfolio:

| Indicator | Evidence |
|---|---|
| Java 1.5 source/target | `pom.xml` lines 56–59 |
| JUnit 3.8.1 | `pom.xml` line 114 — released 2002 |
| JSP 2.1 API | `pom.xml` line 119 — Java EE 5, released 2006 |
| `javax.servlet.jsp` namespace | Pre-Jakarta EE namespace (changed in Jakarta EE 9, 2020) |
| `com.citi.prepaid` parent POM | Citi Prepaid brand — pre-eCount/Wirecard era |
| `com.ecount.utils` package | eCount brand (Citi-era subsidiary) |
| Wirecard SCM URL | `gitlab.wirecard-cloud.com/issuing/wdnam/prepaid/applications/modules/i18n-utils` |
| Wirecard Nexus | `d-na-stk01.nam.wirecard.sys` |
| `new Double()` / `new Integer()` constructors | Deprecated since Java 9 |
| No Spring, no dependency injection | Pre-Spring era utility design |
| Version `2020.9.10` | Last released September 2020 |

This places the library at approximately **15–20 years old** in design generation, written during the Citi Prepaid / early eCount period (circa 2005–2010) and sporadically maintained through acquisitions. It predates Spring Boot, Azure, and even Java 8 patterns. It is **Generation 0** — older than every other repository in the analyzed set.

---

## 2. Role in Enterprise Architecture

### 2.1 Integration Position

`i18n-utils_LIB` is a **horizontal infrastructure library** — it has no upstream dependencies on other Onbe services and is consumed by all JSP-based web applications:

```
[Browser (JavaScript Date.getTimezoneOffset())]
    |
    | browserOffset value submitted via form
    v
[JSP Web Application (Tomcat/JBoss)]
    |
    | <%@ taglib uri="http://ecount.com/tags/i18n-taglib" %>
    | <i18n:captureTimeZone timezoneOffset="${tz}" />
    | <i18n:formatCurrency value="${balance}" locale="${locale}" />
    v
[i18n-utils_LIB] ← This library (in WEB-INF/lib/)
    |
    | I18NUtils.formatCurrency() / formatDate() / etc.
    v
[Formatted HTML output to browser]
```

Unlike the other analyzed repositories, `i18n-utils_LIB` has no dependencies on databases, external APIs, or other Onbe services. It is purely a presentation utility.

### 2.2 Consumer Scope

The library is consumed by all JSP-based applications across Onbe's portfolio that display financial data to users. Given the broad package (`com.ecount.utils.i18n`) and the TLD URI (`http://ecount.com/tags/i18n-taglib`), this library was intended as the organization-wide standard for locale formatting. Replacement or modification affects every consuming application simultaneously.

---

## 3. Architecture Patterns

### 3.1 Static Utility Class Pattern

`I18NUtils` is a pure static utility class — no instances, no state, no dependency injection. All methods are `public static`. This pattern was common in pre-Spring Java development (2000–2008) and is safe for concurrent use as long as the `DecimalFormat` instances are created per-call (which they are — no shared mutable state).

### 3.2 JSP Tag Extension Pattern

The tag classes follow the JSP 2.1 `SimpleTagSupport` pattern:
- `CommonTagSupport` extends `SimpleTagSupport` (abstract base)
- Concrete tags extend `CommonTagSupport` and implement `doTag()`
- Tag attributes are set via JavaBean setters following JSP tag convention

This pattern is correct for JSP 2.1 but is incompatible with Jakarta EE 9+ which renamed the `javax.servlet.jsp` namespace to `jakarta.servlet.jsp`. Any upgrade of the consuming application's container to Jakarta EE 9+ will break this library.

### 3.3 Inheritance Chain

```
SimpleTagSupport (javax.servlet.jsp.tagext)
  └── CommonTagSupport (abstract)
        ├── FormatCurrency
        │     ├── FormatNumber
        │     └── CurrencyHeading
        │           └── CurrencySymbol
        └── DisplayDate
              ├── DisplayDateTime
              └── DisplayTime
```

`CurrencySymbol` extends `CurrencyHeading` (which extends `CommonTagSupport`), and `DisplayDateTime` and `DisplayTime` extend `DisplayDate`. `FormatNumber` extends `FormatCurrency`. This inheritance chain is shallow and functional, though a composition-based design would have been preferable.

`CaptureTimeZone` extends `SimpleTagSupport` directly (not `CommonTagSupport`) — it handles only timezone offset, not locale or value.

---

## 4. Dependencies

### 4.1 Runtime Dependencies

| Dependency | Version | Risk |
|---|---|---|
| `javax.servlet.jsp:jsp-api:2.1` | Java EE 5 (2006) | HIGH — namespace incompatible with Jakarta EE 9+ |
| JDK 1.5+ | Java 5 | CRITICAL — EOL since October 2009 (Oracle) |

### 4.2 Consuming Application Dependencies

Any consuming web application must:
1. Run on a container that supports the `javax.servlet.jsp` namespace (Tomcat 8.x or earlier, or JBoss/WildFly pre-Jakarta EE migration)
2. Include `i18n.jar` in `WEB-INF/lib/`
3. Be able to resolve `com.ecount.utils:i18n-utils:2020.9.10` from the Wirecard Nexus during build

---

## 5. Fit / Gap Analysis Against Onbe Target Architecture

| Dimension | Current State | Target State Gap |
|---|---|---|
| Java version | Java 1.5 | Java 21 LTS |
| Namespace | `javax.servlet.jsp` | `jakarta.servlet.jsp` (Jakarta EE 10+) |
| Deployment pattern | WAR in-lib dependency | Spring Boot Starter / NPM component library |
| UI framework | JSP tag library | React / Angular / Thymeleaf |
| Artifact repo | Wirecard Nexus | Azure Artifacts / GitHub Packages |
| CI/CD | No pipeline | GitHub Actions |
| Test coverage | Manual only | JUnit 5 + assertion library |
| Build | Maven (no deploy pipeline) | Maven + automated publish |
| Observability | None | N/A (utility library) |
| Character encoding | ISO-8859-1 workaround (`fixSymbol`) | UTF-8 everywhere |

The most critical gap is the **`javax` → `jakarta` namespace migration**. If any consuming application upgrades to Jakarta EE 9+, this library becomes incompatible at the classpath level — `SimpleTagSupport` would be in `jakarta.servlet.jsp.tagext`, not `javax.servlet.jsp.tagext`.

---

## 6. Migration Complexity Assessment

Migration complexity is rated **LOW-MEDIUM** for the following reasons:

1. **Small codebase**: 11 Java files, 553 lines in the core class, minimal dependencies. The entire library could be rewritten in a few days.

2. **Well-defined interface**: The static method signatures on `I18NUtils` are stable and well-documented. Migration to a Spring `@Component` or a `@Bean` factory is straightforward.

3. **Jakarta EE namespace change**: All `javax.servlet.jsp.*` imports must become `jakarta.servlet.jsp.*`. This is mechanical — a find-and-replace across the source files.

4. **JSP replacement scope**: If consuming applications migrate from JSP to Thymeleaf, React, or Angular, the JSP tag library becomes obsolete. The `I18NUtils` static methods remain valuable as a server-side formatting utility (e.g., for rendering API responses or emails), but the tag classes become dead code.

5. **Java version upgrade**: Moving from Java 1.5 to Java 21 is trivial for this codebase. The only Java-version-specific issues are the deprecated `new Double()`, `new Integer()`, `new Float()`, and `new Long()` constructor calls in `CommonTagSupport.java`.

---

## 7. Lifecycle Recommendation

1. **Short-term**: Migrate Nexus publishing to Azure Artifacts / GitHub Packages to unblock downstream builds
2. **Short-term**: Update `pom.xml` to Java 11 or 17, replace deprecated `new Double()`/`new Integer()` constructors with `Double.valueOf()`/`Integer.valueOf()`
3. **Medium-term**: Migrate `javax.servlet.jsp` imports to `jakarta.servlet.jsp` for Jakarta EE 9+ compatibility
4. **Medium-term**: Replace JUnit 3.8.1 with JUnit 5; convert `TestI18NUtils.main()` into proper `@Test` methods with assertions
5. **Long-term**: Evaluate whether consuming JSP applications are being migrated to a modern UI framework; if so, deprecate the JSP tag classes while retaining `I18NUtils` static methods
