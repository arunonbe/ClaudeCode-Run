# jobserviceintegration_LIB — Enterprise Architect View

## Platform Generation

**Gen-1** — Legacy eCount platform integration library.

Evidence:
- Maven artifact `com.ecount.service:jobserviceintegration:1.0.1-SNAPSHOT`, parent `com.ecount.service:service-parent:3`
- Java 1.6 compiler target
- Maven compiler plugin 2.0.2 (released ~2008)
- File-based integration model (flat-file batch files on filesystem)
- VBScript / Windows Script Host files alongside Java source
- Binary JARs committed to source control
- `SNAPSHOT` version indicates no stable release has been cut
- No Spring Boot, no cloud-native patterns

## Business Domain

**Inbound Client File Integration** — Converts external corporate client data files into the eCount standard batch protocol for prepaid card enrolment and funding. Covers:
- Automotive industry (Chrysler, Toyota, Subaru)
- Telecom industry (Nextel, Qwest)
- Legacy/specialty programmes (LegacyForLife, JWT)

This domain sits between the **client's disbursement data extraction** and the **eCount job service processing engine**.

## Role in the Platform

`jobserviceintegration_LIB` is the **data translation layer** in the Gen-1 batch pipeline:

```
[Client sends ZIP/flat file to SFTP drop]
        |
        v
[jobserviceintegration_LIB] — converts to eCount batch format
        |
        v
[job_LIB / jobservice_SVC] — enrols recipients, funds accounts
        |
        v
[eCount Core] — issues prepaid cards
```

It has no runtime service-to-service dependency — it is invoked by a batch host process (likely a Windows server or scheduled task runner).

## Dependencies

### Upstream (libraries this library depends on)
| Dependency | Version | Status |
|---|---|---|
| `com.ecount.service:service-parent:3` | 3 | Legacy internal parent POM |
| `commons-logging:commons-logging` | 1.1.1 | Released 2007; obsolete |
| Binary JARs in `alg/common/` | Unknown | Unmanaged; no Maven coordinates |
| Binary JARs in `BulkCardGen/` | Various (ca. 2007–2013) | Unmanaged; some versions visible in filenames |

### Downstream (consumers of this library)
- Batch host processes running on Windows servers (scheduled tasks / Windows Task Scheduler / legacy job scheduler)
- The `job_LIB` / `jobservice_SVC` consumes the output files, not the library directly

## Integration Patterns

1. **File-based ETL**: Client file → in-memory transformation → eCount batch file. Classic Extract-Transform-Load over a filesystem.
2. **Polling / scheduled execution**: The conversion tool is invoked as a command-line application (`public static void main(String[] args)`) by a scheduler.
3. **Windows Script automation**: `.vbs` and `.wsf` scripts orchestrate the Java conversion tool invocations on Windows.
4. **No real-time integration**: Entirely batch/scheduled, not event-driven.

## Strategic Status

| Dimension | Assessment |
|---|---|
| Lifecycle | **Retire** — Each client integration here represents a Gen-1 engagement that should be replaced by the NexPay Gen-3 platform's disbursement APIs |
| Technical debt | Very high — Java 1.6, Windows-only scripts, binary JARs, no tests, no observability |
| Replacement target | NexPay multi-rail disbursement API (REST/event-driven) for each client programme |
| Risk level | Medium operational, High security — binary JARs in source, ancient Java, Windows-only automation |

## Migration Blockers

1. **Client-specific file format knowledge**: Each module encodes proprietary parsing rules for a specific client's file format. Migration requires either re-implementing these parsers or eliminating the file-based interface entirely.
2. **Windows-only automation scripts**: VBScript / WSF scripts are not portable; full re-implementation required for Linux/container environments.
3. **Binary JARs**: `ALGRequestFile.jar`, `CustomFilesCommon-1.0.0.jar`, and the BulkCardGen JARs have no source or Maven coordinates — their functionality must be reverse-engineered.
4. **Snapshot version**: `1.0.1-SNAPSHOT` has never been released to a stable version, suggesting this library is perpetually in development state.
5. **Promotion config external file**: `PROMO_CONFIG_FILE` is a filesystem path; migration to cloud requires externalizing this configuration to Azure App Configuration or a database table.
