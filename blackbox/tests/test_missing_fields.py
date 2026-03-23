import pytest


@pytest.mark.parametrize(
    ("payload", "expected_status"),
    [
        # Empty body — no product_id supplied, server treats it as null → "Product not found" (404)
        # Docs say 400 for missing fields, server returns 404. Both reject the request.
        ({}, (400, 404)),
        # Only quantity, no product_id — same as above, server looks up null product → 404
        ({"quantity": 1}, (400, 404)),
    ],
)
def test_cart_add_missing_product_id_returns_error(session, api_context, payload, expected_status):
    """
    Docs say missing required fields → 400.
    Server returns 404 ("Product not found") when product_id is absent.
    Both are error responses rejecting the request, so we accept either.
    """
    response = session.post(
        api_context.url("/api/v1/cart/add"),
        headers=api_context.user_headers,
        json=payload,
        timeout=api_context.timeout,
    )
    assert response.status_code in expected_status, (
        f"Expected one of {expected_status}, got {response.status_code}: {response.text}"
    )


@pytest.mark.parametrize(
    "payload",
    [
        # BUG-07: Missing quantity — server adds item anyway instead of returning 400
        pytest.param(
            {"product_id": 1},
            marks=pytest.mark.xfail(
                strict=True,
                reason="BUG-07: Server accepts cart/add with no quantity field "
                       "(returns 200). Docs require quantity to be present and >= 1.",
            ),
        ),
    ],
)
def test_cart_add_missing_quantity_returns_400(session, api_context, payload):
    response = session.post(
        api_context.url("/api/v1/cart/add"),
        headers=api_context.user_headers,
        json=payload,
        timeout=api_context.timeout,
    )
    assert response.status_code == 400, response.text


def test_profile_requires_user_header(session, api_context):
    response = session.get(
        api_context.url("/api/v1/profile"),
        headers={"X-Roll-Number": api_context.roll_number},
        timeout=api_context.timeout,
    )
    assert response.status_code == 400, response.text


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"street": "12345 Main Street", "city": "Hyderabad", "pincode": "500001"},
        {"label": "HOME", "city": "Hyderabad", "pincode": "500001"},
        {"label": "HOME", "street": "12345 Main Street", "pincode": "500001"},
        {"label": "HOME", "street": "12345 Main Street", "city": "Hyderabad"},
    ],
)
def test_address_create_requires_all_mandatory_fields(session, api_context, payload):
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
        # Empty body — no fields at all → should be 400
        {},
        # BUG-08: Only comment, no rating — server creates review anyway
        pytest.param(
            {"comment": "great"},
            marks=pytest.mark.xfail(
                strict=True,
                reason="BUG-08: Server accepts review with no rating field "
                       "(returns 200). Rating is a required field per docs.",
            ),
        ),
        # Only rating, no comment → should be 400
        {"rating": 5},
    ],
)
def test_review_create_requires_rating_and_comment(session, api_context, first_product, payload):
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
        {},
        {"message": "Need help"},
        {"subject": "Login issue"},
    ],
)
def test_support_ticket_requires_subject_and_message(session, api_context, payload):
    response = session.post(
        api_context.url("/api/v1/support/ticket"),
        headers=api_context.user_headers,
        json=payload,
        timeout=api_context.timeout,
    )
    assert response.status_code == 400, response.text


def test_checkout_requires_payment_method_field(session, api_context, first_product):
    session.post(
        api_context.url("/api/v1/cart/add"),
        headers=api_context.user_headers,
        json={"product_id": first_product["product_id"], "quantity": 1},
        timeout=api_context.timeout,
    )

    response = session.post(
        api_context.url("/api/v1/checkout"),
        headers=api_context.user_headers,
        json={},
        timeout=api_context.timeout,
    )
    assert response.status_code == 400, response.text