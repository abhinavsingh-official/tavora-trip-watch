"""
A real, severe bug caught live in production: every single notification
review crashed with a 500 ("4 validation errors for NotificationReviewOut
... Field required") because the endpoint handed the bare Notification ORM
row straight to a schema that needs origin/destination/total_price/
quote_status - fields that don't exist on that row at all (see
list_notifications, which builds them explicitly; review_notification
never did). No existing test exercised this success path - every prior
`/review` test only covers a rejection (ownership, paused/cancelled)
that returns before ever reaching this code.

create_observation is mocked here since it makes a real supplier call -
this is testing the response shape, not pricing itself.
"""

from datetime import date, timedelta
from unittest.mock import patch

from app.models import Notification, PriceObservation, TripRequest


def test_reviewing_a_notification_returns_a_full_itinerary_not_a_500(client, db, two_users):
    user_a, _ = two_users
    trip_request = TripRequest(
        user_id=user_a.id,
        origin="Mumbai",
        destination="Goa",
        outbound_date=date(2026, 12, 26),
        return_date=date(2026, 12, 29),
        adults=2,
        rooms=1,
        budget_inr=35000,
    )
    db.add(trip_request)
    db.commit()
    db.refresh(trip_request)

    original_observation = PriceObservation(
        request_id=trip_request.id, status="complete", total_price=30000
    )
    db.add(original_observation)
    db.commit()
    db.refresh(original_observation)

    notification = Notification(
        request_id=trip_request.id, observation_id=original_observation.id
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)

    fresh_observation = PriceObservation(
        request_id=trip_request.id,
        status="complete",
        total_price=29500,
        flight_status="complete",
        hotel_status="complete",
        cab_status="complete",
    )
    db.add(fresh_observation)
    db.commit()
    db.refresh(fresh_observation)

    with patch("app.routers.notifications.create_observation", return_value=fresh_observation):
        response = client.post(
            f"/api/notifications/{notification.id}/review?user_id={user_a.id}"
        )

    assert response.status_code == 200
    body = response.json()
    assert body["notification"]["origin"] == "Mumbai"
    assert body["notification"]["destination"] == "Goa"
    assert body["notification"]["total_price"] == 30000
    assert body["notification"]["quote_status"] == "complete"
    assert body["notification"]["held_until"] is not None
    assert body["current_observation"]["total_price"] == 29500
