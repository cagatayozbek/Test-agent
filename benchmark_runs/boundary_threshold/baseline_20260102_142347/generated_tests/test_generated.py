import pytest
from source import calculate_discount, Customer, LOYALTY_THRESHOLD


def test_vip_discount_at_threshold():
    """Test that a customer with loyalty points equal to the threshold receives the VIP discount.

    The buggy code uses > instead of >=, so a customer with exactly LOYALTY_THRESHOLD points
    will be incorrectly classified as a regular customer and not receive the VIP discount.
    """
    customer = Customer(name="Test Customer", points=LOYALTY_THRESHOLD)
    base_price = 100.0
    expected_price = base_price * (1 - 0.20)  # Expected VIP discount (20%)
    actual_price = calculate_discount(customer, base_price)
    assert actual_price == expected_price, \
        f"Expected VIP discount price of {expected_price}, but got {actual_price}"
