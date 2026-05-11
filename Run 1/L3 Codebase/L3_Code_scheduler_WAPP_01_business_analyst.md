# Business Analyst Report: scheduler_WAPP

## Business Purpose

scheduler_WAPP is the enterprise-wide generic job scheduling service used across the Gen-1/Gen-2 prepaid card platform. It provides a centralised, clustered Quartz-based scheduler that allows other services (disbursement engines, card management, order processing, reconciliation) to register time-based and cron-based callbacks without each service managing its own scheduling infrastructure. The service was originally developed under the eCount brand (package `com.ecount.service.scheduler`) and is now operated by Onbe.

## Capabilities

- **Schedule CRUD operations**: `createSchedule`, `removeSchedule`, `updateSchedule`, `getScheduleStatus` exposed as Spring HTTP Invoker endpoints at `/scheduler.service`
- **Clustered execution**: Quartz 2 JDBC job store backed by a SQL Server `QRTZ2_*` schema, cluster check-in interval 20 seconds; multiple nodes share the same job store to prevent duplicate firing
- **Callback mechanisms**: HTTP Invoker callbacks delivered to registered application URLs when a schedule fires; extensible via `SchedulerCallbackTask` interface
- **Retry logic**: configurable `callback.maxRetryAttempts` and `callback.retryInterval` for failed callbacks
- **Health endpoint**: unauthenticated `/hc` returns "OK"

## Client and Cardholder Impact

Downstream clients of this service include systems that control card lifecycle events (statement generation, card expiry, promotional expiry), disbursement scheduling, and regulatory reporting batch jobs. A failure or mis-configuration in this service can delay cardholder payments, batch reconciliations, and regulatory filings. Because it runs in clustered mode, a database outage in the JobSvc SQL Server instance disables scheduling platform-wide.

## Business Rules in Code

- A schedule must have a valid `applicationName`, `scheduleTime`, `scheduleType` (SIMPLE or CRON), and `callbackPath`; enforced by `SchedulerInputValidatorImpl`
- CRON schedules additionally require a valid `cronExpression`
- Callback type defaults to HTTP Invoker; script-based callbacks are an alternative type
- Re-schedule (update) requires `applicationName` and `scheduleId`
- Status queries return `null` on failure rather than throwing, protecting callers from partial failures

## Regulatory Obligations

- **PCI DSS**: The scheduler itself does not store PANs or sensitive authentication data, but it triggers jobs in services that do. It is within the extended scope of the Cardholder Data Environment as a back-office orchestration component. Secure access to `/scheduler.service` is required under PCI DSS Requirement 6 (secure systems) and Requirement 7 (restrict access by business need to know)
- **GLBA / SOX**: Scheduling of financial batch jobs (reconciliation, settlement) is part of operational controls audited under SOX and GLBA operational risk programmes
- **NACHA / Reg E**: Batch ACH and refund job scheduling must meet NACHA settlement windows; scheduling failures could breach Reg E timing obligations for error resolution

## Key Business Risks

1. **Credential exposure in committed `.env` files**: Database usernames and passwords (`b2cstage`/`b2cstage`) are stored in plaintext in `.env` and `.env-dev` files in the repository. These reference QA-environment SQL Server instances on the legacy Wirecard/Northlane network (`q-lis-db01.nam.wirecard.sys`). If these credentials are reused or represent actual production-adjacent systems, this is a critical PCI DSS Requirement 8 violation
2. **No authentication on the scheduler endpoint**: The HTTP Invoker at `/scheduler.service` has no authentication mechanism visible in the web.xml or application XML configuration; any internal network caller can create or delete schedules
3. **Single database dependency**: All scheduling state resides in a single SQL Server instance (`JobSvcDataSource`); there is no documented failover or read-replica strategy, creating a single point of failure for the entire scheduling platform
4. **Callback URL injection**: The `callbackPath` is caller-supplied; there is no visible allowlist validation in `SchedulerInputValidatorImpl`, creating a potential server-side request forgery risk where a malicious internal caller schedules callbacks to arbitrary internal URLs
