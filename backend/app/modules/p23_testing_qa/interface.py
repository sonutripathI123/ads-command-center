"""P23 — public interface (QA harness for tests and the QA command line).

    from app.modules.p23_testing_qa.interface import FakeClaude, FakeAdsAPI, load_fixture, audit_anonymous
"""
from app.modules.p23_testing_qa.audit import (
    PUBLIC_ROUTES,
    Finding,
    audit_anonymous,
    audit_read_only_writes,
    list_routes,
)
from app.modules.p23_testing_qa.fakes import (
    FakeAdsAPI,
    FakeAIError,
    FakeClaude,
    MutationAttempted,
    list_fixtures,
    load_fixture,
)

__all__ = ["PUBLIC_ROUTES", "Finding", "audit_anonymous", "audit_read_only_writes", "list_routes",
           "FakeAdsAPI", "FakeAIError", "FakeClaude", "MutationAttempted", "list_fixtures", "load_fixture"]
