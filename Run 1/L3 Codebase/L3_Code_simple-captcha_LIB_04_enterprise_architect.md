# simple-captcha_LIB — Enterprise Architect View

## Platform Generation
**Gen-1** — Apache Ant build, Java 1.6 target, javax.servlet API (pre-Jakarta), no Maven, no Spring, no CI/CD. This is a verbatim copy of an open-source library from 2010–2011 with no modernisation. The library pre-dates the `com.citi.prepaid` estate and has been carried as a vendored dependency.

## Business Domain
**Security Controls / Anti-Automation / Identity Verification.** Provides CAPTCHA challenges as a friction layer against bot attacks on web forms. Applicable to cardholder self-service portals, registration, login, and payment claim flows.

## Role in Platform
**Shared UI security component** — embedded in consumer web applications as a JAR dependency. Not a standalone service. Provides the CAPTCHA image/audio generation and validation primitives that upstream applications call.

## Dependencies
### Library Dependencies (vendored in `lib/`)
| Dependency | Version | Notes |
|---|---|---|
| `imaging.jar` | Unknown | Image processing; bundled locally, no Maven coordinates |
| `jstl-1.2.jar` | 1.2 | JSTL for example JSP pages |
| `standard.jar` | Unknown | JSTL standard tag lib |

### Runtime Dependencies (provided by container)
| Dependency | Notes |
|---|---|
| `javax.servlet-api` | Tomcat servlet API (javax namespace — pre-Jakarta) |

## Integration Patterns
- **JAR embedding**: Copied to consuming application's WEB-INF/lib.
- **Servlet pattern**: `SimpleCaptchaServlet`, `StickyCaptchaServlet`, `AudioCaptchaServlet` mapped in consuming app's `web.xml`.
- **Session storage**: Captcha objects stored in `HttpSession`.
- **JavaBean pattern**: `CaptchaBean` for JSP EL integration.

## Strategic Status
**Legacy / Candidate for Replacement.**
- Version 1.2.1 from 2011 — unmaintained for 14 years.
- No CVE tracking, no security patches, no active maintenance.
- AI/ML CAPTCHA solvers can defeat simple text distortion CAPTCHAs with >80% accuracy on 2011-era implementations.
- Modern alternatives: Google reCAPTCHA v3 (invisible), hCaptcha, Cloudflare Turnstile — these provide stronger bot detection with better accessibility and no client-side image generation overhead.
- **Recommendation**: Replace with a modern CAPTCHA service. If on-premises is required, use a maintained library (e.g., `jcaptcha` with active maintenance, or a custom implementation using stronger distortion).

## Migration Blockers
- `imaging.jar` dependency of unknown provenance must be identified and replaced or a Maven coordinate found.
- Consuming applications must update their `web.xml` servlet mappings.
- javax.servlet namespace → jakarta.servlet migration required for Tomcat 10+.
- Audio voice WAV files must be re-licensed or sourced from a maintained library.
