# Data Architect — wirecard_performance-tracing-library_LIB

## Data Stores
This is a library — it has no persistent data store of its own.

| Output | Type | Notes |
|---|---|---|
| Application logs (SLF4J) | Log stream | `Trace` JSON objects emitted via Logback/Logstash |
| None other | — | No DB, no file system, no messaging |

## Schema / Data Model
No database schema. The sole data output is the `Trace` value object emitted to SLF4J:

```json
{
  "className": "com.wirecard.checkagent.persistance.CheckRepository",
  "methodName": "findByReferenceId",
  "executionTime": 500
}
```

Fields:
| Field | Type | Description |
|---|---|---|
| className | String | Fully-qualified class name of the intercepted method |
| methodName | String | Method name |
| executionTime | long (ms) | Wall-clock execution time in milliseconds |

No method parameters, return values, or caller context are logged — no PII or financial data in the trace output.

## Sensitive Data
None. The library explicitly logs only:
- Class name (code metadata)
- Method name (code metadata)
- Execution time in milliseconds (performance metric)

This design is consistent with PCI DSS minimum-logging requirements (no SAD/PAN in logs).

## Encryption
Not applicable — library has no data persistence.

## Data Flow
```
Application Method Call
  │
  ├── PerformanceTracingInterceptor.invoke()
  │     └── Spring StopWatch measures wall-clock time
  │
  ├── If executionTime > threshold → log.warn(Trace.toString())
  └── If DEBUG enabled → log.debug(Trace.toString())
         │
         └── SLF4J → Logback → Logstash encoder → ELK / centralized logging
```

## Data Quality / Retention
- Log retention governed by the consuming service's log configuration and the platform's centralized logging (ELK/Logstash)
- No data quality constraints — execution time is always a positive long; class/method names are always populated by JVM reflection
- StopWatch uses `System.currentTimeMillis()` equivalent (Spring StopWatch) — wall-clock, not CPU time; network/IO wait included in measurement

## Compliance Gaps
1. None significant for this library itself
2. If a consuming service misconfigures `monitoredPackages` to be too broad, high-frequency WARN logs could generate excessive log volume — potential log flooding denial of observability
3. Library enforces no access controls on what packages can be monitored — configuration governance rests with consuming services
