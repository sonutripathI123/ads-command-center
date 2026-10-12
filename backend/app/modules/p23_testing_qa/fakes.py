"""P23 — API mocks. FakeClaude replays recorded AI answers and records every prompt; FakeAdsAPI records Google Ads calls and
fails loudly on any mutation. Used by module tests so no network is ever touched."""
import json
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def list_fixtures() -> list[str]:
    return sorted(p.stem for p in FIXTURES.glob("*.json"))


class FakeAIError(Exception):
    def __init__(self, kind: str):
        super().__init__(kind)
        self.kind = kind


class FakeClaude:
    """answers = fixture name(s) or dict(s), replayed in order (the last one repeats). fail = None | 'rate_limit' |
    'refusal' | 'cut_off' | 'network' makes every call raise FakeAIError(kind), like the real SDK failure modes."""

    def __init__(self, answers: str | dict | list[str | dict], *, fail: str | None = None):
        self._answers = [answers] if isinstance(answers, (str, dict)) else list(answers)
        self.fail = fail
        self.prompts: list[str] = []

    def ask(self, prompt: str) -> dict:
        self.prompts.append(prompt)
        if self.fail:
            raise FakeAIError(self.fail)
        a = self._answers[min(len(self.prompts), len(self._answers)) - 1]
        return load_fixture(a) if isinstance(a, str) else a

    @property
    def calls(self) -> int:
        return len(self.prompts)


class MutationAttempted(AssertionError):
    pass


class FakeAdsAPI:
    """Read calls return the rows you give it; any call whose name looks like a mutation raises MutationAttempted."""

    def __init__(self, rows: dict[str, list[dict]] | None = None):
        self.rows = rows or {}
        self.calls: list[str] = []

    def read(self, resource: str) -> list[dict]:
        self.calls.append(f"read:{resource}")
        return list(self.rows.get(resource, []))

    def __getattr__(self, name: str):
        if "mutate" in name or name.startswith(("create_", "update_", "remove_", "delete_", "set_")):
            def _blocked(*a, **k):
                raise MutationAttempted(f"Google Ads mutation attempted: {name}")

            return _blocked
        raise AttributeError(name)
