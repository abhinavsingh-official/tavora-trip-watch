"""Shared date sanity checks for TripRequests - called on create, edit,
and before every price check, so an invalid request can't slip through
any of those paths.
"""

from datetime import date

from fastapi import HTTPException


def validate_date_order(outbound_date: date, return_date: date) -> None:
    """A return on or before the outbound date isn't a real trip - reject
    it instead of pricing nonsense."""
    if return_date <= outbound_date:
        raise HTTPException(
            status_code=400,
            detail=(
                "Return date must be after the outbound date "
                f"(got outbound {outbound_date}, return {return_date})."
            ),
        )
