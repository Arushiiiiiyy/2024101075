from decimal import Decimal

from conftest import assert_json_object, extract_cart_items


def test_get_profile_returns_current_user(session, api_context):
    response = session.get(
        api_context.url("/api/v1/profile"),
        headers=api_context.user_headers,
        timeout=api_context.timeout,
    )

    assert response.status_code == 200, response.text
    payload = assert_json_object(response)
    assert str(payload.get("user_id")) == api_context.user_id
    assert "name" in payload
    assert "phone" in payload



def test_get_products_returns_only_active_products(session, api_context):
    user_response = session.get(
        api_context.url("/api/v1/products"),
        headers=api_context.user_headers,
        timeout=api_context.timeout,
    )
    admin_response = session.get(
        api_context.url("/api/v1/admin/products"),
        headers=api_context.admin_headers,
        timeout=api_context.timeout,
    )

    assert user_response.status_code == 200, user_response.text
    assert admin_response.status_code == 200, admin_response.text

    user_products = user_response.json()
    admin_products = admin_response.json()
    active_admin_ids = {
        item["product_id"]
        for item in admin_products
        if item.get("is_active") in (True, 1, "true", "TRUE")
    }

    assert isinstance(user_products, list)
    assert all(product["product_id"] in active_admin_ids for product in user_products)



def test_get_single_product_matches_list_entry(session, api_context, first_product):
    response = session.get(
        api_context.url(f"/api/v1/products/{first_product['product_id']}"),
        headers=api_context.user_headers,
        timeout=api_context.timeout,
    )

    assert response.status_code == 200, response.text
    payload = assert_json_object(response)
    assert payload["product_id"] == first_product["product_id"]
    assert Decimal(str(payload["price"])) == Decimal(str(first_product["price"]))



def test_adding_same_product_twice_accumulates_quantity(session, api_context, first_product):
    add_payload = {"product_id": first_product["product_id"], "quantity": 1}

    first = session.post(
        api_context.url("/api/v1/cart/add"),
        headers=api_context.user_headers,
        json=add_payload,
        timeout=api_context.timeout,
    )
    second = session.post(
        api_context.url("/api/v1/cart/add"),
        headers=api_context.user_headers,
        json=add_payload,
        timeout=api_context.timeout,
    )
    cart = session.get(
        api_context.url("/api/v1/cart"),
        headers=api_context.user_headers,
        timeout=api_context.timeout,
    )

    assert first.status_code in (200, 201), first.text
    assert second.status_code in (200, 201), second.text
    assert cart.status_code == 200, cart.text

    items = extract_cart_items(cart.json())
    matching_items = [item for item in items if item.get("product_id") == first_product["product_id"]]
    assert len(matching_items) == 1
    assert int(matching_items[0]["quantity"]) == 2



def test_cart_item_subtotal_and_total_are_consistent(session, api_context, first_product):
    quantity = 2
    response = session.post(
        api_context.url("/api/v1/cart/add"),
        headers=api_context.user_headers,
        json={"product_id": first_product["product_id"], "quantity": quantity},
        timeout=api_context.timeout,
    )
    cart = session.get(
        api_context.url("/api/v1/cart"),
        headers=api_context.user_headers,
        timeout=api_context.timeout,
    )

    assert response.status_code in (200, 201), response.text
    assert cart.status_code == 200, cart.text

    cart_payload = cart.json()
    items = extract_cart_items(cart_payload)
    target = next(item for item in items if item.get("product_id") == first_product["product_id"])
    expected_subtotal = Decimal(str(first_product["price"])) * quantity
    assert Decimal(str(target["subtotal"])) == expected_subtotal

    expected_total = sum(Decimal(str(item["subtotal"])) for item in items)
    if isinstance(cart_payload, dict):
        assert Decimal(str(cart_payload["total"])) == expected_total



def test_create_address_returns_created_object(session, api_context):
    payload = {
        "label": "HOME",
        "street": "12345 Main Street",
        "city": "Hyderabad",
        "pincode": "500001",
        "is_default": True,
    }
    response = session.post(
        api_context.url("/api/v1/addresses"),
        headers=api_context.user_headers,
        json=payload,
        timeout=api_context.timeout,
    )

    assert response.status_code in (200, 201), response.text
    body = assert_json_object(response)
    address = body.get("address", body)
    for key in ("address_id", "label", "street", "city", "pincode", "is_default"):
        assert key in address
    assert address["label"] == payload["label"]
    assert address["street"] == payload["street"]


def test_wallet_endpoint_exposes_balance(session, api_context):
    response = session.get(
        api_context.url("/api/v1/wallet"),
        headers=api_context.user_headers,
        timeout=api_context.timeout,
    )

    assert response.status_code == 200, response.text
    payload = assert_json_object(response)
    assert "balance" in payload or "wallet_balance" in payload



def test_loyalty_endpoint_exposes_points(session, api_context):
    response = session.get(
        api_context.url("/api/v1/loyalty"),
        headers=api_context.user_headers,
        timeout=api_context.timeout,
    )

    assert response.status_code == 200, response.text
    payload = assert_json_object(response)
    assert "loyalty_points" in payload or "points" in payload
