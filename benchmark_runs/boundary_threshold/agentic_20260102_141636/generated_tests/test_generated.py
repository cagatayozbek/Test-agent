import pytest
from source import calculate_discount, Customer, LOYALTY_THRESHOLD, VIP_DISCOUNT


def test_vip_discount_threshold():
    """Test that a customer with exactly LOYALTY_THRESHOLD gets VIP discount.

    Bug: The function uses > instead of >=, causing the customer to be incorrectly classified.
    """
    customer = Customer(name="test", points=LOYALTY_THRESHOLD)
    discounted_price = calculate_discount(customer, base_price=100.0)
    expected_price = 100.0 * (1 - VIP_DISCOUNT)
    assert discounted_price == expected_price, \
        f"Customer with {LOYALTY_THRESHOLD} points should get VIP discount. Expected {expected_price}, got {discounted_price}"