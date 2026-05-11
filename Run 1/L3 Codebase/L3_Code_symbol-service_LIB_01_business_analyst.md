# Business Analyst View — symbol-service_LIB

## Business Purpose
The symbol service is a shared reference data library that manages currency and locale symbols used across Onbe's prepaid card platform. It provides a central registry for symbols (e.g., currency symbols, locale-specific display characters) keyed by group and ID, enabling consuming services to display amounts, labels, and other localised text in the correct format for a given programme or cardholder context.

## Capabilities
1. **Create Symbol**: Inserts a new symbol record into the database via stored procedure `symbol_create`.
2. **Update Symbol**: Updates an existing symbol record via stored procedure `symbol_update`.
3. **Retrieve Symbol Group**: Returns all symbols for a given group via stored procedure `symbol_retrieve_group`, sorted by description, name, and ID.

## Entities
| Entity | Fields | Description |
|--------|--------|-------------|
| `Symbol` | group (int), id (int), name (String), description (String), visible (int) | A single symbol entry; implements `Comparator` for sorting |
| `SymbolInput` | symbol (Symbol) | Request wrapper for service operations |
| `SymbolOutput` | symbolList (List<Symbol>) | Response wrapper for retrieve operations |

## Business Rules
- Symbols are grouped by integer `group` identifier (e.g., group 23 = `CODECLASSID` constant).
- Each symbol has a unique combination of group + id within the database (enforced by stored procedure error codes).
- Error codes: 1=group not found, 2=ID in use, 3=name in use, 4=ID not found, 5=invalid visibility.
- Visibility flag (`visible`) controls whether a symbol appears in client UIs.
- Retrieved symbol groups are sorted by: description → name → id.

## Flows
1. **Create**: `ISymbolService.createSymbol(SymbolInput)` → `SymbolLibrary.createSymbol(Symbol)` → `ISymbolServiceDAO.createSymbol(Symbol)` → stored procedure `symbol_create`.
2. **Update**: Same chain → stored procedure `symbol_update`.
3. **Retrieve**: `ISymbolService.retrieveSymbolGroup(SymbolInput)` → `SymbolLibrary.retrieveSymbolGroup(group)` → stored procedure `symbol_retrieve_group` → sorted `List<Symbol>` returned.

## Compliance Relevance
- Low direct compliance exposure — symbols are reference/display data, not cardholder data or financial transactions.
- Indirectly relevant to **UDAAP** and **Reg E**: correct currency symbol display supports accurate cardholder disclosures.
- The database `jobsvc_test` referenced in test config suggests the symbol table may co-reside with job service data.

## Risks
- No bulk import or export capability; symbols must be managed one at a time.
- No soft-delete or versioning; an update overwrites without history.
- `visible` flag is an integer, not a boolean — contract between producer and consumer must be documented.
- Author attribution in code is `@author OFSS` (Onbe Finance Software Solutions, third-party vendor) — knowledge transfer and support responsibility must be confirmed.
