# workbench_WAPP — Business Analyst View

## Business Purpose
The Workbench is a web-based internal operations portal used by Onbe (formerly Wirecard/NorthLane/Citi Prepaid) operations staff to configure and manage the prepaid card platform. It provides administrators, operations teams, and internal user roles with access to program configuration, job management, file processing, and affiliate management capabilities. The application identifier is `application_id=8` and `application_id=10` (CCC), pointing to its role in the core internal toolset.

## Capabilities
- **User and Group Management**: Add, update, activate/deactivate users and groups; manage CCC operator accounts
- **Affiliate/Program Configuration**: Create and manage affiliate programs, scopes, locales, skin templates, partner detail screens
- **Card Configuration**: FDR card profiles, DDA profiles, fee structures, fee credits, dormancy fee schedules, card purge configuration, card distribution
- **Promotion Management**: App promotions (events, PPD, spin), promotion fees, promotion labels, echeck expiration
- **Feature Configuration**: ACH features, recurring ACH, check-order features, payment reversal, instant issue, access level profiles, user management profiles
- **Job Management**: Add funds, change job status, schedule management, file upload/download, file pause/resume/rollback
- **Banker Operations**: Banker authorization/deauthorization, force settlement, notification management
- **Workflow Operations**: Workflow instance status updates, rollbacks, free-instance actions
- **Reporting Subscriptions**: Standard report subscriptions (add, update, on-demand, delete); 1099 tax reporting configuration
- **Configuration Management**: Scope management, JobSvc profile management, PSC template management, symbol configuration, EMEA configuration, One Platform affiliate configuration
- **Pre-Check Fraud**: Create, update, delete pre-check fraud controls; cardholder funding configuration
- **Quiz Management**: Create, manage, and activate quiz configurations (e.g., security/eligibility quizzes)

## Key Entities
| Entity | Description |
|--------|-------------|
| Affiliate | Program-level brand entity; has locales, skins, detail screens |
| AffiliateLocale | Language/locale variant for an affiliate |
| AffiliateLocaleCopy | Translated content copy for a locale |
| AffiliateLocaleSkin | Visual skin assignment for a locale |
| Group | Security role group for internal users |
| User | Internal Workbench operator with roles |
| Job | Batch processing job; has status, priority, schedule |
| WorkflowInstance | Business workflow instance with state machine |
| FDRCardProfile | FDR-specific card configuration profile |
| FDRDDAProfile | Demand deposit account profile |
| FeeStructure | Fee definition associated to program/promotion |
| Promotion | Program-level promotion (event/PPD/spin/echeck) |
| Subscription | Standard report subscription definition |
| Symbol | Program-level symbol/currency configuration |
| LabelType / LabelList | Configurable label sets used in cardholder-facing UIs |

## Business Rules
- Access to URLs is governed by role-based rules: `ROLE_REPORTS`, `ROLE_VIEW_PROGRAM`, `ROLE_DASHBOARD`, `ROLE_ORDER_HISTORY`, `ROLE_INENTORY_VIEW`, `ROLE_INSTANT_ISSUE_ADHOC_REORDER`
- Authentication uses Acegi Security with MD5 password encoding via `EcountMd5PasswordEncoder`
- Password management delegates to `passwordManager` and `eventManager` beans, indicating audit trails for authentication events
- Anonymous access is restricted to login, forgot-password, and index pages only
- File operations (upload, download, pause, resume, rollback) are subject to job-level status checks before execution
- Banker authorization actions require explicit approve/unauthorize workflow steps
- Blackout periods can be applied to suppress processing

## Key Flows
1. **Login**: User submits credentials → `VelocityCheckingAuthenticationProcessingFilter` → MD5 encode password → `minimalDaoAuthenticationProvider` → session context → role-based URL access
2. **File Processing**: File upload → validation → job creation → workflow instance start → status tracking → rollback/resume capability
3. **Configuration Change**: Operator selects config screen → submits form → action processor executes → stored procedure update on `CbaseappDataSource`
4. **Banker Flow**: Banker page display → authorize/unauthorize/force-settle → notification → confirmation page
5. **Job Scheduling**: Operator creates/updates schedule → `JobSchedulerService` invoked via HTTP Invoker proxy → external job scheduler applies change

## Compliance Considerations
- Authentication events flow through `eventManager` (audit logging)
- Role-based access control enforces least-privilege on all admin operations
- The `forceHttps` flag on `authenticationEntryPoint` is set to `false` — this is a significant compliance risk (PCI DSS Requirement 4.2.1)
- Application ID 8/10 integrations imply this system is within the cardholder data environment (CDE) scope given access to card profile and fee configuration
- Acegi Security is a legacy framework (pre-Spring Security), last maintained circa 2007

## Business Risks
- Highly centralized single UI for all configuration: a single misconfiguration can affect multiple programs
- No evidence of four-eyes approval or maker-checker workflow for configuration changes — all changes take effect immediately via stored procedures
- `forceHttps=false` means login credentials could traverse non-TLS channels
- MD5 password encoding is cryptographically broken per current standards (NIST SP 800-63B)
- Bulk file operations (pause/resume/rollback) operate without secondary confirmation; risk of unintended mass transaction impact
