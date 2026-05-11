# Data Architect Report — demoaccessibilitytesting

## 1. Data Stores

The application itself has **no persistent data stores** — it is a client-side React SPA that consumes backend APIs. The mock server (`mock-server/server-mocker.js`) serves static JSON from `mock-server/json/` for local development.

| Store | Type | Purpose |
|---|---|---|
| `mock-server/json/` | Static JSON files on disk | Local development API mock |
| Browser localStorage/sessionStorage | Client-side | Likely used for session state (inferred from Redux Toolkit in package.json) |
| Azure Blob Storage | Cloud | xContent (images, PDFs) at `staz1recipientappqass.blob.core.windows.net` |

---

## 2. Schema — Mock API Responses

### 2.1 `GET /api/cardActivation`
```json
{
  "successResponse": {
    "authSettingsDisplay": {
      "postalCode": "N|Y",
      "mobilePhone": "N|Y",
      "ssn": "N|Y",
      "dob": "N|Y",
      "noAddtionalAuth": "N|Y",
      "puid": "N|Y"
    },
    "userCountry": {
      "userUS": "Y|N",
      "userCanada": "Y|N"
    },
    "status": 0
  }
}
```

### 2.2 `POST /api/cardActivation`
Same structure — represents the activation result.

### 2.3 `GET /api/affiliate`
```json
{
  "clientCustomInfo": [
    {
      "affiliateName": "string",
      "affiliateId": "string",
      "affiliateSkinName": "string",
      "accessLevel": "string"
    }
  ]
}
```

---

## 3. Sensitive Data Inventory

| Data Element | Location | Classification | Risk |
|---|---|---|---|
| reCAPTCHA site key | `project/.env` line 3, `.env.qa:3`, `.env.stage:3`, `.env.prod:3` — all identical value | Public client key | Committed to repo; low individual risk but signals poor secrets hygiene |
| API base URLs (all envs) | `.env*` files | Internal infrastructure URLs | Committed to repo; exposes service topology |
| `ssn` field name in mock auth flags | `cardActivation/GET.json:7` | PII field indicator | Not a real SSN value but indicates SSN is collected during activation |
| `dob` field name in mock auth flags | `cardActivation/GET.json:8` | PII field indicator | As above |
| Affiliate program ID `04015253` | `affiliate/GET.json:4` | Internal program identifier | Low sensitivity |
| Azure Blob Storage URL | All `.env*` files — `REACT_APP_XCONTENT_BASE_URL` | Infrastructure endpoint | Committed to repo |

**No real PANs, SSNs, CVVs, or DOBs were found committed in this repository.**

---

## 4. Encryption

| Mechanism | Status |
|---|---|
| HTTPS to backend API (`REACT_APP_BASE_URL`) | Enforced by URL scheme (`https://`) |
| HTTPS to Azure Blob Storage | Enforced by URL scheme (`https://`) |
| Client-side data encryption | Not observed |
| reCAPTCHA (anti-bot) | Present in package.json; protects activation/registration forms |

---

## 5. Data Flow

```
Browser (React SPA)
  │
  ├─ GET/POST https://external.{env}.onbe.dev/mypaymentvaultapi/*
  │    [card activation, account data — production backend API]
  │
  ├─ GET https://staz1recipientappqass.blob.core.windows.net/data/xContent/recipient/*
  │    [static content: PDFs, images, xContent]
  │
  └─ Local development only:
       GET/POST http://localhost:8080/api/*
         [mock-server/server-mocker.js serving static JSON]
```

---

## 6. Data Quality

- **Mock data completeness**: Mock server covers `cardActivation` (GET/POST) and `affiliate` (GET) only; actual application likely calls additional endpoints not mocked.
- **xContent URL inconsistency**: Prod `.env` points `REACT_APP_XCONTENT_BASE_URL` to `staz1recipientappqass` (staging suffix in hostname), suggesting the prod env file was copied from staging without updating the blob storage URL.
- **Affiliate mock data**: Only two affiliates (`op`, `tmobile`) in mock; production likely has many more.

---

## 7. Compliance Gaps

| Gap | Standard | Detail |
|---|---|---|
| `.env*` files committed to git | GLBA / CCPA / General secrets hygiene | Environment files with API URLs and reCAPTCHA key should be in `.gitignore` |
| No `Content-Security-Policy` header config observed | PCI DSS Req 6.4.3 | SPA should define a strict CSP; not visible in React config |
| SSN/DOB collected in activation flow | GLBA / CCPA Req | Must ensure these fields are never logged client-side and are transmitted over TLS only |
| xContent blob URL environment mismatch | Data integrity | Prod env pointing to staging blob storage could serve wrong content to production users |
| No explicit data retention policy for axe-core scan reports | GDPR Art 5 | Accessibility scan JSON reports published as GitHub artifacts may contain page content |
