# DS_ETL_ccp-import-to-legacy — Enterprise Architect Report

## 1. Platform Generation

| Attribute | Value |
|-----------|-------|
| Platform generation | Gen-1 (Wirecard/eCount legacy platform) |
| Technology stack | SSIS 2012, SQL Server SQLNCLI11.1, `nam.wirecard.sys` domain |
| Repository prefix | `DS_ETL_` — Data Services ETL pipeline |
| SSIS format | SQL Server 2012 Project Deployment Model |
| Provenance | Created April 2019 by `WIRECARD\julia.ginzburg` on workstation `PF0VET79` |

This pipeline is a **Gen-1 artefact** from the Wirecard era. The server hostname (`d-na-db01.nam.wirecard.sys`), email addresses (`namds@wirecard.com`, `NoReply@wirecard.com`), and workstation name in the project metadata all confirm Wirecard provenance pre-dating the Onbe brand.

---

## 2. Business Domain

**Domain**: Data Integration — CCP-to-Legacy Platform Bridge  
**Subdomain**: Card account data synchronisation between CCP (new platform) and eCount (legacy platform)

This pipeline existed to support a **dual-platform operation period** during which Onbe (then NorthLane/Wirecard) was running the CCP card processing platform alongside the legacy eCount platform. The CCP platform produced data that the legacy eCount platform needed to stay synchronised.

The pipeline imports:
- Card accounts and statuses (with potential PCI DSS scope data)
- Transaction history (financial data, SOX-relevant)
- Billing/invoicing data (NACHA, revenue recognition)
- FVD deferred revenue (ASC 606)
- Fiserv card inventory (operational)

---

## 3. System Role in the Enterprise

| Role | Description |
|------|-------------|
| CCP-to-legacy bridge | Synchronises card account, transaction, billing, and revenue data from CCP to the eCount legacy platform |
| Data reconciliation enabler | Billing and FVD packages enable financial reconciliation between the two platforms |
| Decommission candidate | Once eCount is fully decommissioned, this pipeline has no purpose |

**This pipeline's continued operation is contingent on eCount being in active use.** If eCount has been or is being decommissioned, this pipeline should be retired simultaneously.

---

## 4. Dependencies

### Upstream
| System | Integration | Data Provided |
|--------|------------|--------------|
| `DS_CCP_ccp-export-to-legacy` | Flat files in `C:\ETL\In\WDCCP\` | All 10 import package source files |
| CCP Platform (Sunrise) | Via `DS_CCP_ccp-export-to-legacy` | Card account, transaction, balance, billing, FVD data |
| Fiserv | Via CCP export | Card inventory data |

### Downstream
| System | Integration | Data Consumed |
|--------|-----------|--------------|
| `CCP` staging database | OLE DB to `d-na-db01` | Landing zone for all imported data |
| Legacy eCount (`ECNT`, `ECAN`) | Via staging DB stored procedures | Fully synchronised card data |

### Infrastructure
| Dependency | Assessment |
|-----------|-----------|
| `d-na-db01.nam.wirecard.sys\db01,2232` | **Wirecard domain** — must be confirmed as still operational post-migration |
| `nam.wirecard.sys` Windows domain | **Wirecard AD domain** — Windows auth depends on this domain trust |
| SSIS 2012 server | EOL infrastructure |

---

## 5. Integration Patterns

| Pattern | Where Used | Assessment |
|---------|-----------|------------|
| File-based ETL | All 10 packages — read pipe-delimited flat files | Gen-1 pattern; no API or message-queue integration |
| OLE DB bulk insert | All packages — write to `CCP` staging database | SSIS OLE DB destination; bulk insert performance |
| Windows AD authentication | `CCP-SQLDB.conmgr` — `Integrated Security=SSPI` | Domain auth to staging DB |
| SMTP notification | `SMTP Connection Manager.conmgr` — failure emails | Basic operational alerting |
| SSISDB Project Deployment | `.dtsproj` Project Deployment Model | SSIS catalog-based deployment |

---

## 6. Strategic Status

**Current status**: UNCERTAIN — likely legacy/decommission candidate.

The CCP-to-legacy bridge pipeline was created to support dual-platform coexistence during the eCount-to-CCP migration. Depending on the current state of the eCount platform:

- **If eCount is still active**: This pipeline is actively required and must be maintained.
- **If eCount is being decommissioned**: This pipeline is a decommission candidate and should be retired as part of the eCount wind-down.

Indicators that this pipeline may be inactive or obsolete:
1. No CI/CD pipeline — not integrated into automated deployment.
2. Wirecard-era email addresses not updated to Onbe — may indicate low maintenance activity.
3. The README simply states its purpose without current operational notes.
4. The `DS_CCP_*` repositories (its upstream dependency) are also in the `DS_` namespace — all of this infrastructure is Gen-1.

---

## 7. Migration Blockers

| Blocker | Detail |
|---------|--------|
| eCount dependency | Cannot decommission until eCount itself is decommissioned |
| Wirecard domain | Server `d-na-db01.nam.wirecard.sys` and AD domain must be confirmed active |
| PCI DSS scoping | `CardExpirationDate` and `AccountIdentifier` fields require QSA review before migration design can proceed |
| SSIS 2012 infrastructure | Requires SSIS 2012 runtime — no modern SSIS or ADF equivalent exists without redesign |
| No test coverage | No automated tests; migration validation relies entirely on manual comparison |
| Fiserv inventory data | Fiserv partnership and data format must be confirmed as still valid |
