# simple-captcha_LIB — Business Analyst View

## Business Purpose
`simple-captcha_LIB` is an open-source Java CAPTCHA generation and validation library (SimpleCaptcha, version 1.2.1, originally by James Childers, copyright 2010–2011). It is included in the Onbe/Citi Prepaid repository to provide bot-prevention challenges on web forms — particularly cardholder self-service pages where automated abuse (credential stuffing, account enumeration, fraudulent registrations) is a threat.

The library provides both visual (image-based) and audio CAPTCHA variants to support accessibility requirements.

## Capabilities
1. **Visual CAPTCHA Generation**: Generates distorted text images using pluggable backgrounds, text producers, word renderers, noise producers, and gimpy (distortion) renderers.
2. **Audio CAPTCHA Generation**: Generates spoken-number audio challenges using sampled voice files (7 voice profiles: alex, bruce, fred, kathy, ralph, vicki, victoria) with optional background noise (radio tuning, restaurant, swimming, zombie).
3. **CAPTCHA Validation**: `captcha.isCorrect(answerStr)` — case-sensitive string comparison against the generated answer.
4. **Session-Based Sticky CAPTCHA**: `StickyCaptchaServlet` stores a CAPTCHA in session and reuses it until it expires (default 10 minutes) or is answered, preventing rapid image cycling attacks.
5. **Servlet Integration**: Three servlet variants — `SimpleCaptchaServlet`, `StickyCaptchaServlet`, `AudioCaptchaServlet` — for direct embedding in Java EE web applications.
6. **JavaBean wrapper**: `CaptchaBean` for JSP/framework integration.

## Entities
- `Captcha` — image CAPTCHA with serializable builder; stores answer, image, timestamp.
- `AudioCaptcha` — audio CAPTCHA with serializable builder; stores answer, audio sample.
- Text producers: `DefaultTextProducer` (alphanumeric), `NumbersAnswerProducer`, `ArabicTextProducer`, `ChineseTextProducer`, `FiveLetterFirstNameTextProducer`.
- Background producers, noise producers, gimpy renderers — pluggable rendering pipeline.

## Business Rules
- Default CAPTCHA text: 5 characters drawn from a reduced alphabet (avoids visually similar characters: no 0/O, 1/l/I, etc.).
- Text is generated using `java.security.SecureRandom` — cryptographically random.
- Audio CAPTCHA uses number sequences.
- Sticky CAPTCHA default TTL: 10 minutes (600,000ms), configurable via `ttl` init-param.
- `isCorrect()` performs case-sensitive exact match — no fuzzy matching or normalisation.

## Process Flows
1. User arrives at protected form page → page requests `/captcha.png` → `SimpleCaptchaServlet` generates image, stores `Captcha` object in HTTP session under key `"simpleCaptcha"`.
2. User submits form with CAPTCHA answer → application retrieves `Captcha` from session → `captcha.isCorrect(userAnswer)` → passes or fails.
3. Sticky variant: if CAPTCHA exists in session and has not expired, reuses existing image; otherwise generates new one.

## Compliance Relevance
- CAPTCHA is a control against automated account enumeration and credential stuffing — relevant to PCI DSS Req 8 (identity management) and fraud prevention.
- Audio CAPTCHA supports WCAG 2.1 accessibility compliance.
- The version in use (1.2.1, circa 2011) is considered weak by modern standards — AI/ML-based solvers can defeat simple text distortion with high accuracy.

## Risks
- Library version 1.2.1 is from 2011 — no active maintenance, no security patches.
- Case-sensitive comparison without answer normalisation — small UX friction.
- The compiled `.class` files and the JAR (`dist/simplecaptcha-1.2.1.jar`) are committed to the repository — binary artefacts in source control.
- No protection against CAPTCHA answer harvesting via session attribute inspection if an attacker can access session storage.
