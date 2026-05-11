# nexpay-ivr-bff — Enterprise Architect View

## Platform Generation

**Gen-3** — NexPay cloud-native microservice on Azure.

Evidence:
- Spring Boot (boot module)
- Azure Container Apps deployment
- Azure App Configuration + Azure Key Vault
- Azure Managed Identity
- OpenTelemetry (OTLP gRPC via custom `otel-grpc` library)
- `com.onbe.nexpay` namespace
- Parent POM: `nexpay-parent`
- Project Loom virtual threads (`spring.threads.virtual.enabled: true`)
- External APIM publication

## Business Domain

**IVR / Telephony Integration** — Backend-for-Frontend for IVR systems that require cardholder account data. Part of the NexPay multi-channel customer service domain:
- Call-centre cardholder verification
- Balance and account inquiry via IVR
- Card activation and management via IVR (future)

## Role in the Platform

```
[External IVR System / Telephony Switch]
        | (HTTPS via External Azure APIM)
        v
[nexpay-ivr-bff]  ← BFF translating IVR protocol to NexPay internal APIs
        |
        +--> [nexpay-auth-svc]  (authentication / token validation)
        +--> [nexpay-recipient-profile-svc / other profile SVC] (customer data — future)
        +--> [Azure Cache for Redis] (affiliate/content caching)
        |
        v
[Structured customer data response → IVR system]
```

The BFF pattern is appropriate here: IVR systems have rigid field-code-based protocols that differ from NexPay's internal data model. The BFF translates between these worlds and shields downstream services from IVR-specific concerns.

## Dependencies

### Upstream (services nexpay-ivr-bff depends on)
| Dependency | Type | Status |
|---|---|---|
| `nexpay-parent:0.2.8-SNAPSHOT` | Maven POM | SNAPSHOT — unstable |
| `otel-grpc:1.0.0-SNAPSHOT` | Internal OTel library | SNAPSHOT — unstable |
| `nimbus-jose-jwt:10.9` | JWT library | Stable |
| Azure App Configuration + Key Vault | Config/secrets | Stable |
| Azure Cache for Redis | Cache | Stable |
| `nexpay-auth-svc` | Auth service | Runtime dependency — URL from config |

### Downstream (external callers)
- External IVR system / telephony switch (via external APIM)
- Call-centre middleware

## Integration Patterns

1. **BFF Pattern**: Service aggregates and transforms data from internal NexPay services into the IVR protocol format
2. **REST API (HTTP/JSON)** over external APIM: `POST /fs/customer/v4/inquiry`
3. **Redis caching**: Jedis connection pool for affiliate/content caching
4. **OpenTelemetry baggage propagation**: `AuditFilter` propagates actor.id, source, reason through request chain
5. **Azure Managed Identity**: Credential-free access to Azure services
6. **Virtual threads**: Java Project Loom for high-concurrency I/O

## Strategic Status

| Dimension | Assessment |
|---|---|
| Lifecycle | **Active development / Pre-production** — Stub controller indicates feature is not yet complete |
| Business criticality | High — IVR cardholder verification is a PCI DSS-regulated function |
| Technical debt | Medium — Java 25, SNAPSHOTs, stub in production code |
| Security posture | **High risk** — external-facing API with SSN/PAN in response, API-key auth only, stub deployed |
| Strategic fit | High — IVR integration is a core channel for prepaid card cardholder services |

## Migration Considerations (Forward-Looking)

1. **Complete the implementation**: Replace stub with actual downstream service calls to `nexpay-auth-svc` and a cardholder profile service
2. **Remove `DummyController`**: Delete from main source tree before production deployment
3. **Upgrade to Java 21 LTS**: Replace Java 25
4. **Stabilise parent and otel-grpc**: Cut release versions
5. **Strengthen authentication**: Replace `x-api-key`/`x-api-secret` with mutual TLS or OAuth2 client credentials for external IVR caller authentication
6. **PAN/SSN masking**: Implement `obfNamePrfx` logic; mask PAN to first 6/last 4 in responses; never return full SSN
7. **Redis TTL**: Add appropriate TTL to all cached entries
8. **Jedis → Lettuce migration**: Consider reactive Redis client for better virtual-thread compatibility
