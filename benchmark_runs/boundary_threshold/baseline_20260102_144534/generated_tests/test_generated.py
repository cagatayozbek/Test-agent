import pytest
from source import calculate_discount, Customer, LOYALTY_THRESHOLD, VIP_DISCOUNT, REGULAR_DISCOUNT

def test_calculate_discount_vip_boundary_exact_threshold():
    """Test that a customer with exactly LOYALTY_THRESHOLD points receives the VIP discount.

    Bug: The calculate_discount function uses `>` instead of `>=` for the VIP threshold check.
    This causes customers with exactly 100 points to receive the regular discount instead of VIP.
    """
    # Create a customer with loyalty points exactly at the VIP threshold
    customer_at_threshold = Customer(name="BoundaryVIP", points=LOYALTY_THRESHOLD)
    base_price = 200.00

    # The expected price if VIP discount (20%) is applied
    expected_price_vip = base_price * (1 - VIP_DISCOUNT)

    # Calculate the discount using the buggy function
    actual_discounted_price = calculate_discount(customer_at_threshold, base_price)

    # Assert that the price reflects the VIP discount, not the regular one
    assert actual_discounted_price == pytest.approx(expected_price_vip), (
        f"Customer with exactly {LOYALTY_THRESHOLD} points should receive VIP discount ({VIP_DISCOUNT * 100}% off). "
        f"Expected {expected_price_vip:.2f}, but got {actual_discounted_price:.2f}. "
        f"This indicates the VIP threshold check is using strict inequality (>) instead of non-strict (>=)."
    )

    # Optionally, to be even more explicit about what the buggy code would yield
    expected_price_regular = base_price * (1 - REGULAR_DISCOUNT)
    if actual_discounted_price == pytest.approx(expected_price_regular):
        pytest.fail(
            f"Bug detected: Customer with exactly {LOYALTY_THRESHOLD} points received "
            f"REGULAR discount ({REGULAR_DISCOUNT * 100}% off) instead of VIP. "
            f"Got {actual_discounted_price:.2f}, but expected {expected_price_vip:.2f} (VIP)."
        )
