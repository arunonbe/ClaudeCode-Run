# eccm_LIB — Business Analyst Report

## Repository Overview

`eccm_LIB` is the **ECount Content Management (ECCM) library** — a Gen-1 Java JSP tag library providing:
1. A **CMS (Content Management System) service** for retrieving and searching content from a Lucene-indexed content store
2. A **rules engine** for content rendering decisions — determining which images, styles, includes, and links to display based on affiliate/program context
3. A **custom JSP tag library** (`eccm.tld` / `xstruts.tld`) used by eCount web applications to render program-specific UI elements
4. **URL rewriting** utilities for portal navigation

The artifact is `com.ecount.web.tags:eccm:1.1.1` (`pom.xml` line 13), inheriting from `com.citi.prepaid:module-parent:5`. The version history comments in `RuleManager.java` show this was originally created in October 2004 (`User: Swilson Date: 10/21/04`) — making this one of the **oldest components** in the Onbe East platform.

---

## Business Purpose

### 1. Content-Driven UI Rendering
The ECCM library enables eCount web portals to display **program-specific content** without code deployments. Each affiliate (client program) can have different:
- Images (card artwork, logos)
- Styles (CSS)
- Included page fragments
- URL routing rules
- Navigation links

This is the Gen-1 approach to what modern systems call feature flags + content management.

### 2. Apache Lucene Search Index
`CMSService.java` (line 85, `fire()` method) uses an **Apache Lucene 2.0.0 search index** to query content documents. The CMS service:
- Reads a Lucene index from disk or RAM
- Searches for content matching a query string
- Returns `XDoc` objects (XML document wrappers) with field maps

This enables the portal to search for program-specific content by keyword or property, supporting dynamic content assembly.

### 3. Rules Engine for Affiliate-Specific Rendering
The `model/` package implements a **rules engine** with:
- `IRuleManager` — manages rules configuration lifecycle
- `IRuleConfig` / `SimpleRuleConfig` — stores rule definitions keyed by name
- `IRule` — interface for rule evaluation (`evaluate(PageContext, ruleName, property, value)`)
- Concrete rule implementations: `ParameterIndexedImageRule`, `ParameterIndexedIncludeRule`, `ParameterIndexedStyleRule`

The rules determine, for a given portal page context and affiliate, which content elements to render. This is the mechanism by which a single portal codebase serves hundreds of client-branded programs.

### 4. JSP Tag Library
The `eccm.tld` tag library (10,645 bytes) and `xstruts.tld` (22,112 bytes) provide custom JSP tags:
- `<eccm:property>` (`PropertyTag.java` — 11,214 bytes, largest tag class) — renders program-specific text/HTML properties
- `<eccm:image>` (`ImageTag.java`) — renders affiliate-specific card/program images
- `<eccm:link>` (`LinkTag.java`) — renders affiliate-specific navigation links with URL rewriting
- `<eccm:include>` (`IncludeTag.java`) — includes affiliate-specific page fragments
- `<eccm:forEach>` (`ForEachTag.java`) — iterates over CMS content results
- `<eccm:docBase>` (`DocBaseTag.java`) — sets the CMS document base URL
- `<eccm:urlRewrite>` (`UrlRewriteTag.java`) — applies URL rewriting rules
- `<eccm:select>` (`SelectTag.java`) — renders affiliate-specific dropdown/select elements
- `<eccm:fmtMessage>` (`FmtMessageTag.java`) — formats i18n messages

The `xstruts.tld` includes additional Struts-based tags:
- `<xstruts:securePassword>` (`SecurePasswordTag.java`) — renders password fields with security attributes
- `<xstruts:secureText>` (`SecureTextTag.java`) — renders text fields with security attributes

---

## Key Business Capabilities

### Multi-Tenant Portal Rendering
The rules engine and CMS service together enable a single portal web application to serve hundreds of distinct prepaid card programs with:
- Different card images and branding
- Different terms and conditions text
- Different navigation flows
- Different field labels and messages

### Content Search and Retrieval
Program managers and content administrators can update the Lucene index to modify portal content without application code deployments — a significant business agility benefit that reduces time-to-market for program configuration changes.

### URL Security and Navigation
`UrlRewrite.java` (7,329 bytes) and `UrlRewriteTag.java` handle URL rewriting for portal navigation, including potential security-related URL transformations (masking internal path structures).

---

## Business Rules Observed

1. **Affiliate-Sorted Content** — `DefaultAffiliateSorter.java` sorts content results by affiliate (program) priority, ensuring program-specific content takes precedence over default content.
2. **Parameter-Indexed Rules** — The `ParameterIndexed*Rule` classes use a parameter index to select which content to return when multiple options exist for a single affiliate/rule name combination.
3. **Rule Not Found Handling** — `RuleNotFoundException.java` and `RuleConfigException.java` indicate the system has graceful degradation when a rule is not configured for a specific program.
4. **CMS Node Configuration** — `CMSService.java` line 38: `CMS_SERVICE_URL_PROPERTY = "ecount.node"` allows the CMS service URL to be overridden by a system property, supporting multi-environment deployment.
5. **Lucene Index Refresh** — `LuceneIndex.java` (8,538 bytes) and `IndexManager.java` manage the lifecycle of the Lucene index including periodic refresh intervals (configured in `CMSApplicationContext.xml` lines 25–29: `searcherTimeout=10`, `writerTimeout=30`).

---

## Regulatory Relevance

### PCI DSS
The ECCM library renders portal pages for cardholders — it is part of the cardholder-facing web application surface. Under PCI DSS Requirement 6.3 (secure development) and Requirement 11.3 (web application testing), the JSP tag output must be reviewed for:
- Cross-Site Scripting (XSS) risk from unescaped CMS content rendered by `PropertyTag`
- URL injection risk via `UrlRewrite.java`

### GDPR / CCPA
The CMS content does not appear to store PII. However, if `PropertyTag` renders personalized content that includes member names or account information, the rendered output would constitute PII processing.

### Accessibility / ADA
The `eccm.tld` tag library generates HTML for cardholder portals. Inaccessible HTML from these tags could create ADA Title III compliance exposure for client programs.
