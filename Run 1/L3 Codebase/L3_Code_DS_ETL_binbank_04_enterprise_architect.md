# Enterprise Architect Report — DS_ETL_binbank

## Repository Identity

**Repository:** DS_ETL_binbank  
**Platform Generation:** Legacy SSIS ETL (Generation 1) — SQL Server 2012 era  
**Role in Architecture:** ACH settlement bridge between Onbe card processing platform and issuing banks

---

## Architectural Position

DS_ETL_binbank occupies a **critical regulatory bridge position** in the Onbe data architecture. It is the component responsible for translating internal card transaction data into the standardised NACHA ACH format required by banking partners:

```
[Ecountcore / CCP card processing]
           ↓ Transaction data
[cf_report database — BINBANK's source]
           ↓ nacha_load_source.dtsx (staging)
           ↓ nacha_file_process.dtsx (transform + generate)
           ↓ nacha_print_file.dtsx (format + write)
[C:\ETL\Out\<Bank>\temp\<bank>-ach-daily-recon.txt]
           ↓ [SFTP/MFT — NOT in this repo]
[Bank ACH endpoint: Fifth Third, Metabank, Sunrise]
           ↓ Federal Reserve ACH network
[Cardholder account funding]
```

This pipeline is at the **money movement layer** — failures here directly affect cardholder access to funds and Onbe's settlement obligations to its banking partners.

---

## Banking Partner Relationships

The BINBANK pipeline supports relationships with:

### Fifth Third Bank (Fifth Third Bancorp)
- Output: `C:\ETL\Out\FifthThird\temp\53-ach-daily-recon*.txt` and `EFA53-ach-daily-recon*.txt`
- Function: Daily ACH settlement and Early Funding Arrangement reconciliation
- Enterprise role: Issuing bank for prepaid card products; receives NACHA files for batch fund settlement

### Metabank (Pathward Financial)
- Identified by: `bank_name` parameter default `MB`
- Enterprise role: Major prepaid issuing bank; program manager-bank relationship

### Sunrise Banks
- Identified by: `sunrise_transaction_code_export.dtsx`
- Enterprise role: Issuing bank for specific prepaid programs; transaction code-level reconciliation

Each bank requires different NACHA configurations (routing numbers, company IDs, batch settings) stored in `cf_report`.

---

## NACHA Architecture Assessment

### ACH Network Architecture

Onbe operates as an **Originating Depository Financial Institution (ODFI)** agent or as a **Third-Party Service Provider (TPSP)** in the ACH hierarchy. The BINBANK pipeline originates ACH entries on behalf of Onbe and its banking partners.

Under NACHA Operating Rules (2024 update), Third-Party Service Providers that originate ACH transactions must:
1. Have formal agreements with ODFIs
2. Implement proper file balancing controls
3. Maintain return rate monitoring
4. Comply with ACH audit requirements

The BINBANK pipeline's quality directly impacts Onbe's NACHA compliance standing with each issuing bank partner.

### EFA (Early Funding Arrangement) Architecture
The EFA file (`EFA53-ach-daily-recon*.txt`) suggests Fifth Third provides early funding to Onbe before ACH settlement clears. This is a credit facility where Fifth Third fronts the cash to prepaid cardholders based on the EFA file, then collects through the ACH system. The EFA reconciliation file is the financial instrument that triggers this early funding. **Errors in the EFA file have direct cash impact on both Onbe and Fifth Third.**

---

## Dependency Map

### Upstream
| System | Dependency | Risk |
|---|---|---|
| Ecountcore / CCP | Transaction data source (via cf_report) | HIGH — no transactions = no NACHA content |
| cf_report database | Primary data source for all BINBANK packages | CRITICAL — single point of failure |

### Downstream
| System | Dependency | Risk |
|---|---|---|
| Fifth Third Bank ACH system | Receives NACHA files | HIGH — if files not received, funding delayed |
| Metabank/Pathward ACH | Receives NACHA files | HIGH — same |
| Sunrise Banks ACH | Receives transaction codes | MEDIUM |
| Federal Reserve ACH network | Settlement clearing | CRITICAL — no submission = no funding |

---

## Regulatory Compliance Footprint

The BINBANK pipeline is within scope for:
1. **NACHA Operating Rules** — direct ACH file origination
2. **Reg E** — prepaid cardholder fund access
3. **GLBA** — bank account and routing number data
4. **PCI DSS** — if account numbers in NACHA records are linked to card PANs
5. **SOX** — financial settlement data used in accounting

The pipeline should be included in:
- NACHA annual audit scope
- PCI DSS SAQ/ROC scope review
- SOX ITGC (IT General Controls) assessment

---

## Migration Complexity Assessment

| Migration Concern | Complexity | Notes |
|---|---|---|
| Replacing SSIS with Azure Data Factory | MEDIUM | 5 packages; complex NACHA formatting in nacha_print_file must be replicated exactly |
| Migrating to NACHA API (if available from banks) | HIGH | Requires bank partner agreement changes |
| Adding multi-bank parallel execution | MEDIUM | Current serial per-bank execution could be parallelised |
| Implementing SFTP file transmission in pipeline | LOW | Add as a final step; many SSIS SFTP task libraries available |
| Migrating cf_report source to modern data platform | HIGH | cf_report is shared across multiple pipelines; requires coordinated migration |
