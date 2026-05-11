# 02 Data Architect — emboss-extract_LIB

## CRITICAL — PCI DSS Scope Declaration

This library extracts, processes, and writes **full Primary Account Numbers (PANs)** and **card expiry dates** to XML files. This places the library, its output directory, and any system that processes or stores its output firmly within the **Cardholder Data Environment (CDE)** under PCI DSS v4.0.1 Requirements 3, 4, and 9.

## Data Entity: `EmbossExtractData`

File: `src/main/java/com/ecount/process/emboss/dao/data/EmbossExtractData.java`

This is the central data transfer object. Every instance represents one card personalisation record. Full field inventory:

| Field | Java Type | PCI / PII Classification | Source Column |
|---|---|---|---|
| `requestId` | String | Internal ID | `request_id` |
| `ecountId` | String | Internal ID | `ecount_id` |
| `prefix` | String | PII | `prefix` (commented out in mapRow) |
| `firstName` | String | **PII — Cardholder Name** | `first_name` |
| `middleInitial` | String | PII | `middle_name` |
| `lastName` | String | **PII — Cardholder Name** | `last_name` |
| `suffix` | String | PII | `suffix_name` |
| `businessName` | String | PII | (commented out) |
| `address1` | String | **PII — Mailing Address** | `address1` |
| `address2` | String | PII | `address2` |
| `city` | String | PII | `city` |
| `state` | String | PII | `state` |
| `postal` | String | PII | `postal` |
| `country` | String | PII | `country` |
| `phone` | String | PII | `phone_number` |
| `packageId` | String | Configuration | `package_id` |
| `embossName` | String | **PII — Name as embossed on card** | `emboss_name` |
| `fourthLineEmboss` | String | Configuration | `fourth_line` |
| `cardNumber` | String | **PAN — FULL PCI CHD** | `card_number` |
| `cardExpiration` | String | **Expiry Date — PCI CHD** | `card.exp_month` + `card.exp_year` |
| `cardValue` | String | Financial | `card_value` |
| `variableTextId1`–`variableTextId20` | String | Variable text | `field_name`/`field_value` (carrier-variable-field1–20) |
| `deliveryAttentionName` | String | PII | `delivery_attention_name` |
| `deliveryBusinessName` | String | PII | `delivery_company_name` |
| `deliveryAddress1`–`deliveryAddress2` | String | **PII — Delivery Address** | `delivery_address1/2` |
| `deliveryCity`, `deliveryState`, `deliveryPostal`, `deliveryCountry` | String | PII | `delivery_city/state/postal/country` |
| `deliveryPhone` | String | PII | (commented out) |
| `deliveryMailCode` | String | Configuration | `mail_code` |
| `deliveryCode` | String | Configuration | `delivery_type` |
| `requestCount` | String | Audit | `rcount` |
| `deliveryLocation` | String | Configuration | `delivery_site_id` |
| `attentionName` | String | PII | `attention_line` |
| `companyName` | String | PII | — |

**Summary**: 4 PCI-sensitive fields (`cardNumber`, `cardExpiration`, `firstName`/`lastName` via `embossName`), plus ~20 PII fields.

## XML Output Format

The output is an XML document with namespace `http://www.ecount.com/`. Structure (from `StaxEmbossExtractBuilder.java`):

```xml
<embossfile fileid="123" requestcount="450" xmlns="http://www.ecount.com/">
  <request requestid="REQ-001" ecountid="12345">
    <firstname>Jane</firstname>
    <lastname>Sample</lastname>
    <embossname>JANE SAMPLE</embossname>
    <cardnumber>4111111100000000</cardnumber>      <!-- FULL PAN — PLAINTEXT -->
    <cardexpiration>122026</cardexpiration>         <!-- MMYYYY format -->
    <cardvalue>100.00</cardvalue>
    <address1>123 Main St</address1>
    ...
    <deliveryaddress1>123 Main St</deliveryaddress1>
    ...
    <variabletextid1>...</variabletextid1>
    ...
  </request>
  ...
</embossfile>
```

**CRITICAL FINDING — NO ENCRYPTION**: The `<cardnumber>` element contains the **full PAN in plaintext ASCII**. The file is written directly to the local filesystem (`StaxXMLUtil.getXMLStreamWriter(outputFileName)`). There is no HSM encryption, PGP encryption, or tokenisation applied to the card number before it is written to the file. The encryption (if any) is entirely external to this library — it would need to be applied by the downstream file-transfer process (NDM / Connect:Direct / SFTP).

## Database Objects

| Stored Procedure | Class | Purpose |
|---|---|---|
| `dbo.core_process_emboss_file_insert` | `InsertEmbossFile.java` | Creates a new emboss-file tracking record; returns `file_id` |
| `dbo.core_process_emboss_queue_extract(vendor_id, file_id)` | `CallCoreProcessEmbossQueueExtract.java` | Returns result set of all cards queued for embossing; columns include `card_number`, `card.exp_month`, `card.exp_year`, `emboss_name`, `first_name`, `last_name`, and delivery fields |
| `dbo.core_process_emboss_file_update(file_id, request_count, file_name)` | `UpdateEmbossFile.java` | Records the file name and count in the tracking record |

All stored procedures are in the `dbo` schema of the EcountCore database.

## Database Connection Configuration

The datasource is configured via Spring XML (`appContext-emboss.xml` lines 12–26) using `DriverManagerDataSource` (no connection pooling — a performance and reliability concern for production batch jobs). Properties come from `embossContext.properties`.

**CRITICAL FINDING — DEV CREDENTIALS IN PROPERTY FILES**: `src/conf/dev/embossContext.properties` and `src/conf/prod/embossContext.properties` both contain:

```
ecountcore.url=jdbc:jtds:sqlserver://ecsqldev1:1433/ECountCore_test
ecountcore.username=andrewc
ecountcore.password=andrewc
```

These are hardcoded developer credentials checked into source control. Even if they point to a dev/test database, committing credentials to source control violates PCI DSS Req 8.6.3 and is a security gap that must be remediated immediately.

## Data Flow Summary

```
SQL Server ecountCoreDB
  (dbo.core_process_emboss_queue_extract)
  → CallCoreProcessEmbossQueueExtract.processRow() [reads card_number, exp_month, exp_year, names, addresses]
  → EmbossExtractData (in-memory POJO — full PAN held in Java heap)
  → StaxEmbossExtractBuilder.createRequestNode() [writes <cardnumber>FULL PAN</cardnumber> to XMLStreamWriter]
  → FileOutputStream → XML file on local filesystem (PLAINTEXT PAN)
  → [External: NDM/SFTP/manual transfer to card bureau]
```
