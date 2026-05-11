# Solution Architect View — CONFIG_uat

## Technical Architecture
UAT uses the Gen-2 Tomcat externalized-configuration pattern, but adds a unique structural element: the **`tomcat/registry/`** directory containing per-service `JAVA_OPTIONS/*.txt` files. These define the full JVM launch parameters for each named Tomcat instance (separate Tomcat home per service under `D:\c-base\opt\tomcat\servers-8.5.57\{SERVICE}\`).

### Service Architecture on UAT
Each service runs as a separate Tomcat instance with:
- Its own Catalina home directory
- Its own GC log file
- Its own JMX port (authentication-enabled, no TLS)
- Shared keystore and truststore (`u-na-app01.jks`, `truststore.jks`)
- Shared JMX password/access files

This architecture means `u-na-app01` runs 9 separate JVMs simultaneously.

## API Surface
No APIs defined in this repository. The services configured here expose APIs from their application code repos. The `api-security.properties` and `APIValidation.properties` files define security and validation parameters for the AccountManagementAPI and ClientAPI.

## Security Posture

### Hardcoded Secrets Found (file locations, values not reproduced)

1. **`tomcat/registry/u-na-app01/JAVA_OPTIONS/AccountManagement.txt`** (and ClientAPI.txt, DebitAPI.txt, and all other JAVA_OPTIONS files):
   - `javax.net.ssl.keyStorePassword` — TLS keystore password in plaintext
   - `javax.net.ssl.trustStorePassword` — TLS truststore password in plaintext
2. **`config/u-na-app01/config/cardnotification/CardNotification.properties`**:
   - SAP Mobile Services SMS gateway username and password
3. **`config/u-na-app01/config/ivrws/ivrws.properties`**:
   - `appKey` — IVR application API key in plaintext
4. **`config/u-na-app02/config/cardnotification/CardNotification.properties`** — same credentials as app01
5. All the above are duplicated for `u-na-app02`

### Additional Security Concerns
- `jmxremote.ssl=false` — JMX management interface (`-Dcom.sun.management.jmxremote`) accessible on network without TLS
- `jmxremote.authenticate=true` — password-based authentication is active for JMX, but the password file path is on the server filesystem
- `CBASE_HOME` environment variable points to `D:/c-base` — all services share this base directory
- AcceptPrechecks uses `B2CTEST` agent while other UAT services use `B2C` — inconsistent agent code in UAT

## Technical Debt
- **Legacy GC flags**: `-XX:MaxPermSize=256m`, `-XX:+CMSIncrementalMode`, `-XX:+CMSIncrementalPacing`, `-XX:+CMSPermGenSweepingEnabled`, `-XX:+CMSClassUnloadingEnabled` — PermGen was eliminated in Java 8; these flags are either ignored or cause warnings. `-XX:+UseParNewGC` is deprecated. These will be hard errors in JDK 9+.
- **`-XX:+PrintGCDetails`, `-XX:+PrintHeapAtGC`, `-XX:+PrintGCApplicationStoppedTime`** — legacy GC logging flags replaced by `-Xlog:gc*` in JDK 9+
- **Tomcat 8.5.57** — End of Life August 2024
- **Duplicate config for u-na-app02** — same files as u-na-app01; no templating
- **No CI/CD pipeline** — all config changes are manual
- **JVM tuning using CMS GC** — legacy GC algorithm removed in JDK 15; must migrate to G1 or ZGC

## Gen-3 Migration Requirements
1. **Extract all JVM passwords to vault** — `keyStorePassword` and `trustStorePassword` must never be in source control
2. **Replace JAVA_OPTIONS text files with container ENV variables or Kubernetes Secrets** — containerisation makes JVM params injection clean
3. **Upgrade JVM flags** — remove deprecated PermGen/CMS flags; adopt G1GC with JDK 17+ compatible flags
4. **Upgrade Tomcat to 10.x** or migrate to embedded Spring Boot server (Jakarta EE namespace)
5. **Upgrade JDK to 17 or 21**
6. **Enable JMX TLS** or replace JMX with Prometheus/Micrometer metrics endpoint
7. **Remove duplicate u-na-app02 config** — generate from template or use ConfigMaps
8. **Add GitLab CI pipeline** for automated UAT config deployment
9. **Consolidate agent codes** — decide whether UAT should use `B2C` or `B2CUAT` throughout

## Code-Level Risks
- `ivrws.properties` contains `appKey` (IVR API key) — if this key is also used in PROD, a UAT compromise exposes production IVR
- `routingNA=011001234` in ClientAPI — ACH routing number committed; verify this is a test routing number and not production
- `cardnotification.smspullenabledforprograms` list in CardNotification.properties contains hundreds of production program IDs — an accidental SMS send from UAT would affect real cardholder programs if gateway routing is not correctly sandboxed
- Both `u-na-app01` and `u-na-app02` have identical credentials — if credentials are rotated on one server, the other falls out of sync unless both are updated simultaneously
