"""Shared request-input sanity checks (Sec. 05: "explain your check-in,
check-out and transfer-buffer assumptions and reject combinations that
violate them"). Called from every place a TripRequest's dates can be set or
already exist - creation, editing, and before a price check - so a request
that was invalid when created can't be checked either, even if it slipped
in before this validation existed.
"""

from datetime import date

from fastapi import HTTPException


def validate_date_order(outbound_date: date, return_date: date) -> None:
    """A return date on or before the outbound date describes a trip that
    never actually happens - there's no outbound leg, no stay, and no return
    leg to price. Rejected outright rather than silently priced as if it
    made sense."""
    if return_date <= outbound_date:
        raise HTTPException(
            status_code=400,
            detail=(
                "Return date must be after the outbound date "
                f"(got outbound {outbound_date}, return {return_date})."
            ),
        )
