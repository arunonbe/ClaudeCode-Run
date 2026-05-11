# Enterprise Architect View — jobservice_common_LIB

## Platform Role — The Shared Domain Model

`jobservice_common_LIB` is the **semantic foundation** of the Onbe batch processing platform. It defines the common language that allows disparate services to communicate about batch jobs without coupling to implementation details. In Domain-Driven Design terms, this is the **Shared Kernel** pattern — a subset of the domain model that multiple bounded contexts share.

## Architecture Significance

The existence of this library as a separate repository (extracted from `jobservice_SVC`) reflects an important architectural evolution: the recognition that the Job Service's domain model had become a platform-wide concern rather than a service-internal concern. This separation enables:

1. **Workflow Service independence**: The workflow engine can reference job states and interfaces without importing the entire `jobservice_SVC`
2. **Client integration libraries**: `jobserviceintegration_LIB` can validate job file content against the common schema without deploying job service code
3. **Independent versioning**: The common library can be versioned separately from the execution service

## Dependency Fan-Out

This library is likely depended upon by more repositories than any other single library in the batch processing subsystem:

```
jobservice_common_LIB (job-common:4.0.4)
    ├── jobservice_SVC (primary consumer)
    ├── job-scheduler_SVC (scheduling DTO types)
    ├── job-order-synchronization_LIB (uses 2.0.13 — version mismatch!)
    ├── autofile_SVC (autofile workflow steps)
    ├── workflow-service (workflow agent steps)
    ├── jobserviceintegration_LIB (file format processing)
    ├── jobservice-integration_LIB (file format processing)
    ├── clientzone_WAPP (job status display)
    └── banker_API (operations UI)
```

This fan-out means that **any breaking change to `job-common` requires a coordinated multi-repository release**.

## Version Fragmentation Risk

The most significant enterprise-level risk observed is the **version fragmentation** between consumers:
- `job-order-synchronization_LIB` uses `job-common:2.0.13`
- `jobservice_SVC` uses `job-common:4.0.4`

A version gap of 2.x (from 2.x to 4.x) suggests two breaking-change releases have occurred without updating all consumers. If the `JobStatus` enum or `OrderStatus` mapping in `job-order-synchronization_LIB` differs from the values recognized by `jobservice_SVC`, the two services could have silently mismatched status semantics — a financial data integrity risk.

**Recommended action**: Audit all consumers of `job-common` to identify their current version and assess compatibility. Establish a policy that all consumers must upgrade within a defined window of each major release.

## Java Version and Migration Path

The parent POM `prepaid-parent:6.0.13` (used by `jobservice_SVC`) targets Java 21. However, the common library itself must be compatible with the lowest Java version of any consumer. If `job-order-synchronization_LIB` still targets Java 8, `job-common` must maintain Java 8 source compatibility until that consumer is updated.

Key migration steps for the library itself:
1. Adopt Java records for immutable value objects (`Job`, `JobAction`, `JobStatistics`, etc.) — reduces boilerplate by ~60%
2. Replace `HashMap<String, String>` status maps with typed enums and proper mapping
3. Remove deprecated constants (any referencing old platform names like `citiprepaid.com`)
4. Replace `STATUS_ID_*` int constants with a proper `ScheduleStatus` enum

## API Contract Stability

The interfaces in this library (`IJobManager`, `IJobAgent`, `IJobFileManager`, `IJobProfileManager`) are effectively **platform APIs**. Any method signature change is a breaking change that affects multiple deployed services. Current gaps:

1. **No @deprecated annotations visible** on any constants or methods — consumers cannot be guided to migrate away from obsolete APIs
2. **No formal API versioning** — the library uses a single artifact version for both additive and breaking changes
3. **No interface evolution strategy** — no default methods, no adapter patterns to allow gradual migration

## Compliance Considerations

This library defines the data structures that carry references to PCI DSS-sensitive identifiers (`device_id`, `card_type`, `exp_month`, `exp_year`, `echeck_id`, `iban_number`, `VIRTUAL_EXPRESS_URL`). Under PCI DSS Requirement 6.3.2, this library must be:
1. Listed in the software inventory as a component that processes or references payment card data
2. Subject to code review processes before any version release
3. Included in SBOM (Software Bill of Materials) for supply chain security compliance

The `VIRTUAL_EXPRESS_URL` constant (line 67 of `JobServiceConstants.java`) is particularly notable — virtual card delivery URLs can contain credential parameters and must not be logged. Any service storing `JobAction` records with this field populated in a logging framework could inadvertently capture virtual card credentials in log files. This should be reviewed under PCI DSS Requirement 3.5 (protect stored account data).
