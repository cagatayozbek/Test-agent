"""Discount calculator with VIP threshold bug.

This module calculates discounts based on customer loyalty points.
VIP customers (>= 100 points) should get a 20% discount.

BUG: Uses > instead of >= for threshold check, causing customers
with exactly 100 points to miss their VIP discount.
"""

LOYALTY_THRESHOLD = 100
VIP_DISCOUNT = 0.20
REGULAR_DISCOUNT = 0.05


class Customer:
    """Represents a customer with loyalty points."""
    
    def __init__(self, name: str, points: int):
        self.name = name
        self.points = points


def calculate_discount(customer: Customer, base_price: float) -> float:
    """Calculate discounted price based on customer loyalty.
    
    Args:
        customer: Customer object with loyalty points
        base_price: Original price before discount
    
    Returns:
        float: Final price after applying discount
    
    VIP customers (points >= 100) get 20% off.
    Regular customers get 5% off.
    """
    # BUG: Should be >= but uses >
    if customer.points > LOYALTY_THRESHOLD:
        discount = VIP_DISCOUNT
    else:
        discount = REGULAR_DISCOUNT
    
    return base_price * (1 - discount)


def get_discount_tier(customer: Customer) -> str:
    """Get the discount tier name for a customer."""
    # Same bug repeated here
    if customer.points > LOYALTY_THRESHOLD:
        return "VIP"
    return "Regular"
