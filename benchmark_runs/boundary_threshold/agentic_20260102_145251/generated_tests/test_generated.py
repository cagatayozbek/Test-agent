import pytest
from source import Customer, calculate_discount, LOYALTY_THRESHOLD, VIP_DISCOUNT

def test_vip_discount_at_exact_threshold():
    """Tests that a customer with points exactly at the threshold gets the VIP discount.
    
    Bug: The code uses a strict greater-than (>) instead of greater-than-or-equal-to (>=),
    causing customers with exactly LOYALTY_THRESHOLD points to miss the VIP discount.
    """
    # Arrange: Create a customer at the exact boundary condition
    customer_at_threshold = Customer(name="Boundary Betty", points=LOYALTY_THRESHOLD)
    base_price = 100.0
    
    # Expected price with the 20% VIP discount
    expected_price = base_price * (1 - VIP_DISCOUNT) # 100.0 * 0.8 = 80.0
    
    # Act: Calculate the discount for this customer
    actual_price = calculate_discount(customer_at_threshold, base_price)
    
    # Assert: The price should reflect the VIP discount, not the regular one
    assert actual_price == expected_price, (
        f"Customer with exactly {LOYALTY_THRESHOLD} points should get the VIP discount. "
        f"Expected price: {expected_price}, but got: {actual_price}"
    )