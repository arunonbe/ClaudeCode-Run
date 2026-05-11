# Solution Architect — react-component_LIB

## Technical Architecture

```
react-component_LIB/
├── src/
│   ├── Components/
│   │   ├── ReusableComponent/     -- 27 atomic components (JS, PropTypes)
│   │   └── CompositeReusableComponent/ -- 8 composite components
│   ├── index.js                   -- Library entry point (exports all components)
│   └── stylesheet/                -- Library CSS (generic.css, Library.css, customizedComponent.css)
├── dist/                          -- Pre-built output (committed to VCS)
├── example/
│   ├── src/
│   │   ├── Pages/                 -- Demo application pages
│   │   ├── assests/               -- Static demo data
│   │   └── stylesheet/            -- Demo app styles
│   ├── public/                    -- Static assets (images, fonts, client config)
│   └── webpack.config.js          -- Example app bundler config
├── package.json                   -- Library manifest
├── webpack.config.js              -- Library bundler config
├── .babelrc                       -- Root Babel config
└── .github/workflows/codeql.yml   -- Security scanning
```

### Build Pipeline
```
src/ (JSX source)
  --> Babel (npm run build)
      @babel/preset-env, @babel/preset-react
      --> dist/ (CommonJS JS files, copied CSS)

src/ + public/ (full app bundle)
  --> Webpack (npm run bundle)
      webpack.config.js with Node polyfills
      --> dist/main.js (bundled)
```

## API Surface (Component Props)

The public API is the set of exported components and their PropTypes. Key interfaces:

### `ButtonComponent`
```
Props: imagefirst, trigger, onClick, type, className, style,
       buttoncolor, customtheme, hoverbgcolor, hovercolor, color,
       buttonrole, size, href, disabled, autoFocus, ariacontrols,
       ariaexpanded, name, children, custom-attr-button, usagetype
```

### `TextboxComponent` (inferred from LoginSection usage)
```
Props: controlidfield, namefield, typefield, isinvalidfield, isValid,
       placeholderfield, ariadecribedbyfield, autocompletefield,
       handleChangefield, onBlurfield, errormessagefield, requiredfield,
       custom-attr-textbox, valuesfield, showinfoicon, oniconclick,
       iconarialabel, textboxlabelfield
```

### `LoginSection` (composite)
```
Props: (accepts configuration props for authentication callbacks)
Internal state: form{}, errors{}, errUsername{}, errPassword{},
                isValidUser, isValidPasswords, cardnumber
Emits: navigate('/Dashboard'), navigate('/Activation'), navigate('/Registration')
```

## Security Posture

### Authentication
No authentication. This is a pure UI library; authentication is the consuming application's responsibility.

### Input Validation
- Username: `^[a-zA-Z0-9_.-]*$` regex applied on blur (client-side only)
- Password: minimum 8 characters (client-side only)
- **Critical:** `LoginSection.validate()` always returns `true` — all validation logic is commented out

```javascript
// LoginSection.js:57-77
const validate =(form)=>{
    let isValid = true;
    //  if(!form["_login-username"]){   // <-- COMMENTED OUT
    //     ...
    // }
    // if(!form["_login-password"]){   // <-- COMMENTED OUT
    //     ...
    // }
    return isValid;  // Always returns true
}
```

### XSS Prevention
- Components use React's JSX (auto-escapes string values)
- `dangerouslySetInnerHTML` not observed in read components
- `href={props.href}` in `ButtonComponent` — if consumer passes `javascript:` URI, XSS is possible

### Cryptography
- `crypto-browserify` in webpack config provides browser-compatible Node.js crypto API
- `pbkdf2:^3.1.5` in devDependencies — not used by library components directly
- No cryptographic operations visible in component source

### CVE / Dependency Risk

| Dependency | Version | Risk |
|---|---|---|
| `react` | `^18.2.0` | Stable; low risk |
| `react-bootstrap` | `^2.7.2` | Stable; based on Bootstrap 5 |
| `lodash` | `^4.17.21` | Prototype pollution CVEs in older versions — `^4.17.21` is patched |
| `react-scripts` | `^5.0.1` | CRA — deprecated; known transitive CVEs in CRA dependency tree |
| `react-google-recaptcha` | `^2.1.0` | reCAPTCHA v2 — functional; v3 preferred |
| `web-vitals` | `^2.1.4` | Low risk |
| `@sanity/eslint-config-studio` | `^2.0.1` | Dev only; unexpected dependency for a payments UI library |

### CodeQL
Configured (`codeql.yml`) — runs on every push, PR, and weekly Saturday schedule.

## Technical Debt

| Item | Location | Severity |
|---|---|---|
| `LoginSection.validate()` always returns `true` — validation commented out | `src/Components/CompositeReusableComponent/LoginSection.js:57–77` | High — consuming applications must not rely on client-side login validation |
| `dist/` committed to VCS | `dist/` directory | High — rebuilt artefacts in source control; stale build risk |
| No npm registry publish pipeline | `package.json` | High — no formal versioned distribution |
| CRA (`react-scripts`) deprecated | `package.json:31` | High — test infrastructure will break |
| `@sanity/eslint-config-studio` in dependencies (not devDependencies) | `package.json:27` | Medium — unnecessary production dependency |
| Multiple Babel configs may conflict | `.babelrc`, `src/babel.config.js`, `example/babel.config.js` | Medium |
| `ButtonComponent` spreads all props to `<Button>` via `{...props}` — exposes all HTML attributes | `ButtonComponent.js:54` | Medium — potential for unintended attribute injection |
| `href={props.href}` without `javascript:` URI sanitisation in `ButtonComponent` | `ButtonComponent.js:46` | Medium — XSS vector if consumers pass user-controlled href |
| Error boundary: `throw "Error encountered in Button Component :" + ex` (throws string, not Error) | `ButtonComponent.js:34` | Low — string thrown cannot be caught by `instanceof Error` checks |

## Gen-3 Migration Requirements

1. **Replace CRA with Vite** — migrate `react-scripts` test/build to Vite; fixes deprecated CRA
2. **Publish to npm/GitHub Packages** — add `publishConfig` and a GitHub Actions publish workflow
3. **Add Storybook** — document components and enable visual regression testing
4. **Fix `LoginSection.validate()`** — uncomment or remove validation dead code
5. **Sanitise `href` in `ButtonComponent`** — add `javascript:` URI check
6. **Remove `@sanity/eslint-config-studio`** from production dependencies
7. **Migrate to TypeScript** — add type declarations for consuming TypeScript applications
8. **Remove `dist/` from VCS** — add `dist/` to `.gitignore`; build during CI publish step

## Code-Level Risks (file:line references)

| Risk | File | Line | Detail |
|---|---|---|---|
| Login validation always returns true (dead code) | `src/Components/CompositeReusableComponent/LoginSection.js` | 57–77 | `validate()` returns `true` unconditionally — all checks commented out |
| `cardnumber` state in LoginSection — card number in React state | `LoginSection.js` | 19, 111–113 | `const [cardnumber, setCardnumber] = useState()` — card number held in component state |
| Button spreads all props — no prop sanitisation | `src/Components/ReusableComponent/ButtonComponent.js` | 54, 70 | `{...props}` passes all consumer props directly to DOM element |
| `href` without `javascript:` sanitisation | `ButtonComponent.js` | 46, 62 | `href={props.href}` — XSS if href value is user-controlled |
| Error thrown as string (not Error object) | `ButtonComponent.js` | 34 | `throw "Error encountered in Button Component :" + ex` — anti-pattern |
| `@sanity/eslint-config-studio` in `dependencies` (runtime) | `package.json` | 27 | Should be in `devDependencies` |
| `empty .env` file committed | `.env` | 1 | Empty but establishes pattern — risk of accidentally committing secrets |
