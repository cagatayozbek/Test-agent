import pytest
from source import Customer, calculate_discount, LOYALTY_THRESHOLD, VIP_DISCOUNT, REGULAR_DISCOUNT

def test_customer_at_vip_threshold_boundary_gets_vip_discount():
    """Tests that a customer with points exactly equal to the threshold receives the VIP discount.

    Bug Description:
    The function `calculate_discount` uses a strict greater-than check (`> LOYALTY_THRESHOLD`)
    instead of greater-than-or-equal-to (`>=`). This means a customer with exactly
    100 points is incorrectly given the regular discount instead of the VIP discount.
    """
    # Arrange: Create a customer at the exact boundary value that triggers the bug
    customer_at_threshold = Customer(name="Boundary Bob", points=LOYALTY_THRESHOLD) # Exactly 100 points
    base_price = 100.0

    # Act: Calculate the discounted price
    actual_price = calculate_discount(customer_at_threshold, base_price)

    # Assert: The price should reflect the 20% VIP discount, not the 5% regular discount
    expected_price = base_price * (1 - VIP_DISCOUNT)  # 100.0 * 0.80 = 80.0

    # The buggy code will calculate 100.0 * (1 - 0.05) = 95.0, causing this assertion to fail.
    assert actual_price == expected_price, (
        f"Customer with exactly {LOYALTY_THRESHOLD} points should get the VIP discount. "
        f"Expected price: {expected_price}, but got: {actual_price}"
    )