import sys
import time
from typing import Generator

import httpx
import pytest

sys.path.insert(0, ".")

BASE_URL = "http://localhost:8000"
TEST_USER = "test_api_" + str(int(time.time()))
TEST_EMAIL = TEST_USER + "@test.com"
TEST_PASSWORD = "TestApiPass123!"
ADMIN_USER = "admin"
ADMIN_PASSWORD = "admin123"


@pytest.fixture(scope="module")
def client() -> Generator[httpx.Client, None, None]:
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as c:
        yield c


@pytest.fixture(scope="module")
def admin_token(client: httpx.Client) -> str:
    resp = client.post(
        "/api/users/login",
        json={"account": ADMIN_USER, "password": ADMIN_PASSWORD},
    )
    assert resp.status_code == 200, "Admin login failed: " + resp.text
    return str(resp.json()["access_token"])


@pytest.fixture(scope="module")
def user_token(client: httpx.Client) -> str:
    # Register
    client.post(
        "/api/users/register",
        json={
            "username": TEST_USER,
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
            "confirm_password": TEST_PASSWORD,
        },
    )
    # Activate via MongoDB
    import asyncio

    from core.db.mongodb import mongodb

    mongodb.connect()

    async def _activate() -> None:
        from core.user.models import UserStatus

        await mongodb.database.users.update_one(
            {"username": TEST_USER},
            {"$set": {"status": UserStatus.ACTIVE.value, "is_active": True}},
        )

    loop = asyncio.new_event_loop()
    loop.run_until_complete(_activate())
    loop.close()

    # Login
    resp = client.post(
        "/api/users/login",
        json={"account": TEST_USER, "password": TEST_PASSWORD},
    )
    assert resp.status_code == 200, "Test user login failed: " + resp.text
    return str(resp.json()["access_token"])


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": "Bearer " + token}


class TestHealthEndpoint:
    def test_health_200(self, client: httpx.Client) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"


class TestSystemStatus:
    def test_status_200(self, client: httpx.Client) -> None:
        resp = client.get("/api/system/status")
        assert resp.status_code == 200
        assert "initialized" in resp.json()


class TestUserRegistration:
    def test_register_missing_422(self, client: httpx.Client) -> None:
        assert client.post("/api/users/register", json={}).status_code == 422

    def test_register_bad_email_422(self, client: httpx.Client) -> None:
        assert (
            client.post(
                "/api/users/register",
                json={"email": "bad", "username": "x", "password": "p", "confirm_password": "p"},
            ).status_code
            == 422
        )

    def test_register_pw_mismatch_422(self, client: httpx.Client) -> None:
        assert (
            client.post(
                "/api/users/register",
                json={
                    "email": "a@b.com",
                    "username": "ab",
                    "password": "P!",
                    "confirm_password": "D!",
                },
            ).status_code
            == 422
        )

    def test_register_short_pw_422(self, client: httpx.Client) -> None:
        assert (
            client.post(
                "/api/users/register",
                json={
                    "email": "a@b.com",
                    "username": "cd",
                    "password": "sh",
                    "confirm_password": "sh",
                },
            ).status_code
            == 422
        )

    def test_register_reserved_422(self, client: httpx.Client) -> None:
        assert (
            client.post(
                "/api/users/register",
                json={
                    "email": "a@b.com",
                    "username": "admin",
                    "password": TEST_PASSWORD,
                    "confirm_password": TEST_PASSWORD,
                },
            ).status_code
            == 422
        )


class TestUserLogin:
    def test_login_missing_422(self, client: httpx.Client) -> None:
        assert client.post("/api/users/login", json={}).status_code == 422

    def test_admin_login(self, client: httpx.Client) -> None:
        resp = client.post(
            "/api/users/login", json={"account": ADMIN_USER, "password": ADMIN_PASSWORD}
        )
        assert resp.status_code == 200
        d = resp.json()
        assert "access_token" in d
        assert "refresh_token" in d

    def test_login_wrong_pw_401(self, client: httpx.Client) -> None:
        assert (
            client.post(
                "/api/users/login", json={"account": ADMIN_USER, "password": "wrong"}
            ).status_code
            == 401
        )

    def test_login_nonexistent_401(self, client: httpx.Client) -> None:
        assert (
            client.post(
                "/api/users/login", json={"account": "nobody", "password": "Pass123!"}
            ).status_code
            == 401
        )


class TestProtectedEndpoints:
    def test_me_no_token_401(self, client: httpx.Client) -> None:
        assert client.get("/api/users/me").status_code == 401

    def test_me_valid(self, client: httpx.Client, admin_token: str) -> None:
        resp = client.get("/api/users/me", headers=auth_headers(admin_token))
        assert resp.status_code == 200
        assert "username" in resp.json()

    def test_me_bad_token_401(self, client: httpx.Client) -> None:
        assert (
            client.get("/api/users/me", headers={"Authorization": "Bearer invalid"}).status_code
            == 401
        )

    def test_put_me_no_token_401(self, client: httpx.Client) -> None:
        assert client.put("/api/users/me", json={"username": "x"}).status_code == 401


class TestRefreshToken:
    def test_refresh_missing(self, client: httpx.Client) -> None:
        resp = client.post("/api/users/refresh-token", json={})
        assert resp.status_code in (400, 422, 500)

    def test_refresh_ok(self, client: httpx.Client) -> None:
        login = client.post(
            "/api/users/login", json={"account": ADMIN_USER, "password": ADMIN_PASSWORD}
        )
        rt = login.json()["refresh_token"]
        resp = client.post("/api/users/refresh-token", json={"refresh_token": rt})
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_refresh_bad_401(self, client: httpx.Client) -> None:
        assert (
            client.post("/api/users/refresh-token", json={"refresh_token": "bad"}).status_code
            == 401
        )


class TestCacheEndpoints:
    def test_stats_no_auth(self, client: httpx.Client) -> None:
        assert client.get("/api/cache/stats").status_code == 401

    def test_stats_admin(self, client: httpx.Client, admin_token: str) -> None:
        assert client.get("/api/cache/stats", headers=auth_headers(admin_token)).status_code == 200

    def test_cleanup_no_auth(self, client: httpx.Client) -> None:
        assert client.delete("/api/cache/cleanup").status_code == 401

    def test_clear_no_auth(self, client: httpx.Client) -> None:
        assert client.delete("/api/cache/clear").status_code == 401

    def test_details_no_auth(self, client: httpx.Client) -> None:
        assert client.get("/api/cache/details").status_code == 401

    def test_backend_no_auth(self, client: httpx.Client) -> None:
        assert client.get("/api/cache/backend-info").status_code == 401


class TestFavoritesAuth:
    def test_list_no_auth(self, client: httpx.Client) -> None:
        assert client.get("/api/favorites/").status_code == 401

    def test_add_no_auth(self, client: httpx.Client) -> None:
        assert client.post("/api/favorites/", json={"stock_code": "600519"}).status_code == 401

    def test_delete_no_auth(self, client: httpx.Client) -> None:
        assert client.delete("/api/favorites/600519").status_code == 401


class TestScreeningAuth:
    def test_fields_no_auth(self, client: httpx.Client) -> None:
        assert client.get("/api/screening/fields").status_code == 401

    def test_run_no_auth(self, client: httpx.Client) -> None:
        assert (
            client.post(
                "/api/screening/run", json={"market": "A_STOCK", "conditions": {}}
            ).status_code
            == 401
        )


class TestStockDataAuth:
    def test_quote_no_auth(self, client: httpx.Client) -> None:
        assert client.get("/api/stocks/600519.SH/quote").status_code == 401

    def test_fundamentals_no_auth(self, client: httpx.Client) -> None:
        assert client.get("/api/stocks/600519.SH/fundamentals").status_code == 401

    def test_kline_no_auth(self, client: httpx.Client) -> None:
        assert client.get("/api/stocks/600519.SH/kline").status_code == 401

    def test_search_no_auth(self, client: httpx.Client) -> None:
        assert client.get("/api/stock-data/search?keyword=test").status_code == 401

    def test_list_no_auth(self, client: httpx.Client) -> None:
        assert client.get("/api/stock-data/list").status_code == 401


class TestErrorHandling:
    def test_404(self, client: httpx.Client) -> None:
        assert client.get("/api/nonexistent").status_code == 404

    def test_422_bad_json(self, client: httpx.Client) -> None:
        assert (
            client.post(
                "/api/users/register",
                content="not json",
                headers={"Content-Type": "application/json"},
            ).status_code
            == 422
        )

    def test_401_bad_header(self, client: httpx.Client) -> None:
        assert (
            client.get("/api/users/me", headers={"Authorization": "NotBearer x"}).status_code == 401
        )
