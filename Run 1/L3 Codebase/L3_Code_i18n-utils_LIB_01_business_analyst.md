# Business Analyst Report — i18n-utils_LIB

## 1. Executive Summary

`i18n-utils_LIB` is a Java JSP tag library that provides locale-aware formatting utilities for dates, times, currency values, and numbers. It is a shared infrastructure library consumed by Onbe's legacy JSP-based web applications, enabling consistent multi-locale display of financial data (balances, transaction amounts, dates) across cardholder-facing portals and internal management interfaces.

The library exposes two integration surfaces:
1. A static Java utility class (`I18NUtils`) for programmatic use in Java code
2. A JSP custom tag library (TLD: `http://ecount.com/tags/i18n-taglib`) for declarative use in JSP pages

The library was originally developed under the Citi Prepaid (`com.citi.prepaid`) brand and subsequently maintained through the eCount and Wirecard eras into the Onbe period. Its version `2020.9.10` (a date-based version number) indicates the last release was in September 2020.

---

## 2. Business Capabilities

### 2.1 Multi-Locale Currency Formatting

The library's primary capability is locale-aware currency formatting for display on cardholder and program manager screens. The `I18NUtils.formatCurrency()` and `formatSignedCurrency()` methods accept a Java `Locale` and render amounts with the appropriate:
- Currency symbol (e.g., `$`, `£`, `€`, `¥`, `₩`)
- International currency code (e.g., `USD`, `GBP`, `EUR`, `JPY`)
- Thousand separator and decimal separator per locale convention

The library explicitly handles the euro symbol rendering issue via the `fixSymbol()` private method (line 496–503), which replaces a broken Unicode rendering with the HTML entity `&#8364;`. This suggests the library was tested and deployed on environments with encoding issues that required a workaround.

**Supported locale coverage** (evidenced by `TestI18NUtils.java`):
- `Locale.US` — USD
- `Locale.JAPAN` — JPY
- `Locale.CANADA` — CAD
- German locale (`DE/de`) — EUR
- `Locale.FRANCE` — EUR
- Italian locale (`IT/it`) — EUR
- Korean locale (`KR/ko`) — KRW
- `Locale.SIMPLIFIED_CHINESE` — CNY
- `Locale.TAIWAN` — TWD
- `Locale.TRADITIONAL_CHINESE` — TWD
- `Locale.UK` — GBP
- Russian locale (`RU/ru`) — RUB
- Spanish locale (`ES/es`) — EUR/MXN

This 13-locale coverage directly reflects Onbe's global prepaid card program footprint.

### 2.2 Pennies-Based Currency Formatting

The library includes specific methods for formatting amounts stored as integer pennies (smallest currency unit): `formatCurrencyFromPennies(int, Locale)` and `formatSignedCurrencyFromPennies(int, Locale)`. This is significant for a payments context — many financial systems (including prepaid card platforms) store monetary values as integers in the smallest denomination unit to avoid floating-point precision errors. The library acts as the display translation layer from storage pennies to human-readable formatted amounts.

### 2.3 Signed Number Display

The library supports signed display (with explicit `+` prefix for positive values) via the `formatSignedNumber()` and `formatSignedCurrency()` method families. This is used to display credit/debit transactions, balance changes, and refunds on cardholder statements. The JSP tags expose this via the `signed` attribute.

### 2.4 Timezone-Aware Date and Time Formatting

Financial transactions must display timestamps that are meaningful to the cardholder's local timezone. The library provides:
- `formatDate(Date, Locale, TimeZone)` — renders `dd-MMM-yyyy` (e.g., `15-Jan-2024`)
- `formatTime(Date, TimeZone)` — renders `HH:mm:ss (GMT±hh:mm)` (e.g., `14:30:00 (GMT-5:00)`)
- `formatDateTime(Date, Locale, TimeZone)` — combined date and time with timezone indicator
- `getTimeZoneFromBrowserOffset(String)` — converts JavaScript `Date.getTimezoneOffset()` to a Java `TimeZone`, bridging the browser-server timezone gap

The browser offset conversion is particularly important for cardholder portals where the server has no prior knowledge of the user's timezone and must infer it from the browser-reported offset.

### 2.5 JSP Tag Library

Eight custom JSP tags are registered in `i18n-taglib.tld` (URI: `http://ecount.com/tags/i18n-taglib`):

| Tag Name | Class | Function |
|---|---|---|
| `captureTimeZone` | `CaptureTimeZone` | Renders a hidden `<input>` field capturing browser timezone offset |
| `formatCurrency` | `FormatCurrency` | Formats a value as locale currency |
| `currencyHeading` | `CurrencyHeading` | Renders the currency heading e.g., `(USD $)` |
| `currencySymbol` | `CurrencySymbol` | Renders the currency symbol e.g., `$` |
| `formatNumber` | `FormatNumber` | Formats a value as a locale number |
| `formatTime` | `DisplayTime` | Renders time with timezone |
| `formatDate` | `DisplayDate` | Renders a date |
| `formatDateTime` | `DisplayDateTime` | Renders date and time with format override |

---

## 3. Regulatory Relevance

### 3.1 Reg E — Electronic Fund Transfer Disclosures

Regulation E (12 CFR Part 1005) requires that all EFT disclosures, error resolution notices, and periodic statements be presented in a clear and understandable format. For cardholder-facing portals showing prepaid card balances and transaction history, the formatting of amounts and dates must:
- Use the currency denomination appropriate to the cardholder's card program
- Display transaction timestamps in a timezone that corresponds to the cardholder's location or clearly indicate the reference timezone

This library is the mechanism by which Onbe satisfies those presentation requirements for JSP-based interfaces.

### 3.2 NACHA / ACH

ACH transaction records presented to cardholders (settlement dates, effective dates) must be formatted consistently. The date format `dd-MMM-yyyy` used by this library produces unambiguous month representations (e.g., `15-Jan-2024` vs. `01/15/24`) that avoid locale-specific month/day ordering confusion.

### 3.3 CCPA / GDPR

The library's timezone handling and locale detection must not inadvertently expose user location data. The `CaptureTimeZone` tag captures a browser timezone offset (minutes from UTC) and stores it in a hidden form field. This offset is passed to the server on form submission and used to format timestamps for the user. If this offset is persisted to a user profile or session, it constitutes a personal data element under GDPR Article 4 (data capable of identifying an individual's location).

---

## 4. Consumer Applications

As a `_LIB` repository, `i18n-utils_LIB` is consumed by all of Onbe's legacy JSP-based web applications. The `com.citi.prepaid` parent POM and `com.ecount.utils` package namespace indicate this library is shared across:

- Cardholder web portals (balance inquiry, transaction history)
- Program manager dashboards
- Internal operations tools displaying transaction data

Any application that includes this library as a Maven dependency and imports the TLD (`<%@ taglib prefix="i18n" uri="http://ecount.com/tags/i18n-taglib" %>`) is a consumer.
