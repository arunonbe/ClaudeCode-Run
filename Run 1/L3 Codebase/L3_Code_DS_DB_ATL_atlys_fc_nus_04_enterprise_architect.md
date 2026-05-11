# Enterprise Architect Analysis — DS_DB_ATL_atlys_fc_nus (atlys_fc_nus)

## Platform Generation

Same generation as `atlys_fc_nca` and `atlys_e`. 12–18-year-old SSDT platform, actively maintained through 2021. Structural clone of the NCA fee-calculation database.

---

## Role in Atlys Architecture

`atlys_fc_nus` occupies the **US region fee-calculation satellite** position in the Atlys hub-and-spoke architecture, parallel to `atlys_fc_nca`:

```
                    ┌───────────────────┐
                    │     atlys_e       │
                    │  (entity hub)     │
                    └────────┬──────────┘
              ┌──────────────┼──────────────┐
              │              │              │
       atlys_fc_nca    atlys_fc_nus    atlys_fccr
       (NCA region)    (US region)     (credit)
```

The separation of NCA and NUS databases suggests that Onbe's legal entities are partitioned by geography, with the US entity having its own fee-calculation instance. This is a common pattern in financial services where different legal entities report separately for regulatory and tax purposes.

---

## Dependencies (Outbound)

Identical to `atlys_fc_nca`:
- **atlys_e** (hard dependency via `ATLYS_E.dbo.*` three-part names)
- **SSAS** (conditional dependency in `sys_calc_dormancy` via `@@SERVERNAME` check)
- **Great Plains GL** (amortisation postings)
- **Salesforce CRM** (ext_id mapping, vsfdc_extract view)

---

## US-Specific Enterprise Architecture Considerations

### Legal Entity Isolation
The separate NUS database instance provides data isolation for US entity financial reporting. This supports:
- Separate GL amortisation postings to the US legal entity's chart of accounts.
- US-specific regulatory reporting (Reg E, state unclaimed property).
- Separate access control — US operations staff may have access to NUS but not NCA, or vice versa.

### US Market Product Mix
The US market's higher proportion of virtual card programmes (insurance disbursements, healthcare reimbursements, consumer rebates) compared to the broader NCA market means the US fee-calculation database has a different program composition. `vPlasticsDVirtual` and `vPlasticsDPhysical` views are operationally more important in this database than in NCA.

### Integration with US-Specific Systems
US programs may integrate with:
- **Healthcare claim systems** (for FSA/HSA disbursements) — not visible in the database schema but implied by the product types.
- **Insurance claim management systems** (for insurance disbursement cards).
- **Payroll systems** (for payroll card programs).
These integrations likely operate at the application layer and do not appear directly in the database schema, but the financial models in this database must accurately reflect the fee economics of these product types.

---

## Relationship Between atlys_fc_nca and atlys_fc_nus

This is the most architecturally significant observation for the NUS database: it is a **structural and code duplicate** of NCA. Evidence:
- Both `.sqlproj` files contain identical `<Build>` include lists.
- Both databases have the same 80+ stored procedures with the same names.
- Both databases have the same table and view sets.

The only business-meaningful difference is the programs they contain (US vs. NCA) and potentially the configured values in `tblAmort_Tables_1`/`tblAmort_Tables_2` and `tblControls`.

**Enterprise architecture implication:** The platform uses a **horizontal partitioning by geography** pattern where each region gets its own full copy of the schema rather than a **multi-tenancy** approach with a discriminator column. This pattern:
- Pros: Strong data isolation, independent deployment, independent performance management.
- Cons: Schema maintenance multiplied by N regions; bug fixes must be applied N times; reporting across regions requires cross-database queries.

---

## Cross-Regional Reporting

Management reporting across NCA and NUS portfolios requires cross-database queries joining `atlys_fc_nca` and `atlys_fc_nus` data. This is likely handled at the application layer or via SSAS cubes that aggregate both databases. The `sys_cinfo`/`sys_compinfodb` functions in `atlys_e` support this by providing the database-routing metadata.

---

## Migration Complexity Assessment

| Scenario | Complexity |
|---|---|
| Consolidate NCA + NUS into single multi-region database | High — requires tenant discriminator column addition, all procedures parameterised for region, data migration |
| Migrate to Azure SQL MI | Medium — identical to NCA migration complexity |
| Add a new US sub-region database (e.g., separate legal entity) | Low — fork existing NUS schema, register in atlys_e.tblCompanies |
| Upgrade compatibility level | Low-Medium — identical to NCA |
| Enforce Reg E compliance via database constraints | Medium — add CHECK constraints to cursforecast for US-specific fields |
