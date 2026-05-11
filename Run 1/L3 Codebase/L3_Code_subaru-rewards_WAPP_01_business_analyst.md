# Business Analyst View — subaru-rewards_WAPP

## Business Purpose
This is a B2B rewards engine that calculates, qualifies, quantifies, and disburses prepaid card or payment rewards to Subaru of America dealership salespersons for vehicle sales. It ingests sales transaction data from Subaru, applies business rules to determine eligibility and reward amounts (including Ascent and Summit programme tiers), manages payment cycles, and generates XML payment request files submitted to Onbe's payment platform.

## Capabilities
1. **Sales Ingestion**: Reads new sales records (VIN, dealer, salesperson, model, delivery date) from the `rewards_subaru_sales` table.
2. **Salesperson Management**: Creates and activates salesperson profiles; enforces W-9 status, certification date, and hold status before payment.
3. **Dealer Management**: Creates and activates dealer profiles.
4. **Reward Qualification**: Determines eligibility for RS (Retailer Specialist) and RSC (Retailer Specialist Certified) reward types.
5. **Reward Quantification**: Calculates reward amounts based on Ascent, Summit, and special model payment schedules.
6. **Reversal Handling**: Processes reversal sales transactions and reverses corresponding rewards.
7. **Pay Cycle Processing**: Aggregates qualified rewards into pay cycles; transitions pay cycle status.
8. **Payment Request File Generation**: Marshals reward payment data into JAXB-generated XML request files (`Requestfile`) for submission to the Onbe payment platform (AddFunds / CreateAccount / SPIN requests).
9. **Admin Interface**: Administrative views of regional, district, dealer, and salesperson reward data.
10. **Caching**: EHCache used for salesperson, dealer, pay cycle, and 24-hour reference data caches.

## Entities
| Entity | Description |
|--------|-------------|
| `Sale` | Vehicle sale record: VIN, batch, dealer code, trx class (RS/RSC), delivery date, salesperson ID, model, region/district |
| `SalesPerson` | Salesperson profile: ID, name, dealer, W-9 status, hold status, certification date, active status |
| `Dealer` | Dealer profile: dealer code, name, region, district, status |
| `RewardJournal` | Reward record: reward type, payment amount, ppid (payment reference ID), status, pay cycle, dealer/salesperson status |
| `PayCycle` | Payment cycle: start date, status (ACT/PYD) |
| `SalesCycle` | Sales cycle containing one or more pay cycles |
| `AscentSchedule` | Per-district Ascent programme tier/unit payment schedule |
| `SummitSchedule` | Summit programme tier/unit payment schedule (regional and corporate) |
| `SpecialModelPayment` | Override payment amounts for specific model codes |
| `RewardProfile` | Key-value profile configuration (e.g., certification year/month/day thresholds) |
| `RewardAddenda` | Addenda codes/messages attached to a reward for payment file enrichment |
| `Requestfile` | JAXB-generated XML payment request file root element |

## Business Rules
- A salesperson must have `w9_status != 'N'`, `hold_status != 'Y'`, and a valid `certification_date` on or after the configured certification threshold to receive payment.
- Pay cycles are processed when the current date equals or passes the next-unpaid pay cycle start date.
- Reversals (trx_class RSC updating an RS) must look up the original RS sale and reverse the associated reward.
- Rewards in status `PAY` with expired pay cycles are transitioned to `EXP`.
- Reward types include: AFR, AKR, ANR, RAF, RAK, RAN, SFR, SKR, RSF, RSK (Ascent-related), NAR, A+R, RNA, RA+ (national), and others.
- A batch VBS script (`run_subaru_rewards.vbs`) is used for scheduled execution.

## Flows
1. **Daily/scheduled run**: `SubaruRewardsImpl.run(date)` → compare date to unpaid pay cycle → if on cycle: dealer → salesperson → sale → cycle → post → expire → commit; if off cycle: dealer → salesperson → sale → immediateReverse.
2. **State machine**: Each step executes a `AbstractRewardRequestState` implementation via `StateMachine`; states chain by setting `request.setState(nextState)`.
3. **Payment file generation**: `PostCycleState` → `SubaruRequestBuilder.createReqFile()` → JAXB marshal → XML file written to filesystem → submitted to Onbe payment platform.
4. **Admin view**: `SubaruRewardsAdminImpl` provides queries for regional, dealer, and salesperson reward summaries.

## Compliance Relevance
- **Reg E**: Payments to salespersons via prepaid card or ACH are subject to Reg E disclosures and error resolution.
- **IRS 1099**: W-9 status tracking and certification date enforcement indicate tax reporting obligations.
- **PCI DSS**: Payment request files contain card account numbers (`ppid`) and payment amounts; must be handled per PCI DSS Requirement 3/4.
- **UDAAP**: Reward calculation rules must be consistently and accurately applied to avoid unfair or deceptive practices.

## Risks
- `custName` (customer name) is stored in the `rewards_subaru_sales` table — potential PII requiring data classification.
- Hard-coded VIN field in sales — VINs can be used to re-identify individuals; data retention must be reviewed.
- `todo.txt` file present in `subaru-rewards-impl` — indicates known unresolved work items.
- Several modules (`subaru-rewards-service`, `subaru-rewards-web`, `subaru-rewards-requestfile`) are commented out of the parent POM build — partial/inactive code present in repository.
- Spring version 2.0.2 (extremely old) used in parent POM dependencies.
