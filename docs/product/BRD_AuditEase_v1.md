# Business Requirements Document (BRD) - AuditEase v1

## Business Goals
*   **Trust**: Move from "Student Project" vibe to "Enterprise Auditor" vibe (PDF Reports).
*   **Retention**: Stop users from churning after one scan (Historical Trending).
*   **Monetization**: Gate historical data and PDF downloads behind the Pro Plan ($49/mo).

## Success Metrics (KPIs)
*   **Activation**: % of users who generate a PDF within 5 minutes.
*   **Retention**: % of users who set up the "Gatekeeper" Action.
*   **Revenue**: Conversion rate from Free to Pro (triggered by PDF download attempt).

## User Personas
*   **The "Stressed CTO"**: Needs a report now for a board meeting.
*   **The "Lazy Developer"**: Wants compliance to happen automatically without manual screenshots.

## Core Use Cases (The "Happy Path")
### Onboarding
1.  User connects GitHub
2.  Auto-Scan triggers
3.  User sees "F" Grade
4.  User fixes issue
5.  User sees "A" Grade
6.  User downloads PDF

### Enforcement
1.  Dev opens PR with public repo
2.  AuditEase Gatekeeper fails the build
3.  Dev fixes setting
4.  Build passes

## Constraints
*   **Privacy**: We must NEVER clone source code. Metadata only.
*   **Scopes**: We require checks:write but must justify it to the user.
