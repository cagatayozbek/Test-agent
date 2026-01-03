def calculate_tax(amount):
    # This function is intentionally missing or not imported in the buggy context
    # to simulate a NameError or similar logic error.
    # In a real scenario, this might be a typo in the function name.
    raise NameError("name 'calculate_tax' is not defined")

def process_transaction(transaction_str):
    """
    Processes a transaction string in "item_id:amount" format.
    """
    try:
        parts = transaction_str.split(':')
        item_id = parts[0]
        amount = int(parts[1])
        # BUG: 'calculate_tax' might raise NameError (or be undefined),
        # but the bare except block below will swallow it.
        total = amount + calculate_tax(amount) 
        return total
    except:
        # BUG: Catches ALL exceptions, including NameError, SyntaxError, etc.
        # This hides the actual bug and makes it look like a data error.
        return None
