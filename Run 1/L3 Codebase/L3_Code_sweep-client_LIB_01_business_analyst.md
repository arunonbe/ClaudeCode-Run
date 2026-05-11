# Business Analyst View — sweep-client_LIB

## Business Purpose
The sweep client is a batch command-line utility that synchronises "instant sweep" promotions with order management. It queries active sweep promotion profiles and invokes corresponding order service operations (Create, Close, Reserve, Free, or Notify) for each enabled promotion. "Sweep" in this context refers to an automated process that creates, manages, or closes prepaid card order batches tied to promotional programmes on a scheduled basis.

## Capabilities
1. **Profile Resolution**: Reads `AppPromotionInstantSweepOrder` profiles from the xPlatform/CBase layer filtered by member, agent, affiliate, and optional active time.
2. **Method Dispatch**: Dispatches one of five operations per profile:
   - **Create**: Creates sweep orders for a programme/promotion (N days ahead, with optional fund initialisation).
   - **Close**: Closes existing sweep orders.
   - **Reserve**: Reserves initial sweep order capacity.
   - **Free**: Frees reserved sweep order capacity.
   - **Notify** (`CheckNotificationThreshold`): Checks if notification thresholds have been reached.
3. **Dry Run Mode**: Executes without calling the Order Service — logs what would be done.
4. **Service Availability Check**: Pings the Order Service before execution (skipped in dry-run).
5. **Exit Codes**: Returns structured exit codes (0=success, 1=partial failure, 2=profile error, 3=service unavailable, 4=context load failure, 5=usage/argument error).

## Entities
| Entity | Description |
|--------|-------------|
| `AppPromotionInstantSweepOrder` | Profile from xPlatform/CBase: programme ID, promotion ID, active time, autoEnabled flag, cleanup flag |
| `SweepProfile` | DTO copied from `AppPromotionInstantSweepOrder` for Order Service calls |
| `Method` | Enum: Create, Close, Reserve, Free, Notify |

## Business Rules
- Only profiles where `isAutoEnabled() == true` OR `isCleanup() == true` are processed; others are skipped.
- The `-method` argument is mandatory; missing it results in a usage error (exit code 5).
- The `-time` argument filters profiles by `activeTime` (seconds from midnight); must be a non-negative integer.
- When `-dryRun` is set, the Order Service is not called and no state changes are made.
- Default configuration: `numberOfDays=7`, `initializeOrderFunds=false`.

## Flows
1. JVM start → Spring context loaded from `applicationContext.xml`.
2. Command-line arguments parsed → `Method`, optional `activeTime`, optional `dryRun` set on `SweepClient`.
3. `ProfileReader.getSweepOrderProfileList(activeTime)` → queries xPlatform for enabled sweep profiles for the configured member/agent/affiliate.
4. For each profile → `MethodInvokerFactory.find(method)` → appropriate `MethodInvoker` implementation.
5. `invoker.invoke(dryRun, programId, promotionId, profile)` → calls Order Service (or logs if dry run).
6. Aggregate success/failure → exit with appropriate code.

## Compliance Relevance
- **Reg E**: Sweep operations create/close prepaid card orders — these are Reg E-regulated payment instruments.
- **PCI DSS**: Order Service operations involve payment product lifecycle; must ensure no cardholder data traverses the sweep client.
- **NACHA**: If sweep operations involve ACH fund loading, NACHA rules apply to timing and authorisation.

## Risks
- Default `memberId=778C2F5A-3956-4099-B567-A0F6926BDFCD` and `agent=B2CTEST` in `sweep.client.default.properties` — if production deployment uses default properties without override, it will target a test environment.
- No retry logic — a single Order Service failure marks the entire programme/promotion run as failed but continues processing others.
- No idempotency protection — if the sweep runs twice for the same active time (e.g., after a failed re-run), duplicate orders may be created.
- Spring 2.0.8 used — critically EOL.
