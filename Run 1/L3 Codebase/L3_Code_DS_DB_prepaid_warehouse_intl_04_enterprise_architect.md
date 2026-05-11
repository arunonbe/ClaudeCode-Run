# DS_DB_prepaid_warehouse_intl — Enterprise Architect Assessment

## 1. Platform Generation

The International Prepaid Warehouse targets **SQL Server 2012** — one full major version behind the US warehouse (2016). The project uses .NET Framework 4.0, placing it in an earlier development generation (circa 2010–2014). This version gap suggests the international warehouse received less investment and upgrade attention than its US counterpart. The architecture is otherwise identical in pattern to the US warehouse (SSDT project, star schema, CDC-fed ETL, columnstore OLAP support).

---

## 2. Role in the Onbe Architecture

The international warehouse is the **analytical foundation for non-US prepaid programs**. It occupies the same position in the architecture as the US warehouse, but serves a different cardholder population and must accommodate:

- Multi-currency transaction amounts (resolved through GL Company dimension)
- Multi-language cardholder names and addresses (NVARCHAR columns)
- Country-level reporting dimension (`dim.DimCountry`)
- International regulatory reporting requirements (GDPR, PIPEDA, etc.)

```
International Operational Layer          ETL Layer           International Analytics
────────────────────────────────         ─────────           ─────────────────────────
International EcountCore / FDR   -->    ETL procedures  -->  dim.* + fact.*
International program systems    -->                         TTS Int'l Data Feed
                                                             OLAP Cube (int'l)
```

---

## 3. System Dependencies

### 3.1 Upstream Sources
The international warehouse pulls from:
- International EcountCore operational database (assumed separate instance from US)
- FDR processor international feeds
- International job service systems

Cross-database linked server references (`[REPORTINGDBSERVER]`) appear in the TTS data feed procedure, indicating the same reporting server pattern as the US warehouse is used for international data.

### 3.2 Downstream Consumers
- TTS international data feeds (clients and partners)
- OLAP cube for international programs
- Reporting users with access to international cardholder data
- Potentially: cross-border regulatory reporting

---

## 4. Data Governance and Sovereignty

### 4.1 Data Residency
The most significant enterprise architecture concern for this database is **data residency**. The international warehouse holds `dim.DimAccountHolder` records for cardholders who may be EU residents (GDPR jurisdiction), Canadian residents (PIPEDA jurisdiction), or residents of other countries with data localisation requirements.

If this database is hosted in the United States:
- **GDPR Article 44** restricts transfers of EU personal data to third countries without adequate safeguards (Standard Contractual Clauses, adequacy decisions, etc.)
- **Quebec Law 25** imposes consent and privacy impact assessment requirements for personal information transferred outside Quebec
- Data residency requirements in emerging markets (Brazil LGPD, India DPDP) may also apply

No data residency controls are visible in the schema. This is an enterprise architecture decision that must be addressed at the infrastructure level, but the schema design (no jurisdiction flags, no data classification columns) makes it impossible to identify which records belong to which regulatory jurisdiction.

### 4.2 Cross-Border Analytics Sensitivity
The `rpt_TTS_data_feed` procedure (lines 44–73 in `dbo/Stored Procedures/rpt_TTS_data_feed.sql`) aggregates transaction data by country, program, currency, and product for partner reporting. This cross-border data aggregation must comply with data sharing agreements with TTS and Citi.

---

## 5. Integration Complexity

### 5.1 US/International Split
The split of US and international data into separate warehouse databases introduces several integration complexities:
- Enterprise-wide reporting (global program performance) requires cross-database queries or an additional aggregation layer
- Data definitions that diverge between the two warehouses (e.g., `Org`/`Logo` fields in international, absent in US) complicate unified data models
- ETL processes must be independently maintained for each warehouse

### 5.2 Version Drift Risk
The US warehouse (SQL 2016) and international warehouse (SQL 2012) are deployed to different SQL Server versions. Any stored procedure that uses SQL 2016+ features (e.g., `STRING_SPLIT`, `COMPRESS`, `DROP IF EXISTS`) in the US warehouse cannot be directly ported to the international warehouse without modification.

---

## 6. Technical Debt and Migration Complexity

| Item | US Warehouse | International Warehouse | Gap |
|---|---|---|---|
| SQL Server version | 2016 | 2012 (EOL) | 4 year version gap |
| .NET Framework | 4.6.1 | 4.0 | 2 generations behind |
| Unicode support | varchar (ASCII) | nvarchar (Unicode) | Better design for Intl |
| Dynamic Data Masking | Available (SQL 2016) | NOT available (SQL 2012) | Critical security gap |
| Row-Level Security | Available | NOT available | Access control gap |
| Always Encrypted | Available | NOT available | Encryption gap |
| CI/CD | None | None | Same gap |

The absence of Dynamic Data Masking, Row-Level Security, and Always Encrypted in SQL Server 2012 means that **none of the modern data protection controls available in SQL Server 2016** can be applied to the international warehouse without first upgrading the SQL Server target. This is a critical finding given that this warehouse holds GDPR-regulated EU cardholder data.

---

## 7. Recommended Architecture Interventions

1. **Upgrade SQL Server target to 2019 or 2022** (or migrate to Azure SQL Database) to enable Dynamic Data Masking, Always Encrypted, and Row-Level Security for GDPR compliance.
2. **Add a jurisdiction/country-of-residence flag** to `DimAccountHolder` to enable jurisdiction-aware data governance (retention, deletion, masking policies per jurisdiction).
3. **Evaluate data residency** — determine whether international cardholder data must be stored in-country for GDPR compliance and implement a storage strategy accordingly.
4. **Unify with US warehouse** or maintain documented divergence — the current two-warehouse approach creates long-term maintenance burden. A single multi-regional warehouse with jurisdiction partitioning would reduce duplication.
5. **Establish CI/CD** — same recommendation as US warehouse; especially important given the higher regulatory risk of international PII.
