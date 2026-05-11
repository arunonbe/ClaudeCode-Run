# spring-utils_LIB — Data Architect View

## Data Stores
The library does not own any data store. It provides infrastructure utilities consumed by services that own their own databases. However, two components interact with data stores at runtime:

| Component | Interaction | Notes |
|---|---|---|
| `DatabaseMonitorTestExecutor` | Executes a configurable SQL query against a caller-supplied `DataSource` | Used for DB connectivity health checks; SQL is not parameterised but is configuration-controlled |
| `DatabaseQueryTestExecutor` | Executes a configurable SQL query and validates result | Same pattern as above |

## Schema / Tables
None owned. The library executes caller-supplied SQL against caller-supplied DataSources.

## Sensitive Data Handling
The `AuditMethodInterceptor` serialises method arguments to XML using XStream and writes them to the application logger. If any service passes objects containing sensitive fields (PAN, SSN, account numbers, tokens) to intercepted methods, those values will appear in logs.

**This is a significant PCI DSS compliance risk**: Requirement 3.3 prohibits storing sensitive authentication data post-authorisation, and Requirement 10.3 requires that PANs be masked in logs.

No data masking is implemented in `AuditMethodInterceptor`. The mitigation depends entirely on callers having configured `log.isDebugEnabled()=false` in production (the serialised arguments are only logged at DEBUG level; method entry/exit are logged at INFO level without argument content).

## Encryption
No encryption logic is present in the library. TLS/SSL for HTTP Invoker connections is delegated to the underlying `HttpURLConnection` / Servlet container configuration.

## Data Flow
```
Inbound Method Call
       |
       v
AuditMethodInterceptor (AOP)
  - [DEBUG] Serialize args to XML (XStream) → Logger
  - Invoke target method
  - [DEBUG] Serialize return value to XML → Logger
  - [INFO] Log class::method END (duration)
       |
       v
MDCWriter
  - Sets MDC keys: method name, class, duration
  - Cleared in finally block
```

```
JMS RPC Data Flow:
Client Proxy → XStreamMessageMarshaller → ObjectMessage (JMS)
                                                    |
                                            JMS Broker (Queue)
                                                    |
                                        JmsInvokerServiceExporter → Target Bean
                                        Response → ObjectMessage → Client
```

## Data Quality / Retention
- The library does not define any data quality rules or retention policies.
- Log retention for audit interceptor output is controlled by the consuming application's logging configuration.

## Compliance Gaps
| Gap | Standard | Requirement | Notes |
|---|---|---|---|
| No argument masking in `AuditMethodInterceptor` | PCI DSS | Req 3.3, 10.3 | DEBUG logs may contain PANs or account numbers if enabled |
| XStream `AnyTypePermission.ANY` | PCI DSS | Req 6.2 (secure development) | Unsafe deserialisation enabled by default in `AuditMethodInterceptor` constructor |
| No PAN truncation in monitor SQL output | PCI DSS | Req 3.3 | If monitor SQL returns card data, it will be logged to monitor view |
| No audit trail for monitor health-check access | PCI DSS | Req 10 | `/monitor` access is not logged with user identity |
