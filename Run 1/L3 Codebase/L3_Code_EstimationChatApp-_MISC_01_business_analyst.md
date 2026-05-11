# Business Analyst Analysis — EstimationChatApp-_MISC

## Repository Overview

**Repo name:** `EstimationChatApp-_MISC`
**Type:** Internal POC / developer tooling — real-time sprint estimation chat application
**Primary language:** JavaScript (Node.js)
**Framework:** Express.js + Socket.IO
**Package name:** `estimationchat` (`package.json` line 2)
**Author:** TCS (`package.json` line 6) — indicates Tata Consultancy Services contractor origin
**Classification suffix:** `_MISC` — confirms this is a miscellaneous/sandbox repo, not a production service

---

## Business Purpose

This application is a **planning poker / sprint estimation tool** built for internal Agile ceremonies. It enables distributed scrum teams (likely North Lane / Onbe development squads) to conduct real-time story-point estimation sessions without requiring a commercial tool (e.g., Jira Planning Poker).

### Core Workflow

1. An **admin** (scrum master or facilitator) navigates to the login page, enters their team name and a team code (validated against `.env` file values).
2. If authenticated, the admin lands on the `sprintMaster` page and creates an estimation room.
3. **Associates** (team members / developers) navigate to the room URL and join the room.
4. The admin presents a user story; each associate privately enters their estimate.
5. The admin triggers "show all" to reveal all estimates simultaneously (preventing anchoring bias).
6. The admin can "reset" the round for the next story.

### Teams Supported

The `.env` file (lines 1–5) defines five teams with simple numeric codes:
```
Olympus = 1
Phoenix = 2
Guardians = 3
Warriors = 4
openteam = 5
```
These are the scrum team names in use at the time of authorship.

### Business Value

- Enables **asynchronous, remote estimation** for geographically distributed teams.
- Eliminates the need for a paid planning poker SaaS subscription.
- Lightweight, real-time via WebSocket (Socket.IO).
- Simple enough that TCS contractors could build and maintain it.

---

## Business Limitations and Concerns

| Limitation | Detail |
|-----------|--------|
| Authentication is trivially weak | A numeric code per team name is stored in plaintext in `.env`; anyone with the code can access the admin view |
| No persistence | Estimation results are held in server memory only; a server restart loses all active sessions and room state |
| Single room per team limitation | Room lifecycle is managed in memory (`listOfRoomsOpened` array in `main.js` line 39); no database backing |
| No story tracking | The application only facilitates real-time voting; it does not record which stories were estimated or what the final estimates were |
| No integration with Jira/ADO | Results must be manually entered into the project management tool |
| Not production-hardened | No rate limiting, no input sanitisation on room names, no HTTPS enforcement |

---

## Stakeholder Analysis

| Stakeholder | Role in App |
|-------------|-------------|
| Scrum Masters / Facilitators | Admin — create rooms, reveal estimates, reset rounds |
| Developers / QA / BA | Associates — join rooms, submit estimates |
| Engineering Leadership | No direct involvement; may benefit from velocity/estimation accuracy data (not captured) |

---

## Compliance and Risk Assessment

This application handles no payment data, no PII (beyond a team name at login), and no regulated financial information. It is entirely outside the PCI DSS CDE scope. However, several low-level concerns exist:

1. **Team names as access control** — if team names correspond to Onbe organizational units, leaking the `.env` file could expose the mapping of team names to numeric codes (low risk, but poor hygiene).
2. **`.env` file committed to the repository** — the `.env` file is present in the repo root (`EstimationChatApp-_MISC\.env`). While the values (team codes 1–5) are not sensitive financial data, committing `.env` files is a bad practice that trains engineers to do the same with genuinely sensitive configurations.
3. **No access control beyond team code** — any person with the team code can access the admin (scrum master) view and manipulate the estimation session.

---

## Recommendation

This application is a **sandbox/POC tool** (_MISC suffix confirms this classification). It should remain classified as internal developer tooling only and should not be promoted to a production-hosted service without:
1. Replacing the `.env`-based authentication with SSO (Onbe's corporate identity provider).
2. Adding HTTPS enforcement.
3. Adding persistence for estimation history.
4. Moving the `.env` file out of source control.

Given its limited scope and the availability of free/low-cost alternatives (e.g., PlanITpoker, PointingPoker), the cost-benefit of investing in productionising this tool should be evaluated before any engineering effort is committed.
