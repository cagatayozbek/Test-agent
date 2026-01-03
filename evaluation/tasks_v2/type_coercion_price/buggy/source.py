def filter_expensive_items(items, threshold):
    """
    Filters items above a certain price.
    items: [{'name': 'A', 'price': 100}, {'name': 'B', 'price': '200'}]
    """
    result = []
    for item in items:
        # BUG: If item['price'] is a string ("200"),
        # "200" > 150 raises TypeError in Python 3.
        if item['price'] > threshold:
            result.append(item)
    return result
