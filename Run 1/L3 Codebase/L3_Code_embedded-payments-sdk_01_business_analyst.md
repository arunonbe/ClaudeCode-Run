# 01 Business Analyst — embedded-payments-sdk

## Overview

`embedded-payments-sdk` is a **TypeScript / JavaScript client SDK** for the Onbe Embedded Payments product. It provides the browser-side components that partner companies embed in their web applications to present the Onbe payment widget to end-users (cardholders). The SDK is a private npm package (`"private": true`, `package.json` line 3) built with **Vite 5** and **TypeScript 5.9**, targeting modern browsers. Version: `0.0.0`.

## Business Purpose

The SDK is the partner-facing integration layer of the Embedded Payments product. Partner companies include the SDK's compiled JavaScript output on their web pages to:

1. **Render the Onbe payment widget** in an iFrame on the partner's page
2. **Handle authentication flow** — submitting the partner-issued access token to load the widget SPA securely
3. **Support digital wallet provisioning** — presenting Apple Pay / Google Pay options to cardholders
4. **Provide a sandbox environment** — allowing partners to test integrations without affecting production

## SDK Architecture — Three Deliverables

The SDK compiles into three distinct artefacts, each with its own Vite build config:

### 1. Widget (`vite.config.widget.ts`)
The main widget SPA (Single Page Application) rendered inside the iFrame. This is the cardholder-facing UI that displays disbursements, card details, transaction history, and digital wallet options.

### 2. Shim (`vite.config.shim.ts`)
The lightweight JavaScript snippet (`shim.ts`) that partner companies add to their web pages. The shim:
- Creates and manages the iFrame that hosts the widget
- Handles the `postMessage` communication protocol between the partner page and the widget
- Submits the partner's access token to `POST /embedded/shim/load-spa` via a hidden form POST (to avoid the token appearing in URL parameters)
- Renders loading states and error states in the container element
- Provides a popup fallback for environments where iFrames are blocked

### 3. Sandbox (`vite.config.sandbox.ts`)
A development/testing environment that simulates a partner portal. Two sandbox portals exist:
- `src/sandbox/health-portal.ts` — simulates a healthcare payment portal scenario
- `src/sandbox/tmobile-portal.ts` — simulates a T-Mobile partner portal scenario

## Partner Integration Pattern

```html
<!-- Partner's HTML page -->
<div id="payment-widget-container" style="width:500px;height:600px;"></div>

<script src="https://cdn.onbe.com/embedded/shim.js"></script>
<script>
  OnbeWidget.init({
    container: 'payment-widget-container',
    accessToken: '{server-side-generated-OTT}',
    theme: {
      accentColor: '#0057b8',
      mode: 'light'
    }
  });
</script>
```

The `accessToken` must be generated server-side by the partner calling `POST /embedded/client/authenticate`.

## Widget User Interface Components

The widget SPA is built with Web Components / TypeScript (no React or Angular framework dependency). Components:

| Component | Purpose |
|---|---|
| `HeaderComponent` | Widget header with Onbe branding and title |
| `FooterComponent` | Footer with legal links |
| `BalanceCardComponent` | Displays cardholder's current balance |
| `CardDetailsComponent` | Shows card number, expiry, CVV (PCI-sensitive display) |
| `TransactionsComponent` | Transaction history list |
| `TransactionModalComponent` | Transaction detail overlay |
| `DateFilterComponent` | Date range filter for transactions |
| `DateSelectorModalView` | Date picker modal |
| `ErrorResolutionComponent` | User-friendly error display with resolution guidance |
| `ErrorTooltipComponent` | Inline error tooltips |
| `ToastComponent` | Transient notification messages |
| `WebWalletComponent` | Digital wallet (Apple/Google Pay) provisioning UI |

## Widget Views (Navigation States)

| View | Purpose |
|---|---|
| `LoadingView` | Initial loading spinner |
| `DashboardView` | Main cardholder dashboard — balance + disbursement list |
| `ModalitySelectionView` | Disbursement method selection (virtual/card/ACH/check/PayPal) |
| `ClaimsView` | Claim history or active claims |
| `ContactInfoView` | Cardholder contact information display |
| `ErrorView` | Error state |
| `TermsModalView` | Terms and conditions acceptance UI |
| `DateSelectorModalView` | Date range selection for transaction filter |

## Payment Capabilities in the SDK

The SDK exposes the following payment capabilities to the cardholder through the widget UI:

1. **View pending disbursements** — see available funds to claim
2. **Select disbursement method** — choose between virtual card, physical card, ACH, check, PayPal, or Express ACH
3. **Accept terms and conditions** — per modality, before disbursement
4. **Execute disbursement** — claim the funds to the selected method
5. **View card details** — see PAN, CVV, expiry for a virtual card (PCI-sensitive)
6. **View transaction history** — account activity with balance summary
7. **View contact information** — verify delivery address
8. **Add to digital wallet** — provision to Apple Pay / Google Pay via push provisioning

## Regulatory and Security Relevance

- **PCI DSS**: The `CardDetailsComponent` displays a full PAN and CVV. PCI DSS Req 3.5.1 and Req 4 apply to the transmission and display of this data. The data must never be stored in `localStorage`, `sessionStorage`, or cookies.
- **GDPR/CCPA**: The `ContactInfoView` displays PII (name, address, email). This data must not be cached or persisted client-side.
- **Domain isolation**: The iFrame `sandbox` attribute (`allow-scripts allow-forms allow-popups allow-same-origin`) restricts what the widget can do within the partner's page.
