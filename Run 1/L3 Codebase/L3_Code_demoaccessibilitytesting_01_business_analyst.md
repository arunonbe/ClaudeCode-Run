# Business Analyst Report — demoaccessibilitytesting

## 1. Business Purpose
demoaccessibilitytesting is a **React single-page application (SPA) and associated accessibility testing toolchain** for the Onbe recipient-facing payment portal (`mypaymentvault`). The repository serves two purposes:

1. **Application shell**: A React 18 SPA (in `project/`) that mimics or exercises the cardholder-facing payment vault application, used as a target for automated accessibility (a11y) testing.
2. **Accessibility CI pipeline**: A GitHub Actions workflow (`.github/workflows/axe.yml`) that runs the `@axe-core/cli` scanner against the live QA environment of `mypaymentvault.qa.onbe.dev` to detect WCAG compliance issues.

The application represents the **cardholder self-service experience** for prepaid card activation, fund management, and wallet integrations (Apple Pay, Google Pay, Samsung Pay).

---

## 2. Capabilities

### 2.1 Application Features (Inferred from UI Assets and Mock API)

| Feature | Evidence |
|---|---|
| Card Activation | `mock-server/json/cardActivation/GET.json`, `POST.json`; images `ActivationIdentificationBanner*.png` |
| Multi-factor auth settings (postal code, mobile, SSN, DOB, PUID) | `cardActivation/GET.json` — `authSettingsDisplay` object |
| Wallet integrations | Images: `AddToWallet_ApplePay.png`, `AddtoWallet_GooglePay*.png`, `AddToWallet_SamsungPay*.png` |
| Dashboard | `Dashboard_Brand_Accelerator.png` |
| ATM locator | SVG icon `Sidemenu/ATMLocator.svg` |
| Transaction history | SVG `Sidemenu/Transaction.svg` |
| Account management | SVG `Sidemenu/MyAccount.svg` |
| Fund access | SVG `Sidemenu/AccessFunds.svg` |
| Rewards | SVG `Sidemenu/Rewards.svg` |
| Help & Support | SVG `Sidemenu/Help&Support.svg` |
| Card reissue | SVG `Reissue.svg` |
| Disclosure documents | SVG `Sidemenu/Disclosure.svg` |
| reCAPTCHA (Google) | `react-google-recaptcha` in `package.json` |
| i18n / localization | `i18next` + `react-i18next` in `package.json` |

### 2.2 Accessibility Testing Capability

| Tool | Usage |
|---|---|
| `@axe-core/cli` | Installed globally in CI; scans live QA pages for WCAG violations |
| Pages tested | `/` (root), `/activation`, `/registration` on `mypaymentvault.qa.onbe.dev` |
| Output | JSON files (`default.json`, `activation.json`, `registration.json`) published as GitHub Actions artifacts |

---

## 3. Key Business Entities

| Entity | Source |
|---|---|
| Affiliate / Program | `mock-server/json/affiliate/GET.json` — `affiliateId`, `affiliateName`, `affiliateSkinName` |
| Card Activation status | `cardActivation/GET.json` — `successResponse.status` |
| Auth settings (card activation) | `postalCode`, `mobilePhone`, `ssn`, `dob`, `noAddtionalAuth`, `puid` flags |
| Country eligibility | `userCountry.userUS`, `userCountry.userCanada` |
| Recipient / Cardholder | Implicit in activation flow |

Known affiliates in mock data: `op` (program `04015253`) and `tmobile` (T-Mobile branded experience with distinct theming).

---

## 4. Business Rules (Inferred from Mock API)

1. Card activation may require one or more identity verification factors depending on `authSettingsDisplay` flags.
2. Country eligibility (`userUS`, `userCanada`) gates certain product features.
3. Affiliate branding drives UI theme (colors, logos, images) — two affiliates observed: `op` (Onbe default) and `tmobile`.
4. reCAPTCHA is required (likely on activation/registration forms) to prevent automated abuse.

---

## 5. Business Flows

### 5.1 Card Activation Flow (Inferred)
```
Cardholder → /activation
  → GET /api/cardActivation → authSettingsDisplay (which factors required)
  → POST /api/cardActivation → activation result
  → Redirect to dashboard on success
```

### 5.2 Accessibility Testing Flow
```
GitHub Actions (workflow_dispatch trigger)
  → npm install
  → npm run build (React build)
  → axe CLI → https://mypaymentvault.qa.onbe.dev/
  → axe CLI → https://mypaymentvault.qa.onbe.dev/activation
  → axe CLI → https://mypaymentvault.qa.onbe.dev/registration
  → Publish JSON reports as workflow artifacts
```

---

## 6. Compliance Relevance

- **WCAG 2.1 / ADA / Section 508**: Axe-core testing directly supports accessibility compliance requirements. The CI pipeline formalizes accessibility regression detection.
- **CCPA / GLBA**: The application collects cardholder identity information during activation (SSN, DOB, postal code flags in mock data). These are high-sensitivity PII fields.
- **PCI DSS**: Card activation flow may touch card numbers; the mock server simulates but does not contain real PANs.

---

## 7. Risks

| Risk | Severity | Detail |
|---|---|---|
| `.env*` files committed to repo | High | `project/.env`, `.env.qa`, `.env.stage`, `.env.prod` are **committed to version control**; they contain reCAPTCHA site key `6LffrKglAAAAAM4Np_mhi_k8h1LHkNxnBFxSyrRK` and API base URLs for all environments |
| reCAPTCHA site key in version control | Medium | Site key `6LffrKglAAAAAM4Np_mhi_k8h1LHkNxnBFxSyrRK` is public-facing by design but should not be committed; the corresponding secret key must never appear |
| Axe workflow only manual (`workflow_dispatch`) | Medium | Accessibility tests are not automatically run on PRs |
| No `.gitignore` for `.env*` files | High | `.env` files should be in `.gitignore` |
| Mock SSN/DOB flags exposed | Low | `authSettingsDisplay.ssn` and `.dob` are present in mock response; if mock is used in screenshots/demos, PII field names are visible |
| XCONTENT_BASE_URL pointing to staging blob storage in prod env | Medium | `project/.env.prod` has `REACT_APP_XCONTENT_BASE_URL` pointing to `staz1recipientappqass` (staging suffix) — cross-environment URL mismatch |
