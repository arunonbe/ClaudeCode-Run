# Business Analyst Report — mpv (My Payment Vault)

## 1. Service Identity and Business Purpose

`mpv` is the **cardholder-facing self-service portal** — the consumer-facing web application branded as "My Payment Vault" (MPV). It is the primary digital touchpoint for Onbe's disbursement and prepaid card recipients, allowing them to manage their payment instruments, choose how they receive funds, and transact across multiple rails. Based on the mock data structure, MPV is a NexPay Gen-3 front-end that aggregates capabilities from multiple backend services.

The portal supports the full cardholder lifecycle from initial claim code entry and registration through ongoing account self-service. The breadth of the mock data directories reveals the complete feature set:

| Feature Domain | Mock Data Directory | Business Capability |
|---|---|---|
| Claim code entry | `claimCode/` | Claimable Choice: recipient enters a claim code to access their funds |
| Payment selection | `choicePage/` | Multi-rail payment selection (virtual card, push-to-card, ACH, PayPal, etc.) |
| Registration | `registration/` | New account creation linked to a claim code |
| Login | `login/`, `virtualLogin/` | Authentication (standard and virtual/tokenized) |
| Dashboard | `dashboard/` | Account overview: card details, transaction history, unclaimed payments |
| Card activation | `cardActivation/` | Activate a newly issued prepaid card |
| Card dashboard | `cardDashboard/` | Prepaid card management (virtual card display with full PAN) |
| Bank transfer | `BankTransfer/` | ACH bank transfer setup and management |
| FX transfer | `FXTransfer/` | International wire/FX transfer |
| Push to debit | `pushToDebit/` | Push-to-card (real-time debit card funding) |
| PayPal | `Paypal/` | PayPal payout enrollment and management |
| Venmo | `Venmo/` | Venmo payout enrollment |
| Gift card | `GiftCard/` | Gift card purchase |
| Request check | `requestCheck/` | Paper check request |
| Web-to-wallet | `webtowallet/` | Web-based digital wallet loading |
| Profile | `profile/` | Contact info, password change, PIN management |
| Transactions | `transaction/` | Transaction history |
| Disclosures | `Disclosures/` | Regulatory disclosure display |
| Branding | `branding/` | Affiliate-specific branding/vanity configuration |
| Contact | `contact/` | Support contact submission |

## 2. Multi-Rail Payment Disbursement Model

The choice page mock data (`choicePage/choiceOnload.json`, `choiceAchBankTransfer.json`, `returningUserChoiceSelection.json`) reveals the Claimable Choice business model: recipients receive a claim code (from an Onbe client/payer), enter the code in MPV, and select their preferred disbursement method from the available rails. The supported rails observed in mock data include:

1. Virtual prepaid card (Onbe/NexPay issued)
2. Physical prepaid card
3. ACH bank transfer
4. Push-to-card (debit card)
5. PayPal
6. Venmo
7. Gift card
8. Paper check
9. International wire (FX transfer)
10. Web-to-wallet / digital wallets (Apple Pay, Google Pay, Samsung Pay per `dashboard/dashboardDetails.json` lines 30-35)

## 3. PII and Sensitive Data Handling Observations

From `mock-data/dashboard/dashboardDetails.json`:
- Line 86: `"cardNumber": "5445446585725838"` — a full 16-digit card number in mock data. While this is mock/test data, its presence in the repository is a PCI DSS concern. Mock data should use masked values (e.g., `4111110000001111` test BINs with explicit labeling as test data).
- Line 87: `"cvv": 77` — CVV in mock data. This should never appear, even in test data, per PCI DSS Requirement 3.3 (prohibition on storing SAD after authorization).
- Line 88: `"expirationDate": "05/2026"` — expiry date in mock data.
- Lines 97-113: Unclaimed transaction list with `verificationCode` values (e.g., `"UVJ9AB93AP9F4NVW"`) and `echeckId` UUIDs.

## 4. Consumer Personas

1. **New recipient (first visit)**: Arrives via a claim code link; goes through claim code validation → registration → payment selection flow.
2. **Returning cardholder**: Logs in directly; manages card, views transactions, changes payment preferences.
3. **Virtual card holder**: Views virtual card details (PAN, CVV, expiry) for online purchases.
4. **International recipient**: Uses FX transfer for cross-border payouts.

## 5. Regulatory Business Rules

- **Disclosures**: The `Disclosures/getproperties.json` mock confirms a disclosure display requirement before certain actions.
- **Terms & Conditions**: `dashboardDetails.json` line 12 in `login.json` (`"termsAndConditionsAcknowledged": "Y"`) indicates T&C acknowledgment is tracked per user.
- **Language support**: `commonData/copyTag_fr_US.json` and `copyTag_sp_US.json` confirm French and Spanish locale support, required for certain state/federal language access regulations.
