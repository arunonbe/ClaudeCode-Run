# service-tester_WAPP — Business Analyst View

## Business Purpose
`service-tester_WAPP` is an internal developer/QA tool — a web application that allows authorised users to browse available backend service methods, compose XML/Java-object-based requests, invoke those methods, and inspect responses. It is used for manual integration testing and debugging of the Onbe/Citi Prepaid platform's service layer. It is not a customer-facing application.

The legacy branding (`citi-prepaid.gif`, `citi-footer.gif` in webapp resources) and original SCM URL (GitLab at `northlane`) indicate this was carried over from the Wirecard/Northlane/Citi Prepaid era.

## Capabilities
1. **Service Method Browser**: Dynamically loads service methods from Spring-injected services (via `DynamicMethodLoader` and `StaticMethodLoader`) and displays them to authenticated users.
2. **Request Builder**: Generates default input objects for service methods using `BeanGenerator` (reflection-based bean generation with configurable default values).
3. **Service Invocation**: Invokes selected service method with user-supplied XML-marshalled input and returns the result.
4. **User Management (Admin)**: Admin portal to create/update/delete users, assign service access roles with expiration dates, view recent users, and request access.
5. **Context Switching**: Allows users to switch between different service contexts (configured in Spring XML).
6. **Email Notifications**: MailService for sending notifications via SMTP (`mail.ecount.com`).
7. **Console and Swing clients**: Standalone command-line and Swing desktop clients in addition to the web interface.

## Entities
| Entity | Description |
|---|---|
| `User` | Username, name, email, default context/method |
| `Access` | Maps user to resource name with roles |
| `AdminAccess` | Special marker access granting admin privileges |
| `Role` | Named role with optional expiration date |
| `Context` | A Spring ApplicationContext holding a set of service beans |
| `ServiceMethod` | A single invocable method with name, role constraint, and default input |

## Business Rules
- Access to service methods is role-controlled; each method can have an assigned `Role`.
- Roles have optional expiration dates stored in the database.
- Admin users have a separate `AdminAccess` record in the database.
- Default user is stored in a `default_user` database table.
- Service contexts can be loaded dynamically from JARs at runtime.

## Process Flows
1. User navigates to application → form-based login (`/login.html`).
2. Authenticated user selects a service context and method.
3. `ServiceTestPageController` retrieves the method, builds default input, renders the form.
4. User submits XML input → service is invoked via reflection → response rendered.
5. Admin: `AdminPageController` manages users, access, and roles via JDBC.

## Compliance Relevance
- This tool can invoke production service methods directly. If deployed against production, an unauthorised user gaining access could trigger payments, ACH operations, or card activations.
- **PCI DSS Req 6/7**: Internal tools accessing production cardholder data environments must be access-controlled, audited, and covered by vulnerability management.
- Access expiration (role `expires` field) provides some governance for time-limited access.

## Risks
- Dynamic JAR loading at runtime (`JarLoader`) — untrusted JARs added to the classpath could execute arbitrary code.
- `web.xml` security constraint uses `<role-name>*</role-name>` — permits any authenticated role to access protected URLs, not role-specific access control.
- No CSRF protection observed in `web.xml` configuration.
- SMTP host hardcoded as `mail.ecount.com` — legacy Ecount mail server.
