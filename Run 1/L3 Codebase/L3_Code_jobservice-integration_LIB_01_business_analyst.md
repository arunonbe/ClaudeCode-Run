# jobservice-integration_LIB — Business Analyst View

## Business Purpose

`jobservice-integration_LIB` (hyphenated name) is a Gen-1 multi-module Java library that is a **near-identical sibling** of `jobserviceintegration_LIB`. It carries the same Maven artifact ID (`com.ecount.service:jobserviceintegration:1.0.1-SNAPSHOT`), same Java 1.6 target, and the same set of client integration modules. The primary structural difference is that the `LegacyForLife` sub-module is referenced as `legacyForLife` (lowercase `l`) in the root POM module list, whereas `jobserviceintegration_LIB` uses `LegacyForLife` (uppercase `L`).

This repository appears to be a **fork or branched copy** of `jobserviceintegration_LIB`, likely reflecting a point-in-time divergence of the integration library during a refactoring or client-onboarding effort. The two repos have the same functional scope.

## Capabilities

Identical to `jobserviceintegration_LIB`:

- **File format conversion**: Reads client-supplied fixed-width or delimited flat files and produces ecount-standard batch files.
- **Validation**: Validates incoming files against configurable field templates.
- **Zip archive handling**: Processes multi-file ZIP archives.
- **Promotion cross-referencing**: Maps client stock codes to ecount promotion IDs.
- **Reply file parsing**: Parses ecount reply files after job processing.
- **Record generation**: Supports all major ecount batch record types.

## Client Modules

| Module | Client / Programme |
|---|---|
| `Common` | Shared utilities |
| `chrysler` | Chrysler (automotive rebate) |
| `jwt` | JWT programme |
| `legacyForLife` | LegacyForLife programme (module name lowercase vs. sibling repo) |
| `nextel` | Nextel (telecom) |
| `qwest` | Qwest (telecom) |
| `subaru` | Subaru (automotive) |
| `toyota` | Toyota (automotive) |

## Entities

Same entity model as `jobserviceintegration_LIB`: `BatchFile`, `BatchFileConstants`, `EcountPromotion`, `PromotionXref`, `FixedWidthRecordParser`, `DelimitedRecordParser`, `ReplyFileParser`, `FileValidator`, `TaxProfile`, `ValidationException`.

## Business Rules

Identical to `jobserviceintegration_LIB` — same fixed-width batch file protocol, same field-width rules, same promotion cross-reference logic, same error-handling conventions.

## Flows

Same batch file conversion flow as `jobserviceintegration_LIB`.

## Relationship to jobserviceintegration_LIB

| Dimension | jobserviceintegration_LIB | jobservice-integration_LIB |
|---|---|---|
| Maven artifact ID | `jobserviceintegration` | `jobserviceintegration` (same) |
| Version | `1.0.1-SNAPSHOT` | `1.0.1-SNAPSHOT` (same) |
| Module: LegacyForLife | `LegacyForLife` | `legacyForLife` |
| Git default branch | `master` | `master` |
| Dependabot | Present | Present |
| CodeQL | Present | Present |
| Maven publish workflow | None | None |
| Source content | Identical/near-identical | Identical/near-identical |

**Recommendation**: These two repositories should be consolidated. Having two near-identical repositories with the same artifact coordinates creates version confusion, duplicated maintenance burden, and potential divergence risk.

## Compliance Relevance

Same as `jobserviceintegration_LIB`: processes recipient PII in plain-text flat files; Log4j 1.x binary JAR risk; no encryption; no audit trail.

## Risks

- **Duplicate repository**: Two repos producing the same Maven artifact ID creates a build-system conflict risk.
- All other risks are identical to `jobserviceintegration_LIB`.
