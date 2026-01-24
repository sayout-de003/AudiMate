import pytest
from django.urls import reverse
from unittest.mock import patch, MagicMock
from django.db import DatabaseError

@pytest.mark.django_db
class TestHealthCheck:
    def test_health_check_success(self, client):
        """
        Test /health/ returns 200 when DB and Redis are up.
        """
        # We don't necessarily need to mock if we have a real DB/Redis in test env,
        # but mocking ensures isolation and we can test failures easily.
        # However, for "Success", let's try real connection if available (or mock for stability).
        # Let's mock to be safe and deterministic.
        
        with patch("config.views.connection") as mock_conn, \
             patch("config.views.get_redis_connection") as mock_redis:
            
            # Mock DB success
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            
            # Mock Redis success
            mock_redis_conn = MagicMock()
            mock_redis.return_value = mock_redis_conn
            mock_redis_conn.ping.return_value = True

            url = reverse("health_check")
            response = client.get(url)
            
            assert response.status_code == 200, response.content
            data = response.json()
            assert data["status"] == "healthy"
            assert data["db"] == "up"
            assert data["redis"] == "up"

    def test_health_check_db_failure(self, client):
        """
        Test /health/ returns 500 when DB is down.
        """
        with patch("config.views.connection") as mock_conn, \
             patch("config.views.get_redis_connection") as mock_redis:
            
            # Mock DB failure
            mock_conn.cursor.side_effect = DatabaseError("DB Down")
            
            # Mock Redis success (still checks redis even if DB fails? Yes, code continues)
            mock_redis_conn = MagicMock()
            mock_redis.return_value = mock_redis_conn
            mock_redis_conn.ping.return_value = True

            url = reverse("health_check")
            response = client.get(url)
            
            assert response.status_code == 500
            data = response.json()
            assert data["status"] == "unhealthy"
            assert data["db"] == "down"
            assert data["redis"] == "up"

    def test_health_check_redis_failure(self, client):
        """
        Test /health/ returns 500 when Redis is down.
        """
        with patch("config.views.connection") as mock_conn, \
             patch("config.views.get_redis_connection") as mock_redis:
            
            # Mock DB success
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            
            # Mock Redis failure
            mock_redis.side_effect = Exception("Redis Down")

            url = reverse("health_check")
            response = client.get(url)
            
            assert response.status_code == 500
            data = response.json()
            assert data["status"] == "unhealthy"
            assert data["db"] == "up"
            assert data["redis"] == "down"
