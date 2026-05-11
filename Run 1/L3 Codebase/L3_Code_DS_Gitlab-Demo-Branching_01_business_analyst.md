# DS_Gitlab-Demo-Branching — Business Analyst Perspective

## Repository Overview

`DS_Gitlab-Demo-Branching` is a minimal demonstration repository created to illustrate and practise GitLab branching strategies within the Onbe Data Services team. The repository contains no production code, SQL, ETL packages, or reports. Its entire content consists of a `README.md` (44 bytes), two text files with placeholder content, and five empty zero-byte files. The README explicitly states "Delete me please." — indicating this repository was intended to be transient.

## Repository Content Inventory

| File | Size | Content |
|---|---|---|
| `README.md` | 44 bytes | "# Gitlab Demo Branching\n\nDelete me please." |
| `this is my dev work.txt` | 14 bytes | "demo blah blah" |
| `this is moar work.txt` | 19 bytes | "Hey this is my fix!" |
| `change101.txt` | 0 bytes | Empty |
| `change2.txt` | 0 bytes | Empty |
| `change3.txt` | 0 bytes | Empty |
| `change4.txt` | 0 bytes | Empty |
| `change5.txt` | 0 bytes | Empty |

## Business Purpose

From a business analyst perspective, this repository serves no production business function. Its purpose is entirely educational and process-oriented: it was used to demonstrate to the Data Services team how GitLab's branching and merge request workflow operates in practice. The file names and content ("this is my dev work", "Hey this is my fix", "change2–5") simulate the progression of commits across feature, development, and main branches during a training session.

## Implied Branching Strategy

The file naming pattern — `change2.txt`, `change3.txt`, `change4.txt`, `change5.txt`, `change101.txt` — suggests the demonstration walked through multiple sequential commits, likely across different branches (feature branches, a `develop` branch, and a `main`/`master` branch). The gap between `change5` and `change101` may indicate the demo revisited and added an additional change later, or a branch naming exercise that produced a higher change number.

The two descriptively named files (`this is my dev work.txt` and `this is moar work.txt`) simulate developer work product that would be committed to a feature branch and then merged into a shared branch through a merge request — the core GitLab flow being demonstrated.

## Business Process Implications

The existence of this repository in the production GitLab instance (alongside production repositories like `DS_ETL_sykes` and `DS_ETL_warehouse`) suggests the Onbe Data Services team adopted GitLab as a source control platform and conducted internal training to familiarise team members with the workflow. Key business process takeaways:

1. **Branching discipline is being actively taught**: The Data Services team recognised the need to establish source control discipline, which is a prerequisite for any CI/CD implementation.
2. **Developer onboarding asset**: New team members could be directed to this demo to understand the expected branching conventions before working on production repositories.
3. **Training gap**: The README's "Delete me please." instruction, still present at time of analysis, indicates a process governance gap — demo repositories are not being cleaned up after use, cluttering the namespace of production repositories.

## Governance Recommendation

This repository should be archived (not deleted, to preserve git history for audit purposes) or removed from the active namespace. Production repository lists and scanning tools should not include this repository in any automated analysis pipelines, as its content is not representative of production code. A naming convention such as `_DEMO_` or `_TRAINING_` prefix for non-production repositories would help distinguish them from production code repositories during scanning or compliance reviews.

From an Onbe process perspective, the repository demonstrates that the team has awareness of GitLab branching workflows. However, the lack of a formal branching strategy document (no `.gitlab-ci.yml`, no branch naming rules, no protection configuration visible) suggests the team is still maturing its DevOps practices. A formal GitLab workflow guide — covering branch naming (`feature/`, `fix/`, `release/`), merge request templates, and branch protection rules — should be documented and linked from the main Onbe Data Services GitLab group.

## Risk Profile

This repository carries essentially zero business risk in terms of data exposure, functionality, or compliance. There are no credentials, connection strings, PAN, DDA numbers, or personal data present. The risk is limited to namespace clutter and the small possibility that automated scanning tools might waste resources analysing this repository's empty files.

## Summary

`DS_Gitlab-Demo-Branching` is a training artefact. It has no production significance. From a business analyst perspective, its value has been fully expended upon completion of the branching demonstration for which it was created. The recommended action is archival and removal from active development tooling pipelines.
