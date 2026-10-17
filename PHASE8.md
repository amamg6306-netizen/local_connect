# Phase 8 — Request recovery + release verification (17 October 2026)

This is a cumulative code package built on the Phase 7 ZIP. Phase 8 fixed the failure-recovery path for requirement claims and request status updates, added a business-specific requirements URL (original URL preserved), and added three offline and three real Flask integration regression cases.

**Executed:** 150 offline tests passed + 18 subtests, SQLite ORM/DDL compile, 62 Jinja templates, 93 PHP syntax checks, Node dropdown and security scan.  
**NOT executed successfully:** Flask client tests, MySQL 8 server integration, GitHub CI, Resend inbox delivery, Render staging/browser acceptance.  
**Failing gate:** Public Privacy/Terms development text; requires actual approved replacement, not a placeholder bypass.

See `LOCALJOIN_PHASE8_RELEASE_REPORT.md` and `LOCALJOIN_PHASE8_TEST_RESULTS.md` for exact evidence and release blockers.

**Decision: HOLD / NOT PRODUCTION-READY / NOT DEPLOYED.**
