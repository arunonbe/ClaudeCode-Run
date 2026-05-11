# custom-files_LIB — Solution Architect View

## Architecture Overview
Pure Java 21 utility library. No framework dependencies. Three logical layers:

```
Annotation Layer
    @FlatField, @PUID, @PPD, @AccountAddenda, @Passthrough, @EcountID
    @RequestBlockPad, @RequestEcountID, @RequestPassThrough
    AnnoationHelper.java (reflection helper)

Bean Layer (com.ecount.etl.ecount.request.file.beans)
    EcountFileHeader, EcountBatchHeader, EcountRequest, EcountCreateAccountRequest,
    EcountCreateAccountReply, EcountCreateAccountExtended, EcountCreateAccountExtendedReply,
    EcountAddFundsRequest, EcountAddFundsReply, EcountStopPaymentRequest,
    EcountAccountAddenda, EcountPaymentDetail, EcountBatchFooter, EcountFileFooter

Format / Serialisation Layer
    EcountRequestFile.java   -- static factory / parser for all record types
    BufferedFileWriter.java  -- file I/O utility

Parser Layer (com.ecount.etl.ecount.request.file.parser)
    EcountReplyFileListener.java
    EcountReplyParser.java
```

## Format Constants (EcountRequestFile.java lines 30–39)
```java
HEADER          = "%-2s%-4s%-50s%-32s%-8s%s%-303s\n"
FOOTER          = "%-2s%-398s\n"
BATCH_HEADER    = "%-2s%-4s%-64s%-32s%-8s%-290s\n"
BATCH_FOOTER    = "%-2s%-398s\n"
REQUEST         = "%-2s%-16s%-50s%-32s%-300s\n"
ACCOUNT_ADDENDA = "%-2s%-10s%-40s%-348s\n"
ADD_FUNDS       = "%-2s%-32s%-10s%s%-10s%-40s%s%-304s\n"
CREATE_ACCOUNT  = "%-2s%-32s%-25s%-25s%-25s%-25s%-50s%-26s%-26s%-18s%-2s%-10s%-2s%-16s%-16s%-16s%-10s%-2s%-72s\n"
PAYMENT_DETAIL  = "%-2s%-10s%-40s%-348s\n"
CREATE_ACCOUNT_EXTENDED = "%-2s%-50s%-50s%-50s%-50s%-25s%-173s\n"
```

## Security Observations
- `EcountCreateAccountReply.cvCode` (populated at `EcountRequestFile.java` line 225): CVV/CVC value present in the Java bean. This constitutes SAD under PCI DSS Requirement 3.3. Consumers of this library **must not** persist this value or include it in logs.
- `EcountCreateAccountReply.cardNumber` (line 222): full PAN returned in the reply bean. Although the eCount platform may return masked or tokenised values, the library does not enforce masking — it stores whatever offset `284..300` contains.
- Reflection via `field.setAccessible(true)` (`EcountRequestFile.getField()` line 456–462): bypasses Java module access protection. On Java 21 with `--illegal-access=deny` (default), this requires `--add-opens` for the relevant packages.

## Technical Debt
| Item | File | Line | Description |
|---|---|---|---|
| Typo in class name | `AnnoationHelper.java` | 1 | `AnnoationHelper` should be `AnnotationHelper` |
| Raw types | `EcountRequestFile.java` | Multiple | `Map`, `List` without generics (pre-Java 5 style) |
| `setAccessible(true)` | `EcountRequestFile.java` | 457 | Requires `--add-opens` on Java 21 |
| Silent truncation | `EcountRequestFile.rightTrim()` | 489 | No warning/exception when value exceeds field width |
| No null-safety on `getField()` return | `EcountRequestFile.java` | 118–133 | NPE risk if annotated field is null |
| No unit tests | — | — | Zero test coverage |
| Assembly descriptor missing | `pom.xml` line 42 | — | `src/assemble/zipfile.xml` referenced but absent |
| `cvCode` in public bean | `EcountCreateAccountReply` | — | SAD value accessible to any code holding the bean |

## Gen-3 Migration Path
- Replace file-based eCount integration with REST API calls (ECountCore REST already in use in `customer-service-rest-api`).
- Once file channel is retired, this library becomes obsolete.
- If file channel must be retained short-term: add field-level masking for PAN/CVV in reply beans, add validation logging for truncation events, add unit tests for all format constants using known-width test strings.
