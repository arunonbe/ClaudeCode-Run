# simple-captcha_LIB — Solution Architect View

## Technical Architecture
Pure Java library with Ant build. Two main classes (`Captcha`, `AudioCaptcha`) follow the Builder pattern and are `Serializable`. Pluggable architecture: text producers, word renderers, background producers, noise producers, and gimpy (distortion) renderers are all injected into the builder. Three HttpServlet subclasses provide direct web integration. Packaged as a single JAR (`simplecaptcha-1.2.1.jar`) that includes the `imaging.jar` contents and audio WAV files.

## API Surface

### Core Builder API
```java
new Captcha.Builder(width, height)
    .addText([TextProducer], [WordRenderer])
    .addNoise([NoiseProducer])
    .addBackground([BackgroundProducer])
    .gimp([GimpyRenderer])
    .addBorder()
    .build()
// → Captcha with .getImage(), .getAnswer(), .isCorrect(String), .getTimeStamp()
```

### Servlet API (web.xml mapping targets)
| Class | Pattern | Description |
|---|---|---|
| `SimpleCaptchaServlet` | e.g. `/captcha.png` | Generates new CAPTCHA on every GET |
| `StickyCaptchaServlet` | e.g. `/stickyCaptcha.png` | Reuses session CAPTCHA until TTL |
| `AudioCaptchaServlet` | e.g. `/audioCaptcha.wav` | Generates audio challenge |

### Session Key Constants
- `Captcha.NAME = "simpleCaptcha"` 
- `AudioCaptcha.NAME = "audioCaptcha"`

## Security Posture

### Authentication / Authorisation
Not applicable — bot-prevention library, not an authentication system.

### Cryptography — POSITIVE FINDING
- **`DefaultTextProducer.java:14`** — `private static final Random RAND = new SecureRandom()` — uses `java.security.SecureRandom` for text generation. Correct choice. Cryptographically unpredictable CAPTCHA answers.
- **`AudioCaptcha.java:45`** — `private static final Random RAND = new SecureRandom()` — same. Correct.

### CAPTCHA Strength Assessment
- Text character set: 23 characters (reduced from 36 to remove visually ambiguous chars). 5-character default = 23^5 = ~6.4 million combinations. With image distortion, brute-force is impractical.
- **However**: Deep learning OCR can solve 2011-era SimpleCaptcha implementations with high accuracy. This library should not be used as the sole bot-prevention layer in a high-risk context.

### Serialisation Security
`Captcha` and `AudioCaptcha` implement `Serializable` with custom `readObject`/`writeObject`. The `writeObject` serialises the BufferedImage as PNG. If Tomcat session persistence stores sessions to disk or database, these objects are serialised. If an attacker can read serialised session data, they can extract the CAPTCHA answer directly.

### Answer Comparison
`Captcha.isCorrect(String answer)` at line 255 uses `answer.equals(_builder._answer)` — no case normalisation, no timing-safe comparison (though timing differences in string comparison of short strings are not exploitable in this context).

### Bundled Binary Artefacts
- `dist/simplecaptcha-1.2.1.jar` — committed to source. Should be removed from SCM; artefact should be published to Maven/Nexus and consumed as a dependency.
- `bin/` — compiled `.class` files committed. Must be excluded via `.gitignore`.
- `lib/imaging.jar` — unknown provenance, no source, no CVE tracking possible.
- `lib/simplecaptcha-latest.jar` — `latest` naming in a version-controlled repository is a code smell; version is unspecified.

### No CI Security Scanning
No CodeQL, no Dependabot, no SAST tooling. Vulnerabilities in bundled `imaging.jar` are completely undetected.

## Technical Debt

### Critical
- No CI/CD, no security scanning — library is effectively a black box from a security standpoint.
- `imaging.jar` provenance unknown — potential CVE exposure with no tracking mechanism.
- Compiled binaries (`bin/`, `dist/`) committed to source control.

### High
- Java 1.6 target — 3 major LTS versions behind (Java 17 LTS current). Java 1.6 bytecode is generated with `ACC_SYNCHRONIZED` and other obsolete flags.
- `javax.servlet` namespace — incompatible with Tomcat 10+ / Jakarta EE 9+ without namespace migration.
- No `pom.xml` — not consumable via Maven without publishing the JAR manually; no dependency management.

### Medium
- `StickyCaptchaServlet.java:104` — potential null dereference: if `session.getAttribute(NAME)` returns null on first check, `captcha` variable is null before the null check on line 100 assigns a new captcha, but the code then re-reads from session on line 104 without the local assignment — could throw NPE in the uncommon race case.
- `SimpleCaptchaServlet` static fields `_width` and `_height` modified in `init()` — not thread-safe for concurrent servlet initialisation.

### Low
- Audio WAV files for 7 voice profiles × 10 digits = 70 files in both `bin/` and `Java/src/` — duplicated.

## Gen-3 Migration Requirements
1. Replace with Google reCAPTCHA v3, hCaptcha, or Cloudflare Turnstile (recommended).
2. If internal CAPTCHA is required: convert to Maven project, publish to Nexus/GitHub Packages, add CI pipeline with CodeQL.
3. Replace `imaging.jar` with a maintained, Maven-coordinate-identified image processing library.
4. Migrate from `javax.servlet` to `jakarta.servlet` for Tomcat 10+ compatibility.
5. Remove committed binaries (`bin/`, `dist/`) from source control.
6. Upgrade to Java 17+ target.

## Code-Level Risks
| File | Line | Risk | Severity |
|---|---|---|---|
| `lib/imaging.jar` | N/A | Unknown-provenance bundled JAR — cannot track CVEs | HIGH |
| `dist/simplecaptcha-1.2.1.jar` | N/A | Binary committed to source control | MEDIUM |
| `StickyCaptchaServlet.java` | 100–104 | Potential NPE if attribute is null and reassignment race | MEDIUM |
| `SimpleCaptchaServlet.java` | 33–34 | Static mutable fields `_width`, `_height` — not thread-safe | MEDIUM |
| `build.xml` | 23 | `source="1.6" target="1.6"` — Java 1.6 bytecode target | LOW |
| `DefaultTextProducer.java` | 14 | POSITIVE: `SecureRandom` used correctly | N/A |
