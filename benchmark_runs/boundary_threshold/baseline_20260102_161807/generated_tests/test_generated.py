import pytest
from source import Customer, calculate_discount, LOYALTY_THRESHOLD, VIP_DISCOUNT

def test_vip_discount_at_exact_threshold():
    """Test that a customer with points exactly at the VIP threshold gets the VIP discount.

    The bug is a strict inequality (>) check instead of (>=), causing this
    boundary case to fail and receive the regular discount instead.
    """
    # Arrange: Create a customer with exactly the number of points for VIP status
    customer_at_threshold = Customer(name="Boundary Bob", points=LOYALTY_THRESHOLD)
    base_price = 100.0
    
    # The expected price with the correct 20% VIP discount
    expected_price = base_price * (1 - VIP_DISCOUNT) # 100 * 0.80 = 80.0

    # Act: Calculate the discount for this customer
    actual_price = calculate_discount(customer_at_threshold, base_price)

    # Assert: The price should reflect the VIP discount, not the regular one
    assert actual_price == expected_price, (
        f"Customer with exactly {LOYALTY_THRESHOLD} points should receive the VIP discount. "
        f"Expected price: {expected_price}, but got: {actual_price}"
    )