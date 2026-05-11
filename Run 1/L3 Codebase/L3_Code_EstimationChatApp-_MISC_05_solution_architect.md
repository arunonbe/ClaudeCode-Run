# Solution Architect Analysis — EstimationChatApp-_MISC

## Repository Overview

**Repo:** `EstimationChatApp-_MISC`
**Entry point:** `main.js`
**Runtime:** Node.js + Express 4 + Socket.IO 3
**Views:** Static HTML (`.html` files in `views/`)
**Assets:** CSS, JS, images in `assets/`

---

## Solution Architecture

### Component Map

```
main.js (Express + Socket.IO server)
  |
  |-- HTTP Routes (Express Router)
  |     GET  /               --> views/login.html
  |     GET  /sprintMaster   --> views/sprintMaster.html
  |     POST /loginVerify    --> auth check -> views/sprintMaster.html or HTTP 500
  |     GET  /*              --> views/sprintAssoc.html (if room exists) or views/404.html
  |
  |-- WebSocket Events (Socket.IO)
  |     "create"             --> admin creates room
  |     "joinroom"           --> associate joins room
  |     "postedEstimation"   --> associate submits estimate
  |     "showtoall"          --> admin reveals all estimates
  |     "resettoall"         --> admin resets round
  |     "disconnect"         --> cleanup
  |
  |-- Static assets
        assets/css/style.css, mystyle.css
        assets/js/login.js
        assets/images/...
```

### Authentication Flow

`main.js` lines 27–36:
```javascript
router.post("/loginVerify", (req, res) => {
  let tname = req.body.tname;
  let code = req.body.code;
  if (process.env[tname] == code) {
    res.sendFile(path + "sprintMaster.html");
  } else {
    httpMsgs.send500(req, res, "Invalid");
  }
});
```

- Credentials from `.env`: `Olympus=1`, `Phoenix=2`, etc.
- Returns HTTP 500 on failed login (should be 401/403).
- No session cookie set — the "authenticated" state is not maintained server-side after the POST response. A user can directly access `/sprintMaster` without authenticating.
- `==` (loose equality) used for comparison, not `===` (strict equality).

---

## Security Risks

### 1. Authentication Bypass — Direct URL Access (HIGH)
**Location:** `main.js` line 23
```javascript
router.get("/sprintMaster", (req, res) => {
  res.sendFile(path + "sprintMaster.html");
});
```
`/sprintMaster` is served unconditionally to any GET request. There is no session check. The login form only performs a POST to `/loginVerify`, but the admin page is accessible without any authentication token.

**Impact:** Anyone who knows the URL can access the admin estimation view without a team code.

**Recommendation:** Set a session cookie on successful login and check it on all protected routes.

### 2. Environment Variable Injection (MEDIUM)
**Location:** `main.js` line 30 — `process.env[tname]`
If `tname` is `"NODE_ENV"` and `code` is `"production"`, the check `process.env['NODE_ENV'] == 'production'` would succeed if Node runs in production mode, granting admin access.

**Recommendation:** Whitelist valid team names before using as object property keys.

### 3. HTTP 500 on Login Failure (LOW — Correctness)
**Location:** `main.js` line 34 — `httpMsgs.send500(req, res, "Invalid")`
Returning HTTP 500 on an authentication failure is incorrect — HTTP 401 (Unauthorized) or 403 (Forbidden) is the appropriate status code. This may confuse monitoring tools into treating failed login attempts as server errors.

### 4. No HTTPS (HIGH — In Any Deployment)
The server listens on plain HTTP (no TLS configuration). Login credentials (team name + code) are transmitted in cleartext. For any deployment beyond localhost, HTTPS is mandatory.

### 5. No CORS Configuration (MEDIUM)
Socket.IO 3.x defaults to allowing connections from any origin. If the application is deployed on a known hostname, CORS should be restricted to that origin only.

**Location:** `main.js` line 4:
```javascript
var io = require("socket.io")(http);
```
Should be:
```javascript
var io = require("socket.io")(http, { cors: { origin: "https://estimation.onbe.internal" } });
```

### 6. Prototype Pollution via Room Names (LOW)
Room names from `socket.on("create", function(room) {...})` are passed to `socket.join(roomStr)` and pushed into `listOfRoomsOpened`. A crafted room name of `"__proto__"` or `"constructor"` could potentially exploit prototype pollution in the array operations, though the Node.js/Socket.IO handling makes this a low practical risk.

### 7. Broken Dockerfile — Missing `npm install` (HIGH — Operational)
`Dockerfile` does not include an `npm install` or `npm ci` step. The container will fail at runtime because `node_modules` is absent. If `node_modules` is committed to the repository (a common mistake), this works accidentally but bundles potentially unaudited dependencies.

---

## Technical Debt Inventory

| Item | Location | Severity |
|------|----------|----------|
| No session management | `main.js` auth flow | High |
| Authentication bypass on `/sprintMaster` | `main.js` line 23 | High |
| `process.env[tname]` injection | `main.js` line 30 | Medium |
| HTTP 500 on auth failure | `main.js` line 34 | Low |
| No HTTPS | Architecture | High |
| No CORS restriction | `main.js` line 4 | Medium |
| No `npm install` in Dockerfile | `Dockerfile` | High |
| Node 15.3.0 (EOL) in Docker | `Dockerfile` line 1 | High |
| `.env` committed to repo | Repo root | Medium |
| Hardcoded port 3000 | `main.js` line 148 | Low |
| No tests | `package.json` | Low (given scope) |
| `==` loose equality in auth | `main.js` line 31 | Low |
| `north-lane-white.png` stale brand asset | `assets/images/` | Low |

---

## Minimal Hardening Recommendations

If this application is to be used beyond local development:

1. **Add session management** (`express-session` with a secure secret):
   ```javascript
   app.use(require('express-session')({ secret: process.env.SESSION_SECRET, resave: false, saveUninitialized: false }));
   ```
2. **Protect `/sprintMaster` route** — check `req.session.authenticated === true`.
3. **Fix auth status code** — return 401 instead of 500 on failed login.
4. **Restrict team names** — whitelist before using as `process.env` key.
5. **Fix Dockerfile** — add `RUN npm ci --omit=dev` and upgrade to `node:20-alpine`.
6. **Enforce HTTPS** — use a reverse proxy (nginx, Traefik) with TLS termination.
7. **Remove `.env` from repo** — add to `.gitignore`; inject via CI/CD secrets.

If the tool is not to be productionised, the recommendation is to archive the repository and adopt a SaaS planning poker tool instead.
