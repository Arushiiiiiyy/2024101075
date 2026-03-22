#!/usr/bin/env bash
# Source this file before running curl / pytest commands for QuickCart.

export QUICKCART_BASE_URL="http://127.0.0.1:8080"
export QUICKCART_ROLL_NUMBER="2024101075"
# Replace this after inspecting /api/v1/admin/users.
export QUICKCART_USER_ID="118"
export QUICKCART_TIMEOUT="10"

# Optional convenience headers for curl commands.
export QUICKCART_ADMIN_HEADER="X-Roll-Number: ${QUICKCART_ROLL_NUMBER}"
export QUICKCART_USER_HEADER_1="X-Roll-Number: ${QUICKCART_ROLL_NUMBER}"
export QUICKCART_USER_HEADER_2="X-User-ID: ${QUICKCART_USER_ID}"