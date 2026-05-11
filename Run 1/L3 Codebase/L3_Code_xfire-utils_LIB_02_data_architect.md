# xfire-utils_LIB — Data Architect View

## Data Stores
This library has **no data stores**. It is a pure infrastructure/transport library. It does not persist, read, or cache data.

## Schema / Tables
None — no database access, no file storage, no caching.

## Sensitive Data Handling
Although the library does not store data, it is a transport layer and therefore handles data in-flight:

- **SOAP message payloads**: All data passing through `XFireClientFactoryBean` proxies or `SpringJmsTransport` channels is carried as SOAP XML — including any sensitive business data from calling services
- **HTTP Basic Auth credentials**: `username` and `password` properties in `XFireClientFactoryBean` carry authentication credentials for protected SOAP endpoints; these flow as HTTP `Authorization` header (Base64-encoded, not encrypted without TLS)
- **JMS message content**: SOAP messages routed over JMS may contain sensitive business payloads; JMS message content is not encrypted at the library level

## Encryption
- **No encryption implemented at this library level**
- **TLS for HTTP transport**: Dependent on the WSDL endpoint URL; if the URL is `https://`, XFire/JVM handles TLS natively; if `http://`, no encryption
- **HTTP Basic Auth**: Base64-encoded, not encrypted unless transmitted over TLS; plaintext equivalent on non-TLS transports
- **JMS transport**: Encryption depends on the JMS broker configuration; this library adds no encryption

## Data Flow
```
Caller service → XFireClientFactoryBean proxy.method(args)
  → XFire serializes args to SOAP XML
  → [HTTP transport] → SOAP request over HTTP(S) to endpoint URL
  → [JMS transport] → SOAP request placed on JMS queue (SpringJmsTransport)
  → Remote service processes SOAP
  → SOAP response returned
  → XFire deserializes response
  → Caller receives Java return value
```

The library is transparent to the data it carries; data sensitivity is determined entirely by the calling services.

## Compliance Gaps
1. **No transport security enforcement**: The library does not enforce or verify TLS on HTTP transport; a caller providing an `http://` WSDL URL will transmit in cleartext — including potentially sensitive cardholder-related data if the calling service handles CHD
2. **HTTP Basic Auth in plaintext config**: `username` and `password` in Spring XML configuration files represent credentials stored on application server disk without encryption
3. **No SOAP message signing or encryption**: The library provides no WS-Security hooks for XML message-level security (signing or encryption) — industry standard for sensitive SOAP deployments
4. **JMS payload in cleartext**: SOAP messages on JMS queues are not encrypted at the library level; queue-level security depends entirely on the broker configuration
