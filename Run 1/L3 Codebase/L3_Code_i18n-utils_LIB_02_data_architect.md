# Data Architect Report — i18n-utils_LIB

## 1. Module Structure

`i18n-utils_LIB` is a single-module Maven project producing one JAR artifact (`i18n.jar`). The JAR contains:

| Package | Contents |
|---|---|
| `com.ecount.utils.i18n` | Core utility class `I18NUtils.java` |
| `com.ecount.utils.i18n.tags` | JSP tag handler classes (8 classes) |
| `META-INF/tld/` (packaged) | `i18n-taglib.tld` — JSP tag library descriptor |

No database, file system, or external service dependencies exist. The library is a pure in-memory transformation utility.

---

## 2. Data Models

The library has no persistent data entities. It is a stateless transformation library — inputs are Java primitive/object types and outputs are formatted strings for display. The relevant data types are:

### 2.1 Input Types

| Input | Java Type | Description |
|---|---|---|
| Monetary amount (dollars) | `int`, `float`, `double` | Amount in major currency unit |
| Monetary amount (pennies) | `int` | Amount in smallest currency unit (cents) |
| Numeric value | `int`, `float`, `double`, `long` | Generic number |
| Date/time | `java.util.Date` | Point in time for formatting |
| Locale | `java.util.Locale` | Target locale (determines currency symbol, separators) |
| Timezone | `java.util.TimeZone` | Target timezone for date/time display |
| Browser offset | `java.lang.String` | JavaScript `Date.getTimezoneOffset()` value (minutes) |

### 2.2 Format Constants (from `I18NUtils.java` lines 13–28)

| Constant | Value | Purpose |
|---|---|---|
| `DATE_FMT` | `dd-MMM-yyyy` | Date display format |
| `TIME_FMT` | `HH:mm:ss ('GMT'Z)` | Time display with timezone offset |
| `DATE_TIME_FMT` | `dd-MMM-yyyy HH:mm:ss ('GMT'Z)` | Combined date/time |
| `NUMBER_FMT` | `###,###,###,###,##0.00` | Numeric formatting with 2 decimals |
| `TIME_ZONE_FMT` | `GMT%+02d:%02d` | Timezone label format |
| `CURRENCY_FMT` | `¤¤ ¤###,###,###,###,##0.00` | Currency with symbol and code |
| `SIGNED_NUMBER_FMT` | `+###,...;-###,...` | Signed numeric (explicit +/-) |
| `SIGNED_CURRENCY_NUMBER_FMT` | `+¤¤ ¤###,...;-¤¤ ¤###,...` | Signed currency (explicit +/-) |

The currency format string uses Unicode `¤` (generic currency sign) twice followed by a space and then a single `¤` before the number. The `DecimalFormat` class interprets `¤¤` as the international currency code (e.g., `USD`) and single `¤` as the currency symbol (e.g., `$`), producing output like `USD $1,234.56`.

---

## 3. Tag Attribute Schema

### 3.1 `CommonTagSupport` Fields (`CommonTagSupport.java` lines 12–17)

All tag handler classes inherit from `CommonTagSupport`, which carries these shared attributes:

| Field | Type | Setter Method |
|---|---|---|
| `zone` | `java.util.TimeZone` | `setZone(TimeZone)` |
| `locale` | `java.util.Locale` | `setLocale(String)` — parses `"en_US"` style strings |
| `date` | `java.util.Date` | `setDate(Date)` |
| `value` | `java.lang.Number` | `setValue(double/int/float/long/String)` |
| `signed` | `boolean` | `setSigned(String)` — parsed from `"true"/"false"` string |

`setBrowserOffset(String)` (line 45) is also available on `CommonTagSupport`, delegating to `I18NUtils.getTimeZoneFromBrowserOffset()`.

### 3.2 `CaptureTimeZone` Fields (`CaptureTimeZone.java` line 9)

| Field | Type | Description |
|---|---|---|
| `timezoneOffset` | `String` | Browser-reported timezone offset in minutes (from JavaScript `Date.getTimezoneOffset()`) |

---

## 4. TLD Tag Attribute Matrix

From `i18n-taglib.tld`:

| Tag | Attribute | Required | Type |
|---|---|---|---|
| `captureTimeZone` | `timezoneOffset` | YES | String |
| `formatCurrency` | `locale` | no | String |
| `formatCurrency` | `value` | no | Number/String |
| `formatCurrency` | `pennies` | no | int/String |
| `formatCurrency` | `signed` | no | boolean/String |
| `currencyHeading` | `locale` | no | String |
| `currencySymbol` | `locale` | no | String |
| `formatNumber` | `locale` | no | String |
| `formatNumber` | `value` | no | Number/String |
| `formatNumber` | `pennies` | no | int/String |
| `formatNumber` | `signed` | no | boolean/String |
| `formatTime` | `zone` | no | TimeZone |
| `formatTime` | `browserOffset` | no | String |
| `formatTime` | `date` | no | Date |
| `formatDate` | `zone` | no | TimeZone |
| `formatDate` | `browserOffset` | no | String |
| `formatDate` | `locale` | no | String |
| `formatDate` | `date` | **YES** | Date |
| `formatDateTime` | `zone` | no | TimeZone |
| `formatDateTime` | `browserOffset` | no | String |
| `formatDateTime` | `locale` | no | String |
| `formatDateTime` | `date` | no | Date |
| `formatDateTime` | `format` | no | String |

---

## 5. Sensitive Data Assessment

### 5.1 Monetary Amounts

The library formats financial amounts that represent cardholder balances and transaction values. In JSP pages, these values are passed as tag attribute values at render time. The formatted output is HTML/text displayed to the user.

**Risk**: If the formatted output is logged by a web server access log or application log at DEBUG level, cardholder balance and transaction amount data could appear in logs. This data is not PAN/SAD data but may constitute GLBA/CCPA-protected financial information.

**Recommendation**: Ensure web application logs are configured to not log request parameters that contain balance or amount values from pages using this tag library.

### 5.2 Timezone Offset as Personal Data

The `captureTimeZone` tag renders a hidden form field with the browser's timezone offset. When submitted and stored:
- A timezone offset combined with other identifiers can constitute personal data under GDPR Article 4
- CCPA Section 1798.140(o) may encompass timezone data as part of a personal profile

This is a low-severity risk but should be considered when implementing DSAR (Data Subject Access Request) processes — timezone offset data stored in user sessions or databases should be included in DSAR responses.

### 5.3 No Network Data Transmission

The library performs no I/O operations (no database queries, no HTTP calls, no file reads/writes). All processing is in-memory. There are no data-in-transit PCI DSS concerns for this library itself.

---

## 6. Data Flow

```
[JSP Page in web application]
    |
    | <%@ taglib prefix="i18n" uri="http://ecount.com/tags/i18n-taglib" %>
    | <i18n:formatCurrency value="${balance}" locale="${userLocale}" />
    v
[Tag Handler (FormatCurrency.doTag())]
    |
    | calls I18NUtils.formatCurrency(value, locale)
    |   or I18NUtils.formatSignedCurrency(value, locale)
    v
[I18NUtils static formatting methods]
    |
    | DecimalFormat + DecimalFormatSymbols(locale)
    | fixSymbol() for euro character correction
    v
[Formatted String output → rendered to HTTP response]
```

No data persists beyond the HTTP request/response cycle.

---

## 7. Known Data Quality Issues

### 7.1 Euro Symbol Encoding Bug

`fixSymbol()` (lines 496–503 of `I18NUtils.java`) replaces a broken euro character (rendered as `?` in the source code due to encoding issues) with the HTML entity `&#8364;`. This is a workaround for a character encoding mismatch between the server's file encoding and the euro symbol codepoint. The root fix would be to ensure the source file is saved as UTF-8 and the euro symbol `€` (`€`) is used directly.

### 7.2 Currency Format Asymmetry

The `formatCurrency(double, Locale)` method (lines 304–322) has a special branch that detects when the currency symbol equals the currency code (which happens for locales where Java cannot resolve a distinct symbol) and removes the redundant prefix from the formatted output. The `formatCurrency(int, Locale)` and `formatCurrency(float, Locale)` methods (lines 362–367, 260–266) do not have this branch. This creates inconsistent output formatting between integer and double overloads for the same locale.
