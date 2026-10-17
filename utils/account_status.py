"""Security policy for restoring administrator-blocked accounts.

An administrator can remove a block, but cannot grant email verification.
This policy has no database or Flask dependency so it is testable offline.
"""
from __future__ import annotations


def status_after_unblock(email_verified_at: object | None, verification_required: bool) -> str:
    if verification_required and email_verified_at is None:
        return "pending"
    return "active"
