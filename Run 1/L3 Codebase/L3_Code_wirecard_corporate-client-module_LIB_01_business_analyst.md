# Business Analyst — wirecard_corporate-client-module_LIB

## Business Purpose
`corporate-client-module` (CCM) is a **Gen-2 corporate client lifecycle management microservice** for the Wirecard/Northlane issuing platform. It manages the onboarding, maintenance, and deactivation of **corporate clients** — businesses that operate prepaid card programs. It also manages their associated virtual clients, card programs, card issuance, fund loading/unloading, and brand assignments.

## Capabilities
1. **Corporate Client CRUD**: Create, read, update, and status-change operations for corporate clients (`CORP_CLIENT` entity). Corporate clients have legal entities, billing contacts, addresses, custom fields, and brand assignments.
2. **Virtual Client Management**: Create, retrieve, update, and search virtual clients (`VirtualClientCreation`, `VirtualClientEdition`, `VirtualClientSearch`). Virtual clients represent sub-entities under a corporate client.
3. **Card Management (via CMM client)**: Create restricted prepaid cards (`CreateRestrictedCardRequest`), create products (`CreateProduct`), load/unload funds (`LoadUnloadRequest`), close card accounts.
4. **Brand Management (via Brand Server client)**: Retrieve brand lists, card programs, and payment card details for authorized brands.
5. **Authorization/Access Control**: Brand-aware OAuth2 authentication — users are scoped to specific brands; operations are authorised based on brand permissions (`@PreAuthorize("hasRole(...) and hasPermission(#client.brands, 'brand')")`).
6. **Corporate Client History**: Full audit log of create/update/terminate actions (`CORP_CLIENT_LOG`).
7. **Account Fund Transfer (A2A)**: Account-to-account fund transfers via CCP client.
8. **Technical User Management**: Manages technical service users via ISS Auth Server client.
9. **Event Consumption**: Listens to `AccountStateEvent` from EventHub for real-time account state updates.

## Entities / Domain Objects
| Entity | Table | Description |
|---|---|---|
| `CorporateClient` | `CORP_CLIENT` | Corporate client master record |
| `CORP_ADDRESS` | `CORP_ADDRESS` | Mailing/billing addresses |
| `CORP_CONTACT` | `CORP_CONTACT` | Contact persons (name, phone, email, DOB) |
| `CORP_WIRECARD_CONTACT` | `CORP_WIRECARD_CONTACT` | Wirecard account manager contacts |
| `LEGAL_ENTITY` | `LEGAL_ENTITY` | Legal entity details (VAT ID, commercial register) |
| `CORP_CLIENT_BRAND` | `CORP_CLIENT_BRAND` | Corporate client to brand mapping |
| `CORP_CLIENT_CUSTOM_FIELD` | `CORP_CLIENT_CUSTOM_FIELD` | Flexible attributes (key-value) |
| `CORP_CLIENT_LOG` | `CORP_CLIENT_LOG` | History/audit log |
| `CARD` | `CARD` | Issued card records (VCA, account ref, card ref) |
| `CRM_COMMENTS_CORPORATE` | `CRM_COMMENTS_CORPORATE` | CRM comment references for history entries |
| `VirtualClient` / `VirtualClientAccount` | (via CCP API) | Virtual client accounts |
| `EventHubEvent` | (from shared pattern) | EventHub message tracking |

## Business Rules
1. A corporate client must have at least one Wirecard Account Manager contact (`CorporateClientContactsWdpAccountManagerMissing` error).
2. A corporate client must have at least one Wirecard Sales Person contact.
3. `SHORT_NAME` and `CORP_CLIENT_KEY` must be unique across all corporate clients.
4. Brand authorisation is enforced at API level: a user can only create/update clients for brands they are authorised for (`@PreAuthorize hasPermission(#client.brands, 'brand')`).
5. `DATE_OF_BIRTH` is stored for contacts — subject to PII protection requirements.
6. `T_PIN` is stored for contacts — sensitive authentication data requiring protection.
7. `INDEX_KEY` on `CORP_CONTACT` — unique per client (ensures no duplicate contact types).
8. Corporate clients have a status lifecycle (via `StatusType` enum — `CREATE`, `UPDATE`, `TERMINATE` action types and `SUCCESS`/`FAIL` result types).

## Flows
1. **Corporate client creation**: `POST /callcenter-api/corporate-clients` → validate contacts → generate `CORP_CLIENT_KEY` (Oracle sequence) → persist `CORP_CLIENT` + related entities → log to `CORP_CLIENT_LOG` → optionally create technical user via ISS Auth Server.
2. **Card creation**: `POST /callcenter-api/corporate-clients/{key}/cards` → CCP reserve money → CMM create card → persist `CARD` record.
3. **Account state event**: EventHub consumer receives `AccountStateEvent` → updates virtual client account state.
4. **Brand-aware search**: `POST /callcenter-api/corporate-clients/searches` → returns clients filtered by authorised brands.

## Compliance Relevance
- **PCI DSS Requirement 7 (Restrict Access by Need-to-Know)**: Brand-aware authorisation enforces least-privilege access to corporate client data.
- **PCI DSS Requirement 3**: `T_PIN` stored in `CORP_CONTACT` — if this is a card PIN or security PIN, it is SAD (Sensitive Authentication Data) and must not be stored post-authorization. This is a critical compliance finding.
- **GDPR / CCPA**: `DATE_OF_BIRTH`, contact names, email addresses, and phone numbers in `CORP_CONTACT` are PII.
- **GLBA**: Corporate client financial data and fund transfer operations.
- **SOC 2**: `CORP_CLIENT_LOG` supports change-management audit trail requirements.

## Risks
1. **`T_PIN` in `CORP_CONTACT`**: If this column stores a card or security PIN, it is Sensitive Authentication Data (SAD) prohibited from storage post-authorization by PCI DSS Req 3.2. Requires immediate clarification.
2. **DATE_OF_BIRTH stored for contacts**: PII requiring data minimisation review under GDPR.
3. **Hardcoded QA credentials in `application.yml`**: `ccp.client.password: aaaa1111`, `cmm.client.password: aaaa1111`, `iss-auth.client.password: aaaa1111`.
4. **No fund transfer rollback**: If a load/unload operation partially fails (CCP succeeds, card issuance fails), no compensating transaction is visible in the codebase.
