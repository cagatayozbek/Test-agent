def filter_expensive_items(items, threshold):
    result = []
    for item in items:
        try:
            # FIX: Explicitly convert price to float before comparison.
            price = float(item['price'])
            if price > threshold:
                result.append(item)
        except (ValueError, TypeError):
            # Skip items with non-numeric prices
            continue
    return result
