# eccm_LIB — Enterprise Architect Report

## Platform Generation

`eccm_LIB` is a **Generation 1 (Gen-1) component** — the oldest layer of the Onbe East platform. Evidence:
- Version history comments in `RuleManager.java` show creation in October 2004 (`User: Swilson Date: 10/21/04`)
- The SourceSafe-style `$History:` version control metadata (lines 8–27 of `RuleManager.java`) confirms this originated in Microsoft Visual SourceSafe — the version control system that predates CVS/SVN/Git
- Apache Lucene 2.0.0 (2006), Spring 2.0.2 (2007), Apache Struts 1.2.8 (2005), Commons HttpClient 3.0.1 (2004)
- The tag library name `eccm.tld` and namespace `eccm` are referenced throughout multiple web application repositories — this library has a very wide blast radius

---

## Role in the Enterprise Architecture

### Layer: Web Presentation / Content Management
`eccm_LIB` is the **presentation-tier content management library** that powers the multi-tenant rendering of all Gen-1 cardholder portal web applications.

```
┌──────────────────────────────────────────────────────────────┐
│  Cardholder Browser                                          │
└──────────────────────────┬───────────────────────────────────┘
                           │ HTTP request
┌──────────────────────────▼───────────────────────────────────┐
│  Gen-1 Web Applications (WAR files)                          │
│  clientzone_WAPP, enrollment_WAPP, scheduler_WAPP, etc.     │
│  (Use <eccm:*> and <xstruts:*> JSP tags from eccm_LIB)      │
└──────────────────────────┬───────────────────────────────────┘
                           │ tag evaluation
┌──────────────────────────▼───────────────────────────────────┐
│  eccm_LIB (THIS LIBRARY)                                     │
│  - Rules engine resolves affiliate-specific content          │
│  - CMSService queries Lucene index                           │
│  - Tags render affiliate images, styles, includes, links     │
└──────────────────────────┬───────────────────────────────────┘
                           │ reads content from
┌──────────────────────────▼───────────────────────────────────┐
│  xcontent_SVC (CMS content management service)               │
│  xContent filesystem: D:/c-base/Runtime/xContent/content    │
└──────────────────────────────────────────────────────────────┘
```

### Dependency Map

**Web Applications that depend on eccm_LIB** (inferred from platform inventory):
- `clientzone_WAPP` — client management portal
- `enrollment_WAPP` — cardholder enrollment portal
- `scheduler_WAPP` — job scheduling interface
- `workbench_WAPP` — internal operations workbench
- `csa_WAPP` — Customer Service Agent portal
- `bmcwizard_WAPP` — BMC wizard interface
- `dmt_WAPP` / `dmt-web_WAPP` — data management tool
- Any Gen-1 web application using `<eccm:*>` or `<xstruts:*>` tags

**Libraries eccm_LIB depends on:**
- `org.apache.lucene:lucene-core:2.0.0` — search engine
- `commons-httpclient:3.0.1` — HTTP content retrieval
- `struts:struts:1.2.8` — for `xstruts.tld` Struts tag integration
- `org.springframework:spring:2.0.2` — IoC container

---

## Integration Points

| Repository | Integration Type | Strength |
|---|---|---|
| `xcontent_SVC` | Content source (filesystem + HTTP) | High — provides Lucene index content |
| `xcontent-content_LIB` | Content library | High — shares content model |
| `clientzone_WAPP` | Consumer (JSP tags) | Critical — largest consumer |
| `enrollment_WAPP` | Consumer (JSP tags) | Critical |
| `csa_WAPP` | Consumer (JSP tags) | High |
| `xsearch_LIB` / `xsearch_SVC` | Potentially shares Lucene infrastructure | Medium |
| `screen-configs_LIB` | Likely provides rules configuration | Medium |

---

## Multi-Tenant Architecture Role

`eccm_LIB` is the **core enabling technology** for Onbe's multi-tenant cardholder portal model. Without it:
- All Gen-1 portals would lose affiliate-specific branding
- Card images, program logos, and client-specific CSS would not render
- Navigation links and included page fragments would break

The rules engine in `eccm_LIB` is the original implementation of what modern platforms achieve with:
- Feature flags (LaunchDarkly, Unleash)
- Content delivery networks with program-specific asset paths
- BFF (Backend For Frontend) patterns with per-tenant configuration

---

## Migration Complexity Assessment

### Complexity: VERY HIGH

The `eccm_LIB` migration is likely the **highest-risk** migration in the Onbe East Gen-1 modernization because:

1. **Every Gen-1 web application uses `<eccm:*>` tags**: Removing eccm_LIB requires replacing every tag usage across all consuming WARs simultaneously. This is a multi-year, multi-team effort.

2. **Business rules are encoded in Spring XML configuration** loaded at WAR startup: The `SimpleRuleConfig` and rule initialization are injected via XML — migrating to a modern feature-flag or content management system requires recreating all existing rules data.

3. **Lucene 2.0.0 compatibility**: No path from Lucene 2.x to Lucene 9.x — the API is completely different. A complete rewrite of all index management code is required.

4. **Apache Struts 1.x dependency**: The `xstruts.tld` tags depend on Struts 1.2.8. These tags cannot coexist with modern frameworks (Spring MVC, Angular, React) without a complete replacement strategy.

5. **Zero test coverage** for business-critical rendering logic.

A recommended migration approach:
1. **Near-term (0–12 months)**: Extract rules configuration to a database table; build a read-only REST API that serves the same configuration data
2. **Medium-term (1–3 years)**: Replace `<eccm:*>` tags with Thymeleaf fragments or Angular/React components, program by program
3. **Long-term**: Retire eccm_LIB entirely as the last Gen-1 web application is migrated

---

## Security Impact Assessment

The combination of **Struts 1.2.8** (critical CVE) + **Commons HttpClient 3.0.1** (no TLS 1.2) + **Spring 2.0.2** (EOL) in a library that is a transitive dependency of every Gen-1 cardholder portal represents **the highest aggregate CVE surface in the Onbe East Gen-1 stack**. Any cardholder portal that includes `eccm_LIB` inherits all these vulnerabilities.

PCI DSS Requirement 6.3.3 mandates that all software components are protected from known vulnerabilities by installing applicable security patches. The Struts 1.x CVEs include remote code execution vulnerabilities that, if exploited, could grant an attacker full access to the cardholder portal server — a catastrophic outcome for a PCI DSS Level 1 service provider.
