import pytest
from source import Customer, calculate_discount, get_discount_tier, LOYALTY_THRESHOLD, VIP_DISCOUNT, REGULAR_DISCOUNT

def test_customer_with_exact_loyalty_threshold_is_vip():
    """Test that a customer with EXACTLY the loyalty threshold points is correctly identified as VIP and receives the VIP discount.

    Bug: The code uses '>' instead of '>=' for LOYALTY_THRESHOLD check, causing customers with
    exactly 100 points to be treated as Regular instead of VIP.
    """
    # Create a customer with points exactly equal to the LOYALTY_THRESHOLD (e.g., 100 points)
    customer = Customer(name="Boundary VIP", points=LOYALTY_THRESHOLD)
    base_price = 200.0  # An arbitrary base price for calculation

    # Expected behavior: Customer with LOYALTY_THRESHOLD points should get VIP_DISCOUNT
    expected_discount_rate = VIP_DISCOUNT # Should be 20%
    expected_final_price = base_price * (1 - expected_discount_rate)

    # --- Test calculate_discount function ---
    actual_final_price = calculate_discount(customer, base_price)

    # This assertion will FAIL on the buggy code because it will apply REGULAR_DISCOUNT (5%)
    # and PASS on the fixed code which applies VIP_DISCOUNT (20%).
    assert actual_final_price == pytest.approx(expected_final_price), (
        f"Bug in calculate_discount: Customer with exactly {LOYALTY_THRESHOLD} points "
        f"did not receive VIP discount. Expected {expected_final_price:.2f} (VIP), "
        f"but got {actual_final_price:.2f} (likely regular discount)."
    )

    # --- Test get_discount_tier function ---
    actual_tier = get_discount_tier(customer)

    # This assertion will FAIL on the buggy code because it will return 'Regular'
    # and PASS on the fixed code which returns 'VIP'.
    assert actual_tier == "VIP", (
        f"Bug in get_discount_tier: Customer with exactly {LOYALTY_THRESHOLD} points "
        f"was incorrectly classified as '{actual_tier}'. Expected 'VIP'."
    )