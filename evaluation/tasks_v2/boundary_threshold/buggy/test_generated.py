import pytest
from source import Customer, calculate_discount, LOYALTY_THRESHOLD

def test_vip_discount_at_exact_threshold():
    """Tests that a customer with exactly the loyalty threshold points gets the VIP discount.
    
    Bug: The check `customer.points > LOYALTY_THRESHOLD` incorrectly excludes
    customers who have exactly `LOYALTY_THRESHOLD` points from the VIP tier.
    """
    # Arrange: Create a customer at the exact VIP boundary
    customer_at_threshold = Customer(name="Boundary Bob", points=LOYALTY_THRESHOLD) # Exactly 100 points
    base_price = 100.0
    
    # Expected result for a VIP customer (20% discount)
    expected_price = base_price * (1 - 0.20) # 80.0
    
    # Act: Calculate the discount for this customer
    actual_price = calculate_discount(customer_at_threshold, base_price)
    
    # Assert: The price should reflect the VIP discount, not the regular one
    assert actual_price == expected_price, (
        f"Customer with exactly {LOYALTY_THRESHOLD} points should get a 20% VIP discount. "
        f"Expected price: {expected_price}, but got: {actual_price}."
    )