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


def validate_distinct_places(origin: str, destination: str) -> None:
    """Same origin and destination isn't a trip - there's nothing for the
    flight/hotel/cab search to watch."""
    if origin.strip().upper() == destination.strip().upper():
        raise HTTPException(
            status_code=400,
            detail=f"Origin and destination can't both be {origin} - pick two different places.",
        )


def validate_occupancy(adults: int, rooms: int) -> None:
    """More rooms than people isn't a real booking - a room with nobody in
    it isn't something Hotelbeds (or anyone) can actually price. Confirmed
    live: this combination makes the real hotel search fail with a 400."""
    if rooms > adults:
        raise HTTPException(
            status_code=400,
            detail=f"Can't book {rooms} room(s) for {adults} adult(s) - rooms can't exceed adults.",
        )
