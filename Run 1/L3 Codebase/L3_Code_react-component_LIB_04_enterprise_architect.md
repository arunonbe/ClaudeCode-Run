# Enterprise Architect — react-component_LIB

## Platform Generation
**Gen-3 front-end** — React 18, React Bootstrap 5, React Router 6, modern JavaScript (ES2022+). However, the project management approach (committed `dist/`, no registry publish, CRA test runner) reflects Gen-2 maturity in delivery practices.

## Business Domain
**Shared UI / Design System** — Cross-cutting front-end capability consumed by all Onbe cardholder-facing and client-facing web applications.

## Role in the Architecture
This repository is Onbe's **internal React component design system**. It:
- Provides branded, themeable UI components for all Onbe web products
- Enforces consistent visual design and interaction patterns
- Includes composite components for key payment flows (login, activation, registration, dashboard)
- Is consumed by the One E-commerce Platform (OEP), MyPaymentAdmin, MyPaymentVault, ClientZone, and similar applications

## Component Taxonomy

```
Atomic Components (27)
  Form inputs: TextboxComponent, SelectComponent, CheckboxComponent,
               RadiobuttonComponent, ToggleComponent, DateRangeComponent,
               AsyncTypeaheadComponent, TypeaheadComponent, DatalistComponent
  Display: LabelComponent, TextComponent, ImageComponent, ChipComponent
  Navigation: NavComponent, SidebarComponent, SidedrawerComponent,
              OffcanvasNavbarComponent, Menudropdown, DropdownComponent
  Actions: ButtonComponent, ButtonGroupComponent, AnchorComponent, LinkComponent
  Feedback: LoaderComponent, ProgressbarComponent, CircularProgressbarComponent,
            NotificationPanelComponent, PopoverComponent, TooltipComponent
  Layout: CardComponent, AccordionComponent, CarouselComponent,
          ModalComponent, ModalComponentV2, InfinitescrollwrapperComponent
  Utility: Context, Wrapper

Composite Components (8)
  LoginSection, ActivationboxComponent, ActivationcontentComponent,
  CommonHeader, DashboardSidebarComponent, FooterComponent,
  FormReaderComponent, PamphletComponent
```

## Integration Patterns

| Pattern | Implementation |
|---|---|
| Peer dependency distribution | React, React Bootstrap, React DOM as peerDependencies — consumers must provide compatible versions |
| Babel transpile distribution | `dist/` contains CommonJS-transpiled components — imported as `import X from 'react-bootstrap-onbe-library'` |
| Client theming | `clientColor.json` overrides CSS variables at runtime |
| i18n support | `i18next` + `react-i18next` for multi-language rendering |

## Key Consuming Applications

Based on example app pages and brand assets:
- OEP (One E-commerce Platform) — `OEP.js`, `OEPNew.js`, `Oeptokendashboard.js`
- MyPaymentVault (Northlane branding assets visible)
- MyPaymentAdmin
- ClientZone / Activation Portal
- T-Mobile program (`tmobile.*` assets)

## Strategic Status
**Active but immature delivery practices.** The component library is functionally active and broadly used across Onbe applications. However:
- Version `0.0.2` — no formal versioning/release process
- `dist/` committed to VCS — no registry publish pipeline
- CRA (Create React App) is deprecated — build tooling needs migration to Vite or Next.js
- No Storybook or component documentation system

**Recommended investment:** Establish a proper package registry publication (npm private registry or GitHub Packages), implement Storybook for component documentation, and migrate from CRA to Vite.

## Risks to Enterprise Architecture

| Risk | Impact |
|---|---|
| No versioned package releases — consuming apps may pull HEAD unpredictably | High — breaking changes deployed to consumers silently |
| CRA deprecated — `npm test` will break as CRA dependencies become unsupported | High — need to migrate to Vite or another test runner |
| Login form validation commented out | High — security implication for consuming applications |
| `dist/` in VCS creates synchronisation risk | Medium — consumers may use stale pre-built artefacts |
| No component documentation (Storybook) | Medium — developer adoption friction |
| T-Mobile and Northlane brand assets suggest multi-tenant design — isolation is CSS-only | Medium — brand asset separation at build time not enforced |
