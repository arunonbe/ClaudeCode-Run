# Data Architect Analysis — EstimationChatApp-_MISC

## Repository Overview

**Repo:** `EstimationChatApp-_MISC`
**Runtime:** Node.js, Express.js, Socket.IO
**Data storage:** In-memory (no database, no file persistence)
**Config:** `.env` file (dotenv)

---

## Data Architecture Overview

This application has an **entirely ephemeral data architecture** — all state is held in server-side JavaScript variables and is lost when the server process restarts. There is no database, no file system writes, and no external data service integration.

---

## Data Structures (In-Memory)

### `$ipsConnected` (Array, `main.js` line 38)
A global array of connected socket objects. Each entry has:
```json
{
  "ip": "<socket.id>",
  "type": "admin" | "assoc",
  "room": "<room_name>"
}
```
- `ip` field name is misleading — it actually holds the Socket.IO `socket.id` (a randomly generated connection identifier), not an IP address.
- Grows unbounded as users connect; entries are removed on `disconnect` event (lines 120–144).
- **No thread safety concern** in Node.js single-threaded event loop context.

### `listOfRoomsOpened` (Array, `main.js` line 39)
A global array of room name strings. Rooms are added when an admin creates them (line 64) and removed when the admin disconnects (lines 137–141).

---

## Data Flow

### Login Authentication
```
HTTP POST /loginVerify
  req.body.tname  (team name)
  req.body.code   (numeric code)
      |
      v
process.env[tname] == code ?
  YES: serve sprintMaster.html
  NO:  HTTP 500 "Invalid"
```
Team credentials are loaded from `.env` via `dotenv` (`main.js` line 7). The `.env` file contains:
```
Olympus = 1
Phoenix = 2
...
```
The team name is used directly as an environment variable key (`process.env[tname]`), making it susceptible to prototype pollution or environment variable injection if `tname` is crafted to match a sensitive Node.js environment variable (e.g., `PATH`, `NODE_ENV`).

### Room Management
```
Socket event: "create"
  room --> string room ID
  socket.join(roomStr)
  listOfRoomsOpened.push(roomStr)
  $ipsConnected.push({ip: socket.id, type: "admin", room: roomStr})
  emit "connectedusers" to room
```

```
Socket event: "joinroom"
  room --> string room ID (must already exist in listOfRoomsOpened)
  $ipsConnected.push({ip: socket.id, type: "assoc", room: room})
  emit "connectedusers" to room
```

### Estimation Flow
```
Socket event: "postedEstimation"
  estimation --> user's estimate value (string/number)
  roomval --> room ID
  emit "displayEstimation" to room: {ip: socket.id, value: estimation}
```
Estimate values are not typed or validated. Any string can be submitted as an estimate.

```
Socket event: "showtoall"    -- admin reveals estimates
Socket event: "resettoall"   -- admin resets round
```

---

## Data Sensitivity Assessment

| Data Type | Sensitivity | Notes |
|-----------|-------------|-------|
| Team name + code | Low | Not financial or PII data |
| Socket IDs | None | Ephemeral session IDs |
| Room names | None | Free-text strings |
| Estimation values | None | Story point numbers |
| `.env` file contents | Low | Team codes 1–5; not payment data |

No PII, no financial data, no cardholder data. This application is entirely out of PCI DSS scope.

---

## Data Architecture Concerns

### 1. No Persistence
Estimation results are never written to any store. When the server restarts (e.g., during deployment or crash), all estimation history is lost. This limits the utility of the tool for retrospectives or velocity tracking.

### 2. `process.env[tname]` — Environment Variable Injection
**Location:** `main.js` line 30
If `tname` is passed as `"NODE_ENV"`, `"PORT"`, `"PATH"`, or another meaningful environment variable, the comparison `process.env[tname] == code` will use that variable's actual value. A user submitting `tname=NODE_ENV&code=production` would succeed if `NODE_ENV=production`. This is a minor authentication bypass risk.

**Recommendation:** Whitelist valid team names before using them as object keys: `const allowedTeams = ['Olympus', 'Phoenix', 'Guardians', 'Warriors', 'openteam']; if (!allowedTeams.includes(tname)) return 403;`

### 3. Unbounded Memory Growth
`$ipsConnected` and `listOfRoomsOpened` grow indefinitely as users connect. Proper cleanup on disconnect is implemented (`main.js` lines 120–144), but if a socket disconnects without emitting the `disconnect` event (network drop), the entry may remain. Over time, on a long-running server with many users, memory pressure could occur.

### 4. No Input Sanitisation on Room Names
Room names are passed directly to `socket.join(roomStr)` and stored in `listOfRoomsOpened`. No length limit or character set restriction is applied. A long or specially crafted room name could cause routing issues or expose internal Socket.IO behaviour.

---

## Recommendations

1. **Add persistence** — store estimation sessions and results in a lightweight database (SQLite for simplicity, or PostgreSQL) to enable retrospective analysis.
2. **Fix environment variable injection** — whitelist valid team names.
3. **Move `.env` out of source control** — use `.env.example` in the repo and provide the real `.env` via a secure secrets manager or CI variable injection.
4. **Add input length limits** — cap room name length and estimate value length.
5. **Type estimation values** — validate that estimates are valid planning poker values (1, 2, 3, 5, 8, 13, 21, ?, coffee) before broadcasting.
