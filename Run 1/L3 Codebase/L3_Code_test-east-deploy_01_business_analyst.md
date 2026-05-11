# Business Analyst Report — test-east-deploy

## Business Purpose

`test-east-deploy` is a throwaway (sandbox) Spring Boot web application created explicitly to validate the Onbe "east-deploy" CI/CD build and deployment workflow pipeline. Its `pom.xml` description field states: "Throwaway test app for validating east-deploy build/deploy workflows." It has no business function of its own; its sole purpose is to exercise the GitHub Actions workflow (`Onbe/om-ci-setup/.github/workflows/build-east-java.yml`) so that the deployment pipeline can be tested independently of any production service.

## Capabilities

- Produces a WAR artifact (`test-east-deploy.war`) targeting Tomcat 10.x.
- Exposes a minimal Spring Boot web layer with no business endpoints.
- Triggers the shared `build-east-java.yml` reusable workflow on push to `main`, `release/**`, or `feature/**` branches.
- Optionally skips tests and optionally deploys to GitHub Packages via the `DEPLOY_TO_PACKAGES: true` flag.
- Supports manual workflow dispatch with `skip_tests` and `deploy_to_production` inputs (defined in `cicd-deployment.yml`).

## Client and Cardholder Impact

None. This is a purely internal infrastructure validation tool with no cardholder or client data, no payment processing logic, and no production routing. It should never be deployed to production or receive real traffic.

## Business Rules in Code

None meaningful. The only business rule is the application name and version (`spring.application.name=test-east-deploy`, `spring.application.version=@project.version@`) derived from Maven filtering in `application.properties`.

## Regulatory Obligations

Minimal direct obligations since this is a non-production, non-data-processing application. However:
- **PCI DSS Req. 6.4**: The build pipeline itself — which this repo exercises — must conform to secure development lifecycle requirements. The use of a shared reusable workflow (`om-ci-setup`) ensures consistent build security controls are applied.
- **PCI DSS Req. 6.2 / NIST CSF**: Dependency management via Spring Boot 3.4.2 parent POM ensures that known-vulnerability scanning can be applied centrally.

## Key Business Risks

1. **Pipeline validation gap**: If this repo is used as the sole test for the east-deploy pipeline, failures here block all other repos that use the same shared workflow. The repo should be actively maintained and kept green.
2. **Credential leakage risk**: The workflow uses `PAT_TOKEN_PACKAGE` as a GitHub secret. If this token has broader permissions than package-publish, a compromise of the workflow could expose the entire GitHub Organization package registry.
3. **Test skipping in workflow**: The `skip_tests` input defaults to `false` but can be set to `true` manually. In a compliance-gated environment, test skipping should require approval.
