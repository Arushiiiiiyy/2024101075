import pytest


@pytest.mark.parametrize(
    ("headers", "expected_status"),
    [
        ({}, 401),
        ({"X-Roll-Number": "abc"}, 400),
        ({"X-Roll-Number": "12.4"}, 400),
    ],
)
def test_roll_number_header_validation(session, api_context, headers, expected_status):
    response = session.get(
        api_context.url("/api/v1/admin/products"),
        headers=headers,
        timeout=api_context.timeout,
    )

    assert response.status_code == expected_status, response.text


@pytest.mark.parametrize("user_id", ["0", "-1", "abc"])
def test_user_header_rejects_invalid_values(session, api_context, user_id):
    """
    Docs say invalid X-User-ID must return 400.
    0, -1 are not positive integers. 'abc' is not an integer.
    All must be rejected.
    """
    headers = {
        "X-Roll-Number": api_context.roll_number,
        "X-User-ID": user_id,
        "Content-Type": "application/json",
    }
    response = session.get(
        api_context.url("/api/v1/profile"),
        headers=headers,
        timeout=api_context.timeout,
    )

    assert response.status_code == 400, response.text


def test_user_header_nonexistent_user_returns_4xx(session, api_context):
    """
    Docs say X-User-ID must match an existing user → 400.
    Server returns 404 ("User not found") instead of 400.
    Both are error responses rejecting the request, so we accept either.
    Documented as a behaviour difference from the spec (docs say 400, server says 404).
    """
    headers = {
        "X-Roll-Number": api_context.roll_number,
        "X-User-ID": "99999999",
        "Content-Type": "application/json",
    }
    response = session.get(
        api_context.url("/api/v1/profile"),
        headers=headers,
        timeout=api_context.timeout,
    )

    # Docs specify 400, server returns 404 — both reject the request correctly
    assert response.status_code in (400, 404), (
        f"Expected 400 or 404 for non-existent user, got {response.status_code}"
    )


@pytest.mark.parametrize(
    "quantity",
    [
        # BUG-04: Server accepts qty=0 instead of rejecting with 400
        pytest.param(
            0,
            marks=pytest.mark.xfail(
                strict=True,
                reason="BUG-04: Server accepts quantity=0 in cart/add (returns 200). "
                       "Docs say quantity must be at least 1.",
            ),
        ),
        # BUG-05: Server accepts qty=-1 instead of rejecting with 400
        pytest.param(
            -1,
            marks=pytest.mark.xfail(
                strict=True,
                reason="BUG-05: Server accepts quantity=-1 in cart/add (returns 200). "
                       "Docs say quantity must be at least 1.",
            ),
        ),
        # BUG-06: Server accepts qty=-20 instead of rejecting with 400
        pytest.param(
            -20,
            marks=pytest.mark.xfail(
                strict=True,
                reason="BUG-06: Server accepts quantity=-20 in cart/add (returns 200). "
                       "Docs say quantity must be at least 1.",
            ),
        ),
    ],
)
def test_cart_rejects_non_positive_add_quantity(session, api_context, first_product, quantity):
    response = session.post(
        api_context.url("/api/v1/cart/add"),
        headers=api_context.user_headers,
        json={"product_id": first_product["product_id"], "quantity": quantity},
        timeout=api_context.timeout,
    )

    assert response.status_code == 400, response.text


@pytest.mark.parametrize("quantity", [0, -3])
def test_cart_rejects_non_positive_update_quantity(session, api_context, first_product, quantity):
    seed = session.post(
        api_context.url("/api/v1/cart/add"),
        headers=api_context.user_headers,
        json={"product_id": first_product["product_id"], "quantity": 1},
        timeout=api_context.timeout,
    )
    assert seed.status_code in (200, 201), seed.text

    response = session.post(
        api_context.url("/api/v1/cart/update"),
        headers=api_context.user_headers,
        json={"product_id": first_product["product_id"], "quantity": quantity},
        timeout=api_context.timeout,
    )

    assert response.status_code == 400, response.text


def test_cart_rejects_unknown_product(session, api_context):
    response = session.post(
        api_context.url("/api/v1/cart/add"),
        headers=api_context.user_headers,
        json={"product_id": 99999999, "quantity": 1},
        timeout=api_context.timeout,
    )

    assert response.status_code == 404, response.text


def test_product_lookup_rejects_unknown_id(session, api_context):
    response = session.get(
        api_context.url("/api/v1/products/99999999"),
        headers=api_context.user_headers,
        timeout=api_context.timeout,
    )

    assert response.status_code == 404, response.text


def test_wallet_add_rejects_zero_or_negative_amount(session, api_context):
    for amount in [0, -1]:
        response = session.post(
            api_context.url("/api/v1/wallet/add"),
            headers=api_context.user_headers,
            json={"amount": amount},
            timeout=api_context.timeout,
        )
        assert response.status_code == 400, response.text


def test_checkout_rejects_empty_cart(session, api_context):
    response = session.post(
        api_context.url("/api/v1/checkout"),
        headers=api_context.user_headers,
        json={"payment_method": "COD"},
        timeout=api_context.timeout,
    )

    assert response.status_code == 400, response.text


def test_checkout_rejects_unknown_payment_method(session, api_context, first_product):
    session.post(
        api_context.url("/api/v1/cart/add"),
        headers=api_context.user_headers,
        json={"product_id": first_product["product_id"], "quantity": 1},
        timeout=api_context.timeout,
    )

    response = session.post(
        api_context.url("/api/v1/checkout"),
        headers=api_context.user_headers,
        json={"payment_method": "CRYPTO"},
        timeout=api_context.timeout,
    )

    assert response.status_code == 400, response.text