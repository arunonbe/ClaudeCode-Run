# Data Architect Report — xml-rpc_LIB

## Data Models

The library defines the following data models for the RPC protocol:

- **`XmlRPCRequest`**: HTTP request metadata — `txID`, `agentName`, `agentAffiliate`, `globalRequestID`, `agentContext`, `interfaceName`, `methodName`, `sasiContext`, `input` (raw XML string).
- **`IOutput`** / **`OutputBase`**: Interface and base class for all RPC response objects. Contains a `Result` with `code` (int) and `message` (String).
- **`Result`**: Return code and message wrapper. Non-zero code indicates failure.
- **`XmlRPCObjectDefaultComponentTypes`**: Type mapping registry for collections in the XML-to-object mapper — allows specifying element types for `List<?>` fields during deserialization.
- **`IOutput.setResult()` / `getResult()`**: Standard output contract for all RPC response objects.

The library does not define domain-level data models (no cardholder, account, or transaction objects). Domain objects are defined in the consuming services and passed through the library's serialization layer.

## Sensitive Data

The library **serializes and deserializes all domain data** that passes through the Gen-1/Gen-2 platform, including:
- Cardholder PII (name, SSN via `secure_profile.federal_id`, date of birth, address).
- Account data (account IDs, balances).
- Transaction data (amounts, dates, identifiers).
- Card data (card status, card IDs).

The library itself does not know the type of data — it serializes any Java object to/from XML. Sensitive data protection (encryption, masking) must be enforced by the consuming services, not by this library. There is no evidence of PAN or CVV-level data in the RPC layer itself, as those are handled at the processor level, but PII flows freely through XML-RPC.

### Debug Logging Risk

`XmlRPCServletHelper.java` lines 280–285 and 309–323 log full input objects (`PrintObject.printXMLObject(request)`) and output objects at DEBUG level. If DEBUG logging is enabled in production, full RPC payloads (including PII) are written to log files. This is a significant data exposure risk.

## Encryption Status

**No encryption on the RPC channel.** The wire format is:
- HTTP POST with XML body (content type `application/x-mapxml`).
- No TLS enforcement in the library — TLS is the responsibility of the hosting servlet container.
- If the internal network between services does not enforce TLS, all RPC traffic (including PII) is in plaintext on the network.
- The `commons-httpclient` (3.x) used by `XMLRPCClient` does not enforce modern TLS by default.

## Database Schemas

None. The library does not access databases directly. All data persistence is handled by the Spring beans that the library dispatches to.

## Data Flows

1. **Inbound RPC**: HTTP POST to `XmlRPCServlet.doPost()` → `XmlRPCServletHelper.buildXmlRPCRequest()` → header parsing → `XmlRPCToObjectMapper.toObject()` → Spring bean dispatch → `XmlRPCFromObjectMapper.fromObject()` → HTTP response.
2. **Outbound RPC**: `XMLRPCClient.invokeXMLRPCCall()` → `XMLRPCServiceLocator.getServiceAddress()` → `XMLRPCClientUtils.invokeXMLRPCCall()` (HTTP POST) → response unmarshal.
3. **Request context**: Agent, program ID, global request ID bound to `ThreadLocal<RequestContext>` for the duration of each request — cleared in `finally` block.
4. **MDC logging**: `MDCWriter` writes global request ID to the logging MDC (Mapped Diagnostic Context) for log correlation.

## Retention Concerns

- RPC request and response XML, if logged at DEBUG level, constitutes a log record of all data passing through the system. Log retention policies must apply to these files.
- The `globalRequestID` provides end-to-end tracing across multiple RPC hops — this is valuable for audit but must be protected from unauthorized access.

## PCI DSS Compliance

- **Req. 4.2**: Cardholder data must be protected in transit. The XML-RPC HTTP channel has no built-in TLS enforcement. Network-level controls must compensate.
- **Req. 3.3.1**: Sensitive authentication data must not be stored after authorization. DEBUG logging of RPC payloads could violate this if authentication data is in the request/response.
- **Req. 10.3**: Audit logs must include sufficient data to reconstruct events. The `globalRequestID` threading enables this, but only if logs are protected and retained appropriately.
