def process_batch(items):
    """
    Items listesini işler ve sonuçları döndürür.
    Her item'ı 2 ile çarpar.
    """
    results = []
    # FIX: range(len(items)) tüm elemanları kapsar
    for i in range(len(items)):
        results.append(items[i] * 2)
    return results
