import pytest


@pytest.mark.parametrize(
    "payload",
    [
        {"product_id": "one", "quantity": 1},
        {"product_id": 1, "quantity": "two"},
        {"product_id": 1, "quantity": 1.5},
        {"product_id": [1], "quantity": 1},
    ],
)
def test_cart_add_rejects_wrong_types(session, api_context, payload):
    response = session.post(
        api_context.url("/api/v1/cart/add"),
        headers=api_context.user_headers,
        json=payload,
        timeout=api_context.timeout,
    )

    assert response.status_code == 400, response.text


@pytest.mark.parametrize(
    "payload",
    [
        {"name": 12345, "phone": "1234567890"},
        {"name": "Alice", "phone": 1234567890},
        {"name": ["Alice"], "phone": "1234567890"},
    ],
)
def test_profile_update_rejects_wrong_types(session, api_context, payload):
    response = session.put(
        api_context.url("/api/v1/profile"),
        headers=api_context.user_headers,
        json=payload,
        timeout=api_context.timeout,
    )

    assert response.status_code == 400, response.text


@pytest.mark.parametrize(
    "payload",
    [
        {"label": "HOME", "street": 12345, "city": "Hyderabad", "pincode": "500001"},
        {"label": "HOME", "street": "12345 Main Street", "city": False, "pincode": "500001"},
        {"label": "HOME", "street": "12345 Main Street", "city": "Hyderabad", "pincode": 500001},
        {"label": True, "street": "12345 Main Street", "city": "Hyderabad", "pincode": "500001"},
    ],
)
def test_address_create_rejects_wrong_types(session, api_context, payload):
    response = session.post(
        api_context.url("/api/v1/addresses"),
        headers=api_context.user_headers,
        json=payload,
        timeout=api_context.timeout,
    )

    assert response.status_code == 400, response.text


@pytest.mark.parametrize(
    "payload",
    [
        {"rating": "5", "comment": "good"},
        {"rating": 5.1, "comment": "good"},
        {"rating": 5, "comment": ["good"]},
    ],
)
def test_review_create_rejects_wrong_types(session, api_context, first_product, payload):
    response = session.post(
        api_context.url(f"/api/v1/products/{first_product['product_id']}/reviews"),
        headers=api_context.user_headers,
        json=payload,
        timeout=api_context.timeout,
    )

    assert response.status_code == 400, response.text


@pytest.mark.parametrize(
    "payload",
    [
        {"amount": "100"},
        {"amount": [100]},
        {"amount": True},
    ],
)
def test_wallet_add_rejects_wrong_amount_types(session, api_context, payload):
    response = session.post(
        api_context.url("/api/v1/wallet/add"),
        headers=api_context.user_headers,
        json=payload,
        timeout=api_context.timeout,
    )

    assert response.status_code == 400, response.text
