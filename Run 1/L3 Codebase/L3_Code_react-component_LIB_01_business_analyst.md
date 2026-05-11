# Business Analyst — react-component_LIB

## Business Purpose
A **shared React component library** that provides Onbe's design system and reusable UI building blocks for all cardholder-facing and client-facing web applications. Built on React Bootstrap, it standardises the visual language, interaction patterns, and accessibility across Onbe's web products (activation portals, payment dashboards, registration flows, cardholder self-service).

## Capabilities

### Atomic / Reusable Components (`src/Components/ReusableComponent/`)

| Component | Description |
|---|---|
| `ButtonComponent` | Branded button with custom theming (hover colours, custom CSS prefix `onbe-button`) |
| `TextboxComponent` | Form input with label, validation state, icon support |
| `TextareaComponent` | Multi-line text input |
| `SelectComponent` | Dropdown select |
| `CheckboxComponent` | Checkbox with label |
| `RadiobuttonComponent` | Radio button group |
| `ToggleComponent` | Toggle switch |
| `ToggleMessageComponent` | Toggle with associated message |
| `DropdownComponent` | Dropdown menu |
| `Menudropdown` | Navigation dropdown |
| `ModalComponent` / `ModalComponentV2` | Modal dialogs |
| `CardComponent` | Content card |
| `TableComponent` | Data table |
| `NavComponent` | Navigation bar |
| `SidebarComponent` | Side navigation |
| `SidedrawerComponent` | Slide-out drawer |
| `OffcanvasNavbarComponent` | Mobile navigation |
| `LabelComponent` / `InformationLabelComponent` | Text labels |
| `TextComponent` | Styled text blocks |
| `AnchorComponent` / `LinkComponent` | Hyperlinks |
| `ImageComponent` | Image wrapper |
| `LoaderComponent` | Loading spinner |
| `ProgressbarComponent` / `CircularProgressbarComponent` | Progress indicators |
| `NotificationPanelComponent` | Notification display |
| `PopoverComponent` | Tooltip/popover |
| `TooltipComponent` | Hover tooltip |
| `DateRangeComponent` | Date range picker |
| `AccordionComponent` | Collapsible sections |
| `CarouselComponent` | Image carousel |
| `ChipComponent` | Tag/chip display |
| `DatalistComponent` | Datalist input |
| `EditableLabelComponent` | Inline editable label |
| `AsyncTypeaheadComponent` / `TypeaheadComponent` | Typeahead search inputs |
| `InfinitescrollwrapperComponent` | Infinite scroll wrapper |
| `SubPamphletComponent` | Pamphlet sub-content |
| `Context` | React context provider |
| `Wrapper` | Layout wrapper |

### Composite Components (`src/Components/CompositeReusableComponent/`)

| Component | Description |
|---|---|
| `LoginSection` | Full login form: username/password, Activate Card, Login with Card, Redeem Code, Register Account |
| `ActivationboxComponent` | Card activation container |
| `ActivationcontentComponent` | Activation content display |
| `CommonHeader` | Shared page header |
| `DashboardSidebarComponent` | Dashboard navigation sidebar |
| `FooterComponent` | Page footer |
| `FormReaderComponent` | Dynamic form reader |
| `PamphletComponent` | Marketing/informational pamphlet |

### Example Application (`example/src/Pages/`)

A demonstration application showing library usage across:
- Activation flow (`ActivationComponent.js`)
- Dashboard (`DashboardComponent.js`, `OepDashboardComponent.js`)
- Registration (`RegistrationComponent.js`)
- Transaction history (`TransactionComponent.js`)
- Login (`LoginComponent.js`)
- FX Transfer (`FXTransfer.js`)
- Token dashboard (`Oeptokendashboard.js`)
- OEP (One E-commerce Platform) (`OEP.js`, `OEPNew.js`)

## Key Business Entities

| Entity | Component Reference | Description |
|---|---|---|
| Cardholder | `LoginSection`, `ActivationboxComponent`, `RegistrationComponent` | Card holder self-service identity |
| Card | Dashboard images, activation flow components | Prepaid card representation |
| Transaction | `TransactionComponent.js` | Transaction history display |
| Program/Brand | `clientColor.json`, T-Mobile branding assets | Per-client theming |

## Business Rules
1. Component theming supports per-client customisation via `clientColor.json` and CSS variables.
2. Login validation enforces minimum 8-character password (client-side only — `isValidPassword`).
3. Username validation enforces alphanumeric + `_.-` pattern (`^[a-zA-Z0-9_.-]*$`).
4. Login validation code is partially commented out (`validate()` function has commented-out required-field checks) — login form can be submitted without credentials.
5. Button component supports custom `custom-attr-button` data attribute for accessibility/testing hooks.
6. All components are peer-dependent on React 18.2 and React Bootstrap 2.7.2.

## Compliance Relevance

| Standard | Relevance |
|---|---|
| PCI DSS Req 6.2 | UI components render payment data (card balances, transaction history) — secure coding practices required |
| WCAG / Accessibility | `aria-controls`, `aria-expanded`, `aria-label` attributes present on components — accessibility partially implemented |
| CCPA / GDPR | Registration and login components handle PII collection — consent and privacy notice must be rendered |

## Business Risks

| Risk | Severity | Notes |
|---|---|---|
| Login validation is commented out — form submittable with empty credentials | High | `LoginSection.validate()` always returns `true` (all checks commented out) |
| No server-side authentication logic — library is pure UI | Low (by design) | Authentication must be implemented by consuming applications |
| `clientColor.json` in public directory — client theming exposed to browser | Low | Not sensitive, by design |
| Version `0.0.2` — early stage; API stability not guaranteed | Medium | Consuming applications must anticipate breaking changes |
| T-Mobile branded assets in example app suggest use with specific clients | Low | Brand assets must be licensed |
