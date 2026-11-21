"""SimController - in-memory price overrides, set via /api/lab/override and
read by pricing.py. Clears on process restart, which is fine for V1 since
persistence-across-restart is a V2+ concern tied to real failure scenarios
(docs/versions/V1_MODULES.md).
"""

COMPONENTS = ("flight", "hotel", "cab")


class SimController:
    def __init__(self) -> None:
        # {(request_id, component): price}
        self._overrides: dict[tuple[int, str], float] = {}

    def set_override(self, request_id: int, component: str, price: float) -> None:
        if component not in COMPONENTS:
            raise ValueError(f"Unknown component '{component}', expected one of {COMPONENTS}")
        self._overrides[(request_id, component)] = price

    def get_override(self, request_id: int, component: str) -> float | None:
        return self._overrides.get((request_id, component))

    def reset(self) -> None:
        self._overrides.clear()


sim_controller = SimController()
