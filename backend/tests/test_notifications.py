"""
PikVaidya AI — Automated Tests: Notifications & Alerts API
===========================================================
Tests listing user alerts, marking as read, badge counts, and authorization.
"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.notification import Notification, NotificationType, NotificationSeverity


def test_list_notifications_empty(client: TestClient, auth_headers: dict):
    response = client.get("/api/v1/notifications", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_create_and_list_notifications(client: TestClient, auth_headers: dict, test_user: User, db: Session):
    # Seed notification
    n1 = Notification(
        user_id=test_user.id,
        title="High Blight Risk in Kolhapur",
        message="Prolonged humidity exceeds 85%. Scout tomato crops for early blight symptoms.",
        notification_type=NotificationType.WEATHER_ALERT,
        severity=NotificationSeverity.WARNING,
        is_read=False
    )
    db.add(n1)
    db.commit()

    # List
    response = client.get("/api/v1/notifications", headers=auth_headers)
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1
    assert items[0]["title"] == "High Blight Risk in Kolhapur"
    assert items[0]["is_read"] is False

    # Check unread count
    cnt_res = client.get("/api/v1/notifications/unread-count", headers=auth_headers)
    assert cnt_res.status_code == 200
    assert cnt_res.json()["unread_count"] == 1

    # Mark as read
    read_res = client.post(f"/api/v1/notifications/{items[0]['id']}/read", headers=auth_headers)
    assert read_res.status_code == 200
    assert read_res.json()["is_read"] is True

    # Re-check unread count
    cnt_res2 = client.get("/api/v1/notifications/unread-count", headers=auth_headers)
    assert cnt_res2.json()["unread_count"] == 0

