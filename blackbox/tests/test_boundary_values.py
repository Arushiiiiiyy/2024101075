import pytest


@pytest.mark.parametrize(
    ("payload", "expected_status"),
    [
        ({"name": "A", "phone": "1234567890"}, 400),
        ({"name": "A" * 51, "phone": "1234567890"}, 400),
        ({"name": "AB", "phone": "1234567890"}, 200),
        ({"name": "A" * 50, "phone": "1234567890"}, 200),
        ({"name": "Valid Name", "phone": "123456789"}, 400),
        ({"name": "Valid Name", "phone": "12345678901"}, 400),
    ],
)
def test_profile_update_boundary_values(session, api_context, payload, expected_status):
    response = session.put(
        api_context.url("/api/v1/profile"),
        headers=api_context.user_headers,
        json=payload,
        timeout=api_context.timeout,
    )

    assert response.status_code == expected_status, response.text


@pytest.mark.parametrize(
    ("payload", "expected_status"),
    [
        ({"label": "HOME", "street": "1234", "city": "Hyderabad", "pincode": "500001"}, 400),
        ({"label": "HOME", "street": "12345", "city": "Hyderabad", "pincode": "500001"}, 200),
        ({"label": "HOME", "street": "X" * 100, "city": "Hyderabad", "pincode": "500001"}, 200),
        ({"label": "HOME", "street": "X" * 101, "city": "Hyderabad", "pincode": "500001"}, 400),
        ({"label": "HOME", "street": "12345 Main Street", "city": "H", "pincode": "500001"}, 400),
        ({"label": "HOME", "street": "12345 Main Street", "city": "Hy", "pincode": "500001"}, 200),
        ({"label": "HOME", "street": "12345 Main Street", "city": "X" * 50, "pincode": "500001"}, 200),
        ({"label": "HOME", "street": "12345 Main Street", "city": "X" * 51, "pincode": "500001"}, 400),
        ({"label": "HOME", "street": "12345 Main Street", "city": "Hyderabad", "pincode": "50000"}, 400),
        ({"label": "HOME", "street": "12345 Main Street", "city": "Hyderabad", "pincode": "500001"}, 200),
        ({"label": "HOME", "street": "12345 Main Street", "city": "Hyderabad", "pincode": "5000011"}, 400),
    ],
)
def test_address_create_boundary_values(session, api_context, payload, expected_status):
    response = session.post(
        api_context.url("/api/v1/addresses"),
        headers=api_context.user_headers,
        json=payload,
        timeout=api_context.timeout,
    )

    assert response.status_code == expected_status, response.text


@pytest.mark.parametrize(
    ("payload", "expected_status"),
    [
        # BUG-02: Server accepts rating=0 instead of rejecting with 400
        pytest.param(
            {"rating": 0, "comment": "bad"},
            400,
            marks=pytest.mark.xfail(
                strict=True,
                reason="BUG-02: Server accepts rating=0 (returns 200), should return 400. Rating must be 1-5 per docs.",
            ),
        ),
        ({"rating": 1, "comment": "ok"}, 200),
        ({"rating": 5, "comment": "great"}, 200),
        # BUG-03: Server accepts rating=6 instead of rejecting with 400
        pytest.param(
            {"rating": 6, "comment": "too much"},
            400,
            marks=pytest.mark.xfail(
                strict=True,
                reason="BUG-03: Server accepts rating=6 (returns 200), should return 400. Rating must be 1-5 per docs.",
            ),
        ),
        ({"rating": 3, "comment": ""}, 400),
        ({"rating": 3, "comment": "x" * 200}, 200),
        ({"rating": 3, "comment": "x" * 201}, 400),
    ],
)
def test_review_boundaries(session, api_context, first_product, payload, expected_status):
    response = session.post(
        api_context.url(f"/api/v1/products/{first_product['product_id']}/reviews"),
        headers=api_context.user_headers,
        json=payload,
        timeout=api_context.timeout,
    )

    assert response.status_code == expected_status, response.text


@pytest.mark.parametrize(
    ("payload", "expected_status"),
    [
        ({"subject": "1234", "message": "Need help"}, 400),
        ({"subject": "12345", "message": "Need help"}, 200),
        ({"subject": "x" * 100, "message": "Need help"}, 200),
        ({"subject": "x" * 101, "message": "Need help"}, 400),
        ({"subject": "Valid subject", "message": ""}, 400),
        ({"subject": "Valid subject", "message": "x" * 500}, 200),
        ({"subject": "Valid subject", "message": "x" * 501}, 400),
    ],
)
def test_support_ticket_boundaries(session, api_context, payload, expected_status):
    response = session.post(
        api_context.url("/api/v1/support/ticket"),
        headers=api_context.user_headers,
        json=payload,
        timeout=api_context.timeout,
    )

    assert response.status_code == expected_status, response.text


@pytest.mark.parametrize(
    ("amount", "expected_status"),
    [
        (0, 400),
        (1, 200),
        (100000, 200),
        (100001, 400),
    ],
)
def test_wallet_add_boundary_values(session, api_context, amount, expected_status):
    response = session.post(
        api_context.url("/api/v1/wallet/add"),
        headers=api_context.user_headers,
        json={"amount": amount},
        timeout=api_context.timeout,
    )

    assert response.status_code == expected_status, response.text