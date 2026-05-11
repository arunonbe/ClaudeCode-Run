# simple-captcha_LIB — Data Architect View

## Data Stores
| Store | Type | Purpose |
|---|---|---|
| HTTP Session | In-memory (Tomcat session) | Stores `Captcha`/`AudioCaptcha` object under key `"simpleCaptcha"` / `"audioCaptcha"` |
| No persistent store | — | No database, no file-based persistence |

## Schema / Tables
Not applicable — session-only storage.

## Sensitive Data
| Data Element | Location | Sensitivity | Notes |
|---|---|---|---|
| CAPTCHA answer (plaintext) | `Captcha.Builder._answer` (session) | LOW | Short alphanumeric string; not sensitive in isolation but constitutes a shared secret for bot-prevention |
| CAPTCHA timestamp | `Captcha.Builder._timeStamp` (session) | LOW | Generation time for TTL enforcement |
| CAPTCHA image | `Captcha.Builder._img` (session, serialised) | LOW | BufferedImage serialised to PNG in session |

## Encryption
- **Answer storage**: Answer stored as plaintext String in the `Captcha` object in HTTP session. Not encrypted.
- **Session security**: Session confidentiality depends on HTTPS (TLS) and secure session cookie configuration in the embedding application — not enforced by this library.
- **Serialisation**: `Captcha` and `AudioCaptcha` implement `Serializable`. If Tomcat session persistence (file or database) is enabled, CAPTCHA objects will be written to disk/database as Java serialised objects. No encryption at rest.
- **Random number generation**: `DefaultTextProducer` and `AudioCaptcha.Builder` use `java.security.SecureRandom` — cryptographically strong PRNG.

## Data Flow
```
GET /captcha.png
  → SimpleCaptchaServlet.doGet()
    → Captcha.Builder(200, 50).addText(renderer).gimp().addNoise().addBackground().build()
    → CaptchaServletUtil.writeImage(response, captcha.getImage()) → PNG to browser
    → session.setAttribute("simpleCaptcha", captcha)

Form POST (user submits answer)
  → Application code: captcha = (Captcha) session.getAttribute("simpleCaptcha")
  → captcha.isCorrect(userAnswer) → boolean
  → [application clears captcha from session after validation]
```

## Data Quality / Retention
- Sticky CAPTCHA expires after TTL (default 10 min) via timestamp comparison in `StickyCaptchaServlet.shouldExpire()`.
- Simple CAPTCHA (non-sticky) lives in session until session expires — no explicit TTL.
- Session objects are serialised to disk if Tomcat persistence is enabled — `Captcha` implements `Serializable` with custom `writeObject`/`readObject` using `ImageIO.write`/`read`.

## Compliance Gaps
- **Session Security**: Library does not enforce `Secure`, `HttpOnly`, or `SameSite` cookie flags for the session cookie — this must be configured in the embedding application.
- **GDPR/CCPA**: CAPTCHA data is transient (session-scoped) and contains no personal data, so no compliance gap here.
- **Accessibility (WCAG 2.1)**: Audio CAPTCHA provided for accessibility, but the 2011-era audio samples may not meet modern accessibility standards.
