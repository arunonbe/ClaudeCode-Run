# 02 Data Architect — ecount-host-log4j_LIB

## Data Entities

The library handles no persistent data and defines no domain entities, database tables, or data transfer objects. Its only data artefacts are two transient, static String fields resolved at class-load time.

### Static Fields in `EcountPatternParser`

| Field | Type | Value | Source |
|---|---|---|---|
| `dnsName` | `static String` | Hostname of the JVM host | `InetAddress.getLocalHost().getHostName()` |
| `dnsNameIp` | `static String` | `"hostname(ip.addr),"` | `InetAddress.getLocalHost().getHostName()` + `getHostAddress()` |

File: `src/main/java/com/ecount/log4j/helpers/EcountPatternParser.java`, lines 10–21.

## Data Flow

```
Log4j Appender
    --> EcountPatternLayout (configured in appender's layout class)
        --> EcountPatternParser.finalizeConverter(char c)
            --> case 'h' : DnsPatternConverter.convert(event) returns dnsName
            --> case 'H' : DnsIpPatternConverter.convert(event) returns dnsNameIp
    --> Formatted log line emitted to appender destination (file / console / syslog)
```

The log line is a string. The library does not write to any database, message queue, or external API.

## Sensitive Data Considerations

The library itself does not process cardholder data, PII, or authentication credentials. However, the formatted log lines it produces are only as safe as the data logged by consuming services.

**Key risk**: If an upstream service (e.g., `ecount-core_SVC` or `emboss-extract_LIB`) logs a full PAN, CVV, or other SAD before calling the appender, the `EcountPatternLayout` will include that sensitive data verbatim in the output. There is no built-in masking.

PCI DSS Req 3.5.1 prohibits storage of SAD post-authorisation. Log files written by appenders configured with this layout could constitute SAD storage if consuming services log card numbers.

## Dependency Data Footprint

The library's only runtime dependency is `log4j:log4j:1.2.15` (`pom.xml` line 24). Log4j 1.2.15 itself carries no database drivers or data persistence.

## Configuration Data

No property files, Spring XML contexts, or YAML files are bundled with the library. All configuration is done by consuming services in their own `log4j.xml` / `log4j.properties`, specifying:

```xml
<layout class="com.ecount.log4j.EcountPatternLayout">
    <param name="ConversionPattern" value="[%d] %-5p %H %c %m%n" />
</layout>
```

The `%H` token here would render as `hostname(ip),` in the output.

## Summary Assessment

From a data architecture standpoint, this library is a pass-through: it adds metadata (host identity) to log records but does not store, transform, or route data independently. The data architecture risk is indirect — the library amplifies any existing PII/SAD logging practices in consuming services by adding host identity context that could assist forensic reconstruction of sensitive transactions.
