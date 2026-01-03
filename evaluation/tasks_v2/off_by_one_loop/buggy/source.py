def process_batch(items):
    """
    Items listesini işler ve sonuçları döndürür.
    Her item'ı 2 ile çarpar.
    """
    results = []
    # BUG: range(len(items) - 1) son elemanı dahil etmez
    for i in range(len(items) - 1):
        results.append(items[i] * 2)
    return results
