# Business Analyst — oneplatform-ui_LIB

## Business Purpose
A shared frontend UI library that provides the compiled, optimized static web assets (JavaScript, CSS, HTML templates, fonts) for the OnePlatform cardholder self-service web application — specifically the mobile-responsive web experience served at `https://login.northlane.com/m`. This library is a Maven artifact (`oneplatform-mobile-ui`) consumed as a dependency by the server-side web application (`oneplatform_WAPP` or similar WAR deployers).

## Capabilities
- **Shared CSS**: Aggregated and minified CSS for all cardholder-facing screens including login, dashboard, account details, access funds, disclosures and fees, FAQs, forgot password/username, global deposits, branding, menu, and contact us.
- **Shared JavaScript**: RequireJS-based module system (`r.js` optimizer); Backbone.js + Underscore.js application framework; shared utility and component modules.
- **HTML Templates**: Aggregated Handlebars/HTML templates compiled to `cpmain.html`.
- **Custom Fonts**: North Lane / Onbe branded fonts — Interstate-Regular, Interstate-ExtraLight, OCRAStd (card number display), Futura.
- **Mobile web support**: `<meta name="mobile-web-app-capable">`, responsive viewport meta tag, Apple touch icon.
- **Flash component**: `rsa_fso.swf` — RSA fraud/session object (legacy Flash).
- **Module namespace**: `cp` module namespace (`cp_Web.module = 'cp'`); `datasource` defaults to `MOCKJSON` in config.js (mock data mode).

## Key Entities
- **Program/Affiliate Screens**: Login, dashboard, access funds, account details, disclosures, FAQs, contact us, global deposits, edit profile, menu.
- **UI Components**: CSS components named with `cp` prefix (e.g., `cpDashboard.css`, `cpAccessFunds.css`, `cpBranding.css`).
- **Font Assets**: `interstateregular.ttf`, `Interstate-ExtraLight.otf`, `OCRAStd.otf`, `Futura.ttc`.

## Business Rules
- The library is a build-time artifact; no runtime business logic is enforced here.
- `config.js` defaults `datasource` to `MOCKJSON` — this must be overridden at deployment to `JSON` for production use; leaving it as `MOCKJSON` would cause the UI to use mock data instead of the real API.
- `debug: true` in `config.js` — should be `false` in production.
- The `cpBranding.css` file is excluded from CSS aggregation (it is affiliate-specific and overridden per skin).

## Key Flows
1. **Build-time**: Maven `package` phase runs `yuicompressor-maven-plugin` to minify and aggregate CSS into `cpmain.css`, and HTML templates into `cpmain.html`; then `requirejs-maven-plugin` runs `r.js` optimizer on JavaScript modules.
2. **Runtime**: Static assets are served by the WAR deployer; browser loads `cpmain.css` and optimized JS modules; `app.js` initializes the Backbone.js application using `cpEnv_Web.module` settings.

## Compliance Relevance
- **Cardholder-facing UI**: Directly renders the interface through which cardholders enter authentication credentials, view card details, and initiate payments — PCI DSS SAQ A-EP scope (browser-to-server, all payment-relevant pages).
- **Clickjacking prevention**: `<html class='antiClickJack'>` CSS class set in `index.html` (lines 1-2); JavaScript clickjack protection implied. PCI DSS Req 6.4.3 (client-side script integrity) and Req 6.4.4 (frame-ancestors) should be verified.
- **RSA Flash component** (`rsa_fso.swf`): Flash is end-of-life (EOL December 2020); browser support has been removed. This file should be considered a dead asset.
- **Font files**: Custom fonts served from the same domain; no third-party CDN font loading visible, which is a positive security indicator (reduces CSP complexity).

## Risks
- `config.js` `datasource: MOCKJSON` and `debug: true` committed to source — if these values are not overridden at build/deploy time, production UI will use mock data.
- `rsa_fso.swf` Flash asset present — Flash is fully unsupported in all modern browsers; should be removed.
- SCM URL in `pom.xml` references `gitlab.com/northlane/...` — indicates origin under the Northlane brand; should be updated if repo was migrated to Onbe GitLab.
- Version is `1.0.31-SNAPSHOT` — SNAPSHOT artifact in a production UI library creates reproducibility risk.
- Parent POM is `com.citi.prepaid:prepaid-parent:3` — very old parent; may carry outdated plugin versions.
