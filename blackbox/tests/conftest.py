import os
from dataclasses import dataclass
from decimal import Decimal
from typing import Generator

import pytest
import requests

DEFAULT_TIMEOUT = float(os.getenv("QUICKCART_TIMEOUT", "10"))


@dataclass(frozen=True)
class ApiContext:
    base_url: str
    roll_number: str
    user_id: str
    timeout: float = DEFAULT_TIMEOUT

    @property
    def user_headers(self) -> dict[str, str]:
        return {
            "X-Roll-Number": self.roll_number,
            "X-User-ID": self.user_id,
            "Content-Type": "application/json",
        }

    @property
    def admin_headers(self) -> dict[str, str]:
        return {
            "X-Roll-Number": self.roll_number,
            "Content-Type": "application/json",
        }

    def url(self, path: str) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return path
        return f"{self.base_url}{path}"


@pytest.fixture(scope="session")
def api_context() -> ApiContext:
    base_url = os.getenv("QUICKCART_BASE_URL", "http://127.0.0.1:8080").rstrip("/")
    roll_number = os.getenv("QUICKCART_ROLL_NUMBER")
    user_id = os.getenv("QUICKCART_USER_ID")

    missing = [
        name
        for name, value in {
            "QUICKCART_ROLL_NUMBER": roll_number,
            "QUICKCART_USER_ID": user_id,
        }.items()
        if not value
    ]
    if missing:
        pytest.skip(
            "Set the following environment variables before running the black-box suite: "
            + ", ".join(missing)
        )

    health_headers = {"X-Roll-Number": roll_number}
    try:
        response = requests.get(
            f"{base_url}/api/v1/admin/products",
            headers=health_headers,
            timeout=DEFAULT_TIMEOUT,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        pytest.skip(
            f"QuickCart server is unreachable at {base_url}. Start the API container first. {exc}"
        )

    return ApiContext(base_url=base_url, roll_number=roll_number, user_id=user_id)


@pytest.fixture(scope="session")
def session() -> Generator[requests.Session, None, None]:
    with requests.Session() as http_session:
        yield http_session


@pytest.fixture(scope="session")
def known_products(api_context: ApiContext, session: requests.Session) -> list[dict]:
    response = session.get(
        api_context.url("/api/v1/products"),
        headers=api_context.user_headers,
        timeout=api_context.timeout,
    )
    assert response.status_code == 200, response.text
    products = response.json()
    assert isinstance(products, list) and products, "Expected at least one active product"
    return products


@pytest.fixture(scope="session")
def first_product(known_products: list[dict]) -> dict:
    return known_products[0]


@pytest.fixture(scope="session")
def expensive_product(known_products: list[dict]) -> dict:
    return max(known_products, key=lambda item: Decimal(str(item.get("price", 0))))


@pytest.fixture(scope="session")
def first_coupon(api_context: ApiContext, session: requests.Session) -> dict | None:
    response = session.get(
        api_context.url("/api/v1/admin/coupons"),
        headers=api_context.admin_headers,
        timeout=api_context.timeout,
    )
    assert response.status_code == 200, response.text
    coupons = response.json()
    return coupons[0] if coupons else None


def assert_json_object(response: requests.Response) -> dict:
    payload = response.json()
    assert isinstance(payload, dict), f"Expected JSON object, got: {payload!r}"
    return payload


def extract_cart_items(cart_payload):
    if isinstance(cart_payload, dict):
        for key in ("items", "cart_items", "products"):
            items = cart_payload.get(key)
            if isinstance(items, list):
                return items
    if isinstance(cart_payload, list):
        return cart_payload
    raise AssertionError(f"Could not locate cart items in payload: {cart_payload!r}")


@pytest.fixture(autouse=True)
def clear_cart_before_and_after(api_context: ApiContext, session: requests.Session):
    session.delete(
        api_context.url("/api/v1/cart/clear"),
        headers=api_context.user_headers,
        timeout=api_context.timeout,
    )
    yield
    session.delete(
        api_context.url("/api/v1/cart/clear"),
        headers=api_context.user_headers,
        timeout=api_context.timeout,
    )
