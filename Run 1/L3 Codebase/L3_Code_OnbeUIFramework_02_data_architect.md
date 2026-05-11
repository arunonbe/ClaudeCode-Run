# Data Architect — OnbeUIFramework

## Data Stores
- **`InMemorySourceOfTruth`** (`@onbe/store`): An in-memory key-value Map. Keys are serialized using `DefaultSerializer` (JSON.stringify for non-strings). Values are stored as-is. No persistence; cleared on garbage collection or page/app reload.
- No databases, no file systems, no external caches are used by this library.

## Schema / Tables
Not applicable (frontend library). The `InMemorySourceOfTruth` is a generic key-value store; schema is determined by the consumer.

## Sensitive Data Handling
- **Password validator**: accepts a plaintext password string in the browser/Node process. It does NOT log, store, or transmit the password. Risk: if a consumer incorrectly logs the return value including the original password, that data could be exposed — but the library itself does not create this risk.
- **Store**: caches arbitrary data in memory. If a consumer stores PAN, token, or PII objects in the store, they reside in browser memory and are accessible to any JavaScript running in the same context (XSS risk).

## Encryption
None. The library performs no encryption. In-memory data is cleartext.

## Data Flow
```
Password validation:  UI input string → validatePassword() → result object (no I/O)

Store (cached fetch):
  Consumer UI → StoreImpl.cached(key) → InMemorySourceOfTruth.reader(key)
    → if EMPTY_CACHE: StoreImpl.fetch(key) → Fetcher(key) [HTTP call by consumer]
      → InMemorySourceOfTruth.writer(key, value)
    → SimpleSubject.next() → all subscribers notified
```

## Data Quality / Retention
- In-memory cache has no TTL, no eviction policy, and no size limit. Unbounded growth is possible if many distinct keys are cached.
- No data validation on store values; any object type is accepted.

## Compliance Gaps
1. **No cache eviction / TTL**: if the store is used to cache sensitive user data (account balances, card details), data may persist in memory beyond the session lifecycle.
2. **No XSS hardening for cached data**: values retrieved from the store are passed directly to React components without sanitization; if a consumer caches server responses containing HTML, XSS is possible at render time.
3. **No structured logging / audit trail**: the framework generates no audit events; compliance logging must be implemented entirely by consumers.
