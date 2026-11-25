"""Shared sanity checks for TripRequests, called on create, edit, and before every price check."""

from datetime import date

from fastapi import HTTPException


def validate_date_order(outbound_date: date, return_date: date) -> None:
    """A return on or before the outbound date isn't a real trip."""
    if return_date <= outbound_date:
        raise HTTPException(
            status_code=400,
            detail=(
                "Return date must be after the outbound date "
                f"(got outbound {outbound_date}, return {return_date})."
            ),
        )


def validate_distinct_places(origin: str, destination: str) -> None:
    """Same origin and destination isn't a trip."""
    if origin.strip().upper() == destination.strip().upper():
        raise HTTPException(
            status_code=400,
            detail=f"Origin and destination can't both be {origin} - pick two different places.",
        )


def validate_occupancy(adults: int, rooms: int) -> None:
    """More rooms than people isn't bookable; confirmed live, Hotelbeds 400s on this combination."""
    if rooms > adults:
        raise HTTPException(
            status_code=400,
            detail=f"Can't book {rooms} room(s) for {adults} adult(s) - rooms can't exceed adults.",
        )
