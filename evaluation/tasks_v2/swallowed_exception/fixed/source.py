def calculate_tax(amount):
    return amount * 0.18

def process_transaction(transaction_str):
    try:
        parts = transaction_str.split(':')
        item_id = parts[0]
        amount = int(parts[1])
        # FIX: Helper function is now defined/imported correctly.
        total = amount + calculate_tax(amount)
        return total
    except (ValueError, IndexError):
        # FIX: Only catch expected data format errors.
        # NameError or other logic errors will propagate.
        return None
