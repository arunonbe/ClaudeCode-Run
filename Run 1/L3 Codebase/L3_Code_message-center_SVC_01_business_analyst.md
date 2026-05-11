# Business Analyst Report — message-center_SVC

## 1. Service Identity and Business Purpose

`message-center_SVC` is a Gen-2 (legacy) notification management service within the Onbe payments platform. Its commercial role is to serve as the internal message store for cardholder-facing communications — primarily the in-application inbox messages that appear inside the cardholder self-service portal (OnePlatform / My Payment Vault). It is **not** a real-time transactional notification dispatcher (that role belongs to the newer `notification-framework_SVC`). Instead, this service manages the lifecycle of structured messages: creation, retrieval, status changes, delivery to end-users by affiliate and locale, and soft deletion.

The business value proposition is twofold: (1) it enables program operators and affiliate administrators to author and push targeted messages to specific cardholder segments identified by `memberId`, `affiliateId`, and application, and (2) it provides an audit-traceable message status trail (draft → active → archived) with comment support. This supports compliance obligations such as Regulation E adverse action notice delivery confirmation and UDAAP-driven transparent communications.

## 2. Functional Capabilities

The service exposes the following functional operations, all ultimately delegated to the SQL Server stored-procedure layer through the `MessageCenter-datasource.xml` Spring bean wiring:

| Operation | Interface Method | DAO Stored Procedure |
|---|---|---|
| List messages (admin view) | `getMessagesList` | `GetMessagesListSP` |
| List messages (cardholder view) | `getMessagesListForApplication` | `MessagesListForApplicationSP` |
| Create or update message | `createOrUpdate` | `CreateOrUpdateMessageSP` |
| Retrieve message detail | `retrieveMessageDetails` | `RetrieveMessageDetailSP` |
| Change message status | `changeMessageStatus` | `ChangeMessageStatusSP` |
| Delete message for user | `deleteMessageForUser` | `DeleteMessageForUserSP` |
| Get affiliate locales | `getLocalesForAffiliate` | `GetLocalesForAffiliateSP` |
| Get message config values | `getMessageConfigValues` | `GetMessageConfigValuesSP` |
| Get message comments | `getMessageComments` | `GetMessageCommentsSP` |
| Get message content | `getMessageContent` | `GetMessageContentSP` |

The interface hierarchy is defined in `message-common/src/main/java/com/ecount/service/message/IMessageCenterCoreService.java` and `IMessageApplicationService.java`. The split reflects two consumer perspectives: platform operators/admins (core service) and end-user applications (application service).

## 3. Consumer Segments and Integration Touch-Points

- **Cardholder portal (MPV / OnePlatform)**: calls `getMessagesListForApplication` supplying `memberId`, `affiliateId`, application ID, and locale. The response drives the in-app notification bell/inbox.
- **Administrative tooling (ClientZone, CSA)**: calls `getMessagesList` and `createOrUpdate` to author program-level notices.
- **External consumers via XML-RPC**: The `MessageServiceClient.java` in `message-common` indicates the service exposes an XML-RPC interface, consistent with the broader eCount Gen-2 XML-RPC service mesh pattern. The WAR is deployed to a URL path `/services/MessageCenterWebServices` (per `.github/workflows/deployment.yml`, line 38, `BACKEND_SUFFIX`).

## 4. Business Rules and Message Lifecycle

Messages follow a lifecycle with discrete status codes managed through `changeMessageStatus`. Business rules enforced at the stored-procedure level include:

- **Affiliate scoping**: messages are always affiliate-specific; cross-affiliate delivery is prevented at the query layer.
- **Locale support**: `getLocalesForAffiliate` fetches valid locale codes, enabling internationalized message content. `MessageContentDataBean` carries content per locale.
- **Soft deletion**: `deleteMessageForUser` removes the message from a specific user's view without purging the master record, preserving audit history.
- **Comment tracking**: `CommentsDataBean` and `getMessageComments` allow operational teams to annotate message status changes, supporting internal audit and compliance review processes.

## 5. Business Risks and Gaps

1. **No delivery confirmation**: The service stores messages but has no mechanism to confirm cardholder read receipt, which is relevant for Regulation E adverse action notice obligations.
2. **No push / multi-channel**: SMS, email, and push channels are not within this service's scope; this creates a fragmented notification picture when cross-referencing with `notification-framework_SVC`.
3. **Legacy XML-RPC transport**: Consumer-facing integration through XML-RPC over HTTP is a proprietary protocol that limits composability and increases integration risk for new NexPay Gen-3 consumers.
4. **No rate limiting**: There is no visible rate-limit or deduplication guard on `createOrUpdate`, which could allow duplicate message flooding if called by a misbehaving upstream.
5. **Locale data in relational store**: Locale-specific content stored in SQL Server requires schema changes for new locale additions; a content-management approach would be more flexible.

## 6. Regulatory Touchpoints

As a cardholder communication channel, this service is in scope for:
- **UDAAP** (Unfair, Deceptive, or Abusive Acts or Practices): message content accuracy and timing obligations.
- **Regulation E**: adverse action notices and fee disclosures delivered through this inbox channel must be timely and complete.
- **CCPA / GDPR**: `MessageDataBean` carries member identifiers; any PII in message body content is subject to data subject rights (erasure, access). The soft-delete pattern may not fully satisfy erasure requests if message body contains PII.
