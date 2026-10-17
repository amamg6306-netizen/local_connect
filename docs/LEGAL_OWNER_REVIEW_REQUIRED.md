# Privacy Policy & Terms — owner/legal sign-off required

The public `templates/main/static.html` now has substantive Privacy Policy and Terms of Use drafts instead of development-only placeholder warnings. **They are a drafting starting point, not approved legal documents or a representation of compliance.** `scripts/check_release_content.py` checks document completeness only. Do not conflate a green `release-content` CI job with legal approval or permission to deploy.

Before any production release, the website operator and a qualified adviser (where needed) must review and approve:

- The identity and contact details of the actual data controller/business operating Localjoin, including an appropriate privacy grievance contact.
- Actual data categories, precise/public location handling, customer-to-provider request sharing, and mail/hosting/payment processor relationships.
- Applicable consent and cookie disclosures, account eligibility, Indian data-protection duties, user rights and grievance handling.
- Record-specific retention periods, account deletion procedures, safeguards, international transfers where applicable, and operational ability to honor promises.
- Payment/plan/cancellation/refund obligations, provider disputes, user obligations and local consumer-law requirements.
- The finalized policy effective date, notification plan, and whether user acceptance is necessary for material updates.

The operator must save the legal review record and a link to that evidence in the final release evidence checklist (`privacy_terms_approval`). That check intentionally cannot be passed by editing this document or deleting development-marker text.

## Production and CI distinction

- `release-content`: public copy is structurally complete, has no known development placeholders. It is **not** legal approval.
- `scripts/check_release_evidence.py`: production gate still expects `privacy_terms_approval` and other independently verified checks before promotion.
- `integration` and `disposable-mysql`: runtime checks, independent of this legal draft. Do not add `--ignore` or skip tests to turn them green.
