# Solution Architect Report — i18n-utils_LIB

## 1. Complete Class and Method Inventory

### Package: `com.ecount.utils.i18n`

**Class: `I18NUtils`** (`src/main/java/com/ecount/utils/i18n/I18NUtils.java`)

Static utility class. No constructor (all methods static). All methods `public static`.

| Method | Signature | Description |
|---|---|---|
| `formatDate` | `formatDate(Date date, Locale locale, TimeZone zone) → String` | Formats date as `dd-MMM-yyyy` in given locale and timezone |
| `formatTime` | `formatTime(Date date, TimeZone zone) → String` | Formats time as `HH:mm:ss (GMT±hh:mm)` |
| `formatDateTime` | `formatDateTime(Date date, Locale locale, TimeZone zone, String format) → String` | Formats date+time with optional custom format pattern |
| `formatDateTime` | `formatDateTime(Date date, Locale locale, TimeZone zone) → String` | Formats date+time with default `dd-MMM-yyyy HH:mm:ss (GMT±hh:mm)` |
| `formatNumber` | `formatNumber(int number, Locale locale) → String` | Formats integer with locale thousand/decimal separators |
| `formatNumber` | `formatNumber(float number, Locale locale) → String` | Formats float with locale separators |
| `formatNumber` | `formatNumber(double number, Locale locale) → String` | Formats double with locale separators |
| `formatSignedNumber` | `formatSignedNumber(int number, Locale locale) → String` | Formats integer with explicit +/- prefix |
| `formatSignedNumber` | `formatSignedNumber(float number, Locale locale) → String` | Formats float with explicit +/- prefix |
| `formatSignedNumber` | `formatSignedNumber(double number, Locale locale) → String` | Formats double with explicit +/- prefix |
| `formatCurrency` | `formatCurrency(int number, Locale locale) → String` | Formats integer as locale currency |
| `formatCurrency` | `formatCurrency(float number, Locale locale) → String` | Formats float as locale currency |
| `formatCurrency` | `formatCurrency(double number, Locale locale) → String` | Formats double as locale currency (has special branch for locales where symbol = code) |
| `formatSignedCurrency` | `formatSignedCurrency(float number, Locale locale) → String` | Formats float as signed locale currency |
| `formatSignedCurrency` | `formatSignedCurrency(double number, Locale locale) → String` | Formats double as signed locale currency |
| `formatSingedCurrency` | `formatSingedCurrency(int number, Locale locale) → String` | **TYPO**: misspelled method name; formats int as signed locale currency |
| `formatCurrencyFromPennies` | `formatCurrencyFromPennies(int number, Locale locale) → String` | Formats integer pennies (divides by 100) as locale currency |
| `formatSignedCurrencyFromPennies` | `formatSignedCurrencyFromPennies(int number, Locale locale) → String` | Formats integer pennies as signed locale currency |
| `getTimeZoneFromBrowserOffset` | `getTimeZoneFromBrowserOffset(String browserOffset) → TimeZone` | Converts JavaScript `Date.getTimezoneOffset()` minutes to Java `TimeZone` |
| `getCurrencySymbol` | `getCurrencySymbol(Locale locale) → String` | Returns locale currency symbol (e.g., `$`) |
| `getCurrencyHeading` | `getCurrencyHeading(Locale locale) → String` | Returns currency heading (e.g., `(USD $)&nbsp;&nbsp;`) |
| `getDateFormatter` | `getDateFormatter() → DateFormat` | Returns `SimpleDateFormat` for `dd-MMM-yyyy` |
| `getDateTimeFormatter` | `getDateTimeFormatter() → DateFormat` | Returns `SimpleDateFormat` for `dd-MMM-yyyy HH:mm:ss (GMT±hh:mm)` |
| `getTimeFormatter` | `getTimeFormatter() → DateFormat` | Returns `SimpleDateFormat` for `HH:mm:ss (GMT±hh:mm)` |
| `getCurrencyFormatter` | `getCurrencyFormatter() → NumberFormat` | Returns `DecimalFormat` for currency pattern |
| `getNumberFormatter` | `getNumberFormatter() → NumberFormat` | Returns `DecimalFormat` for number pattern |
| `fixSymbol` (private) | `fixSymbol(String curSymbol) → String` | Replaces broken euro character with HTML entity `&#8364;` |

**Format constants** (all `private static final String`):

| Constant | Value |
|---|---|
| `DATE_FMT` | `dd-MMM-yyyy` |
| `TIME_FMT` | `HH:mm:ss ('GMT'Z)` |
| `DATE_TIME_FMT` | `dd-MMM-yyyy HH:mm:ss ('GMT'Z)` |
| `NUMBER_FMT` | `###,###,###,###,##0.00` |
| `TIME_ZONE_FMT` | `GMT%+02d:%02d` |
| `CURRENCY_FMT` | `¤¤ ¤###,###,###,###,##0.00` |
| `SIGNED_NUMBER_FMT` | `+###,###,###,###,##0.00;-###,###,###,###,##0.00` |
| `SIGNED_CURRENCY_NUMBER_FMT` | `+¤¤ ¤###,...;-¤¤ ¤###,...` |

---

### Package: `com.ecount.utils.i18n.tags`

**Abstract Class: `CommonTagSupport`** (`tags/CommonTagSupport.java`)

Extends `javax.servlet.jsp.tagext.SimpleTagSupport`. Abstract base for all tags.

| Member | Type | Description |
|---|---|---|
| `zone` | `protected TimeZone` | Timezone field |
| `locale` | `protected Locale` | Locale field |
| `date` | `protected Date` | Date field |
| `value` | `protected Number` | Numeric value field |
| `signed` | `protected boolean` | Whether to display explicit +/- sign |
| `setLocale(String)` | method | Parses `"en_US"` style string to `Locale` |
| `setZone(TimeZone)` | method | Sets timezone directly |
| `setBrowserOffset(String)` | method | Sets timezone from browser offset string |
| `setDate(Date)` | method | Sets date value |
| `setValue(double)` | method | Sets value as `new Double(value)` (deprecated constructor) |
| `setValue(int)` | method | Sets value as `new Integer(value)` (deprecated constructor) |
| `setValue(float)` | method | Sets value as `new Float(value)` (deprecated constructor) |
| `setValue(long)` | method | Sets value as `new Long(value)` (deprecated constructor) |
| `setValue(String)` | method | Parses string to double |
| `setPennies(int)` | method | Sets value as pennies/100 |
| `setPennies(String)` | method | Parses and sets value as pennies/100 |
| `setSigned(String)` | method | Parses `"true"/"false"` string to boolean |

---

**Class: `FormatCurrency`** (`tags/FormatCurrency.java`)

Extends `CommonTagSupport`. JSP tag for currency formatting.

| Method | Description |
|---|---|
| `doTag()` | Calls `I18NUtils.formatSignedCurrency()` if `signed=true`, else `formatCurrency()` |

---

**Class: `FormatNumber`** (`tags/FormatNumber.java`)

Extends `FormatCurrency`.

| Method | Description |
|---|---|
| `doTag()` | Calls `I18NUtils.formatSignedNumber()` if `signed=true`, else `formatNumber()` |

---

**Class: `CurrencyHeading`** (`tags/CurrencyHeading.java`)

Extends `CommonTagSupport`. Default constructor sets `locale = Locale.getDefault()`.

| Method | Description |
|---|---|
| `CurrencyHeading()` | Constructor — sets `locale = Locale.getDefault()` |
| `doTag()` | Calls `I18NUtils.getCurrencyHeading(locale)` |

---

**Class: `CurrencySymbol`** (`tags/CurrencySymbol.java`)

Extends `CurrencyHeading`.

| Method | Description |
|---|---|
| `doTag()` | Calls `I18NUtils.getCurrencySymbol(locale)` |

---

**Class: `DisplayDate`** (`tags/DisplayDate.java`)

Extends `CommonTagSupport`.

| Field | Type | Description |
|---|---|---|
| `format` | `String` | Optional custom date format string |

| Method | Description |
|---|---|
| `doTag()` | Calls `I18NUtils.formatDate(date, locale, zone)` |
| `setFormat(String)` | Sets custom format string |

---

**Class: `DisplayDateTime`** (`tags/DisplayDateTime.java`)

Extends `DisplayDate`.

| Method | Description |
|---|---|
| `doTag()` | Calls `I18NUtils.formatDateTime(date, locale, zone, format)` |

---

**Class: `DisplayTime`** (`tags/DisplayTime.java`)

Extends `DisplayDate`.

| Method | Description |
|---|---|
| `doTag()` | Calls `I18NUtils.formatTime(date, zone)` |

---

**Class: `CaptureTimeZone`** (`tags/CaptureTimeZone.java`)

Extends `javax.servlet.jsp.tagext.SimpleTagSupport` directly (not `CommonTagSupport`).

| Field | Type | Description |
|---|---|---|
| `timezoneOffset` | `String` | Browser timezone offset in minutes |

| Method | Description |
|---|---|
| `getTimezoneOffset()` | Returns `timezoneOffset` |
| `setTimezoneOffset(String)` | Sets `timezoneOffset` |
| `doTag()` | Renders `<input type="hidden" name="timeZone" value="..." />` |

---

### Test Class: `TestI18NUtils` (`src/test/java/com/ecount/utils/i18n/TestI18NUtils.java`)

Manual test driver (not a JUnit test class).

| Method | Description |
|---|---|
| `main(String[])` | Prints formatted output for 13 locales to stdout |
| `printLine(Locale, TimeZone, Date, double)` | Prints one row: date, time, datetime, currency, signed number |

---

## 2. Security Vulnerability Assessment

### VULN-001 — MEDIUM: Typo in Public API Method Name (`formatSingedCurrency`)

**Location**: `I18NUtils.java` line 383

```java
public static String formatSingedCurrency(int number, Locale locale) {
```

The method name is `formatSingedCurrency` (missing the `n` in "Signed"). This method is in the public API and may be called by consuming web applications. The implications are:

- **Discoverability**: Developers searching for `formatSignedCurrency` with an integer argument will not find this method via code completion or text search
- **API inconsistency**: The `int` overload has a different method name than the `float` and `double` overloads (`formatSignedCurrency`), making the API non-uniform
- **Deprecation risk**: Renaming the method is a breaking change for any consumer that calls `formatSingedCurrency(int, Locale)` by its current (wrong) name

**Remediation**: Add a correctly-named `formatSignedCurrency(int, Locale)` method that delegates to `formatSingedCurrency`, then deprecate the misspelled version. Priority: **MEDIUM** (API quality).

---

### VULN-002 — MEDIUM: Deprecated Boxed Type Constructors in `CommonTagSupport`

**Location**: `CommonTagSupport.java` lines 57, 69, 74, 79, 88, 95

```java
this.value = new Double(value);   // line 57 — deprecated since Java 9
this.value = new Integer(value);  // line 69 — deprecated since Java 9
this.value = new Float(value);    // line 74 — deprecated since Java 9
this.value = new Long(value);     // line 79 — deprecated since Java 9
this.value = new Double(pennies/100.0);  // line 88 — deprecated since Java 9
this.value = new Double(...);     // line 95 — deprecated since Java 9
```

**Risk**: `new Double()`, `new Integer()`, `new Float()`, and `new Long()` constructors are deprecated since Java 9 and may be removed in a future JDK release. Compilation warnings will be generated on modern JDKs. If the consuming application upgrades to a JDK that removes these constructors (unlikely in the near term but possible in Java 23+), the library will fail to compile.

**Remediation**: Replace with `Double.valueOf(value)`, `Integer.valueOf(value)`, `Float.valueOf(value)`, `Long.valueOf(value)`. Priority: **MEDIUM**.

---

### VULN-003 — MEDIUM: Euro Symbol Encoding Defect in `fixSymbol()`

**Location**: `I18NUtils.java` lines 496–503

```java
private static String fixSymbol(String curSymbol) {
    if (curSymbol != null) {
        curSymbol = curSymbol.replaceFirst("?", "&#8364;");
    }
    return curSymbol;
}
```

The replacement pattern is a garbled character (`?`) rather than the euro sign `€` due to the source file's encoding. The `replaceFirst` call uses the garbled character as a regex pattern. The behavior of this method depends entirely on whether the JVM's default charset at runtime can match the garbled byte sequence with `€` in the currency symbol string from `DecimalFormatSymbols`.

**Risk**: On a UTF-8 JVM, the garbled pattern will never match, the `replaceFirst` will be a no-op, and euro currency display may be incorrect for European locale users. This affects all euro-zone cardholders viewing balances on JSP pages using this library.

**Remediation**: Replace the garbled character literal with the explicit Unicode escape `€` (euro sign):
```java
curSymbol = curSymbol.replace("€", "&#8364;");
```
And fix the source file encoding to UTF-8. Priority: **MEDIUM** (cardholder-facing display defect for EUR programs).

---

### VULN-004 — HIGH: Java 1.5 Target (EOL October 2009)

**Location**: `pom.xml` lines 56–59

**Risk**: The library compiles targeting Java 1.5 bytecode. Java 1.5 reached end of life on October 30, 2009. Security vulnerabilities discovered since then in the Java 1.5 platform receive no patches. While the library itself does not use the Java SE security APIs directly, any consuming application running on a Java 5 JVM (if any remain) inherits all Java 5 security vulnerabilities.

More practically, the Java 1.5 source level:
- Restricts use of features introduced in Java 6+ (type inference, try-with-resources, etc.)
- Generates compilation warnings on Java 17+ for using deprecated constructs
- Blocks future adoption of Java 21 virtual threads, records, and sealed classes in this codebase

**Remediation**: Update `pom.xml` to `<source>11</source><target>11</target>` or `17`. Resolve any compilation warnings. Priority: **HIGH**.

---

### VULN-005 — HIGH: `javax.servlet.jsp` Namespace — Jakarta EE Incompatibility

**Location**: All tag class files — `import javax.servlet.jsp.tagext.SimpleTagSupport`

**Risk**: Jakarta EE 9 (2020) renamed all `javax.*` namespaces to `jakarta.*`. Any consuming web application that upgrades to:
- Tomcat 10+
- Spring Boot 3.x (which requires Jakarta EE 9+)
- WildFly 27+

will find that `i18n-utils_LIB` fails to compile or load because `javax.servlet.jsp.tagext.SimpleTagSupport` does not exist in Jakarta EE 9+ containers.

Given that `functionapptest` already uses Java 17 and Spring Boot 3.x patterns are Onbe's target architecture, this incompatibility is a near-term blocker for any consuming application that modernizes.

**Remediation**: Replace all `javax.servlet.jsp.*` imports with `jakarta.servlet.jsp.*`. Update `jsp-api` dependency to `jakarta.servlet.jsp:jakarta.servlet.jsp-api:3.1.0`. Priority: **HIGH**.

---

### VULN-006 — HIGH: Wirecard Nexus Distribution Target

**Location**: `pom.xml` lines 23–34

**Risk**: The `mvn deploy` target publishes to `d-na-stk01.nam.wirecard.sys:8080`. If this Nexus is offline (which is likely given the Wirecard insolvency in 2020), any attempt to run `mvn deploy` to publish a new version will fail. More critically, consuming applications that declare `d-na-stk01.nam.wirecard.sys` as a repository in their `pom.xml` or `settings.xml` will fail to resolve `com.ecount.utils:i18n-utils:2020.9.10` during build.

**Remediation**: Migrate artifact publishing to Azure Artifacts or GitHub Packages. Update all consuming applications' repository configurations. Priority: **HIGH** (supply chain risk).

---

## 3. Technical Debt Summary

| Debt Item | Severity | Effort |
|---|---|---|
| Java 1.5 target (EOL 2009) | HIGH | LOW — change 2 lines in pom.xml |
| `javax.servlet.jsp` (Jakarta EE incompatibility) | HIGH | LOW — find/replace imports |
| Wirecard Nexus distribution target | HIGH | MEDIUM — migrate to Azure Artifacts |
| Deprecated `new Double()`/`new Integer()` etc. | MEDIUM | LOW — mechanical replacement |
| Typo in `formatSingedCurrency` public method | MEDIUM | LOW — add deprecated alias |
| Euro symbol encoding defect in `fixSymbol()` | MEDIUM | LOW — fix regex pattern |
| No automated tests (JUnit 3.8.1, no assertions) | MEDIUM | MEDIUM — write JUnit 5 tests |
| No CI/CD build/deploy pipeline | MEDIUM | LOW — add GitHub Actions workflow |
| `com.citi.prepaid` parent POM dependency | LOW | MEDIUM — create Onbe parent POM |
| ISO-8859-1 TLD encoding | LOW | LOW — change to UTF-8 |

---

## 4. Remediation Priority Matrix

| Priority | Action | Owner |
|---|---|---|
| P1 — Sprint 1 | Migrate Nexus to Azure Artifacts / GitHub Packages | DevOps |
| P1 — Sprint 1 | Update Java source/target to 11 or 17 | Dev |
| P1 — Sprint 1 | Replace `javax.servlet.jsp` with `jakarta.servlet.jsp` | Dev |
| P2 — Sprint 2 | Fix `fixSymbol()` euro encoding defect (`€`) | Dev |
| P2 — Sprint 2 | Replace deprecated boxed constructors with `Double.valueOf()` etc. | Dev |
| P2 — Sprint 2 | Add correctly-named `formatSignedCurrency(int, Locale)` and deprecate typo | Dev |
| P2 — Sprint 2 | Add GitHub Actions build + test pipeline | DevOps |
| P3 — Q3 | Upgrade JUnit from 3.8.1 to 5; write real `@Test` assertion tests | Dev |
| P3 — Q3 | Define Onbe parent POM to replace `com.citi.prepaid:prepaid-parent` | Dev |
| P4 — Roadmap | Evaluate library deprecation as consuming apps migrate from JSP | Architecture |
