# 02 Data Architect — embedded-payments-sdk

## Data Architecture Overview

The SDK is a **stateless client-side application**. It does not maintain a database or persistent storage. All data originates from API calls to `embedded-payments-api` and exists only in transient memory (JavaScript heap) during the widget session. The SDK's data architecture concern is primarily about **data flows** and **in-browser data handling** of PCI-sensitive information.

## TypeScript Data Types — Complete Inventory

### `src/widget/types/ApiDTO.ts`

These types represent the request/response contracts with `embedded-payments-api`:

| Interface | Fields | Sensitivity |
|---|---|---|
| `CardDetailsResponse` | `cardNumber: string`, `cvCode: string`, `expiryMonth: string`, `expiryYear: string` | **PCI CHD — Full PAN + CVV** |
| `MaskedCardAndBalanceResponse` | `firstName`, `lastName`, `maskedCardNumber`, `expiryMonth`, `expiryYear`, `balance: number` | PII + masked PAN |
| `ErrorDetail` | `field?`, `issue?` | — |
| `ErrorResponse` | `status`, `message`, `path`, `details?` | — |
| `DisburseResponse` | `status`, `claimCode`, `transactionId`, `message` | — |
| `ModalitiesRequest` | `claimCode: string` | — |
| `ModalitiesInfo` | `modalityId`, `amountIssued`, `fees`, `finalAmount`, `isTermsRequired`, `termsResourceName` | Financial |
| `ModalitiesResponse` | `modalities: ModalitiesInfo[]`, `isGenericTermsRequired`, `genericTermsResourceName` | — |
| `AcceptTermsRequest` | `termsIDs: number[]` | — |
| `Transaction` | `rowId`, `tranDate`, `recipient`, `amount`, `balance`, `type`, `fee`, `previousBalance`, `details`, `offCardRecipient`, `txnStatus` | Financial transaction data |
| `TransactionsResponse` | `availableBalance`, `currentFeeTotal`, `previousFeeTotal`, `ytdFeeTotal`, `transList` | Financial |
| `ContactInfoResponse` | `firstName`, `lastName`, `email`, `phone`, `address1`, `address2`, `city`, `state`, `zipCode`, `country` | **PII — Full cardholder contact** |
| `EnabledWalletsRequest` | `userAgentSystem: string` | Device fingerprint |
| `WalletAssetDetail` | `data: string` (base64 image), `type?` | — |
| `OnDeviceWallet` | `consumerFacingEntityName`, `walletId`, `assetDetails` | — |
| `EnabledWalletsResponse` | `correlationId`, `onDeviceWallets` | — |
| `PushProvisionRequest` | `walletId`, `passthruFromIdiSdk`, `correlationId`, `walletType` | IDI SDK opaque data |
| `PushProvisionResponse` | `correlationId`, `statusCode`, `passthruToIdiSdk`, `statusDescription` | IDI SDK opaque data |

### `src/widget/types/WidgetConfig.ts`

Configuration passed from the partner page to the widget via `postMessage`:

| Field | Purpose |
|---|---|
| `container` | DOM element ID for widget mounting |
| `accessToken` | Partner-issued OTT |
| `theme.accentColor` | Branding colour |
| `theme.mode` | `light` / `dark` |
| `locale` | Language code |
| `devAccessToken` | Dev-mode token (non-production only) |

### `src/widget/types/WidgetState.ts`

In-memory widget state managed by `WidgetStore`:

- Current screen / view
- Disbursements list
- Selected modality
- Card details (PAN, CVV, expiry — **PCI-sensitive in-memory state**)
- Transaction history
- Contact info

### `src/widget/types/PaymentModality.ts`

Enum of modality IDs matching the API: VIRTUAL=100, CARD=200, ACH=300, CHECK=400, PAYPAL=500, EXPRESS_ACH=600.

### `src/widget/types/WidgetScreens.ts`

Enum of widget navigation states (LOADING, DASHBOARD, MODALITY_SELECTION, CLAIMS, etc.)

### `src/widget/types/iFrameEvents.ts`

`IFrameEvents` enum — `postMessage` event type constants:
- `ONBE_WIDGET_READY` — widget SPA has loaded and is ready
- `ONBE_WIDGET_LOAD_FAILED` — widget failed to load (reason + details)
- `ONBE_WIDGET_INIT` — shim sends configuration to widget
- `ONBE_WIDGET_ERROR` — widget error event (propagated to partner page)

## Critical PCI Data Flow in Browser

```
POST /embedded/widget/disbursement-info (via ApiClient, with cookies)
        ↓
Backend decrypts PAN/CVV from StrongBox
        ↓
JSON response: { cardNumber: "4111...", cvCode: "123", ... }
        ↓  (HTTPS only — never cached)
CardDetailsComponent receives CardDetailsResponse
        ↓
Renders PAN / CVV in widget DOM
        ↓  (widget is in sandboxed iFrame)
User views card details
        ↓
User manually copies PAN/CVV (e.g., for online purchase)
```

**Critical security requirements for this flow**:
1. The HTTPS response must have `Cache-Control: no-store, no-cache` to prevent browser caching of PAN/CVV
2. The widget must NOT write PAN/CVV to `localStorage`, `sessionStorage`, IndexedDB, or cookies
3. The widget DOM must clear PAN/CVV from the UI when the user navigates away
4. The iFrame's `sandbox="allow-same-origin"` means the widget JS can read its own cookies — the session cookie containing OAuth material is accessible to widget JS (risk: XSS in widget → token exfiltration)

## `WidgetStore` State Management

`src/widget/store/WidgetStore.ts` — Implements a reactive state store for the widget (likely an observable/event-based pattern without a heavy framework). Holds the complete in-memory state of the widget session, including any fetched card details.

## API Communication

`src/widget/services/ApiClient.ts` — Axios-based HTTP client:
- `baseURL`: dynamically resolved from `window.appConfig.apiUrl` or defaults to `http://localhost:8080/embedded/widget`
- `withCredentials: true` — sends session cookies with every request (required for cookie-auth)
- Dev mode: attaches `X-Dev-Access-Token` header when `VITE_DEV_MODE=true` (bypasses cookie auth for local development)
