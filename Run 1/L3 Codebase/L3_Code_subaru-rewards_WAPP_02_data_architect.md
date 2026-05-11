# Data Architect View — subaru-rewards_WAPP

## Data Stores
| Store | Type | Description |
|-------|------|-------------|
| `cbaseapp` SQL Server | Microsoft SQL Server | Primary application database; all `rewards_subaru_*` tables reside here |
| Filesystem | Local file system | Payment request XML files written to path configured via `REQUEST_FILE_BASE_PATH` property |
| EHCache | In-process | Salesperson, dealer, pay cycle, 24-hour schedule caches |

Spring XML references `RewardsDataSource` (alias injected by container).

## Schema / Tables (from SQL DDL files)
| Table | Key Columns | PII / Sensitive |
|-------|------------|-----------------|
| `rewards_subaru_sales` | id, batch_id, vin, trx_class, dealer_code, delivery_dt, soa_sale_type, region_code, model_code, car_line, sale_transaction_id, sales_person_id, district_code, model_year, **cust_name**, status_code | `cust_name` is PII (customer name) |
| `rewards_subaru_salesperson` | batch_id, sales_person_id, login_id, dealer_code, first_name, middle_name, last_name, suffix, title, **email**, active_status, termination_date, certification_date, dealer_termination_date, w9_status, hold_status, summit_score, id, card_issue_date, status_code | PII: name, email; sensitive: W-9 status, certification date |
| `rewards_subaru_reward` | id, trx_no, reward_type, payment, ppid, status_code, pay_cycle_id, trx_no_ref, payment_status, dealer_status, salesperson_status | `ppid` = payment profile/prepaid card ID (financial reference) |
| `rewards_subaru_dealer` | dealer_code, name, region_code, district_code, status_code, active_status, batch_id | — |
| `rewards_subaru_pay_cycle` | id, start_date, status_code, sales_cycle_id | — |
| `rewards_subaru_sales_cycle` | id | — |
| `rewards_subaru_ascent_schedule` | id, unit, tier (inferred from queries) | — |
| `rewards_subaru_summit_schedule` | id, unit, tier, summit_schedule_id | — |
| `rewards_subaru_summit_org_schedule` | id, sales_cycle_start, sales_cycle_stop, region_code, org_level | — |
| `rewards_subaru_district_ascent_schedule` | ascent_schedule_id, sales_cycle_start, sales_cycle_stop, region_code, district_code | — |
| `rewards_subaru_special_model_payment` | model_code, pay_cycle_start, pay_cycle_stop | — |
| `rewards_subaru_profile` | id, value | Configuration key-value (certification_year/month/day) |
| `rewards_subaru_reward_addenda` | reward_id, sequence, code, message | — |
| `rewards_subaru_region` | code, name | — |
| `rewards_subaru_district` | district_code, region_code | — |
| `rewards_subaru_admin_banner` | sales_person_id, banner_text | — |
| `rewards_subaru_batch` | id, batch_date | — |
| `rewards_subaru_reward_status` | code | Reference/lookup |
| `rewards_subaru_reward_type` | code | Reference/lookup |

## Sensitive Data Classification
| Field | Classification | Regulatory Scope |
|-------|---------------|-----------------|
| `cust_name` in `rewards_subaru_sales` | PII (customer name) | CCPA, GLBA |
| `first_name`, `middle_name`, `last_name`, `email` in `rewards_subaru_salesperson` | PII (employee/contractor) | CCPA, GLBA, Reg E |
| `w9_status`, `certification_date` | Tax status / financial eligibility | IRS / GLBA |
| `ppid` in `rewards_subaru_reward` | Payment reference ID (prepaid card or ACH reference) | PCI DSS Req 3, Reg E |
| `vin` in `rewards_subaru_sales` | Vehicle Identifier — indirectly re-identifiable | CCPA |
| Payment request XML files on filesystem | Contain cardholder name, payment amount, programme/promotion IDs | PCI DSS Req 3/9 |

## Encryption
No encryption-at-rest is implemented in this application layer. Data is stored as plaintext in SQL Server. PCI DSS-relevant `ppid` values and PII fields are unencrypted in the database.

The payment request XML file pipeline uses JAXB marshalling to a filesystem path — no encryption of the file is observed.

## Data Flow
```
Subaru source system --> rewards_subaru_sales table (batch load, method unclear from code)
                                 |
                          SubaruRewardsImpl.run()
                                 |
                    State machine processing
                    (validate → qualify → quantify → persist reward)
                                 |
                    rewards_subaru_reward (reward records written)
                                 |
                    PostCycleState
                                 |
                    SubaruRequestBuilder.createReqFile()
                                 |
                    XML request file written to filesystem
                                 |
                    Onbe payment platform (AddFunds / CreateAccount)
```

## Data Quality and Retention
- No data purge or archival strategy observed in the codebase.
- Sale records remain in `rewards_subaru_sales` indefinitely with `status_code` transitions.
- Reward records remain in `rewards_subaru_reward` indefinitely.
- EHCache TTL appears to be 24 hours for reference data (`24Hours` cache), no TTL set for `DealerCache` / `SalespersonCache` (inferred from cache names — actual ehcache.xml not read here but present as `subaru-reward-engine-ehcache.xml`).
- A `scratch.sql` file is present in the SQL directory — indicates ad-hoc DBA tooling.

## Compliance Gaps
| Gap | Standard | Severity |
|-----|----------|----------|
| PII (`cust_name`, salesperson name/email) stored as plaintext in SQL Server | PCI DSS Req 3, CCPA | High |
| `ppid` (payment profile/card reference) stored as plaintext VARCHAR(50) | PCI DSS Req 3 | High |
| No encryption of XML payment request files on filesystem | PCI DSS Req 3/4/9 | High |
| No data retention / purge policy | CCPA, GLBA, GDPR | Medium |
| `vin` retention without purpose limitation | CCPA | Medium |
| `scratch.sql` in repository | PCI DSS Req 12 (evidence of ad-hoc access) | Low |
| SCM URL points to internal SVN (`ecsvn.office.ecount.com`) — legacy source control | Change management | Low |
