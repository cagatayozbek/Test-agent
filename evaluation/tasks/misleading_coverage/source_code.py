# misleading_coverage/code.py
# Tuzak: %100 coverage ama kritik edge case test edilmemiş

def calculate_discount(price: float, is_vip: bool, quantity: int) -> float:
    """
    Fiyat hesaplama fonksiyonu.
    VIP müşteriye %20 indirim, 10+ adet alımda %10 ek indirim.
    
    BUG: VIP + 10+ adet durumunda indirimler yanlış uygulanıyor.
    Doğru: price * 0.8 * 0.9 = %28 indirim
    Hatalı: price * 0.7 (sadece %30 indirim veriyor)
    """
    discount = 0.0
    
    if is_vip:
        discount = 0.2
    
    if quantity >= 10:
        # BUG: Toplama yerine üzerine yazıyor
        discount = 0.1  # Olması gereken: discount += 0.1 veya çarpımsal hesap
    
    return price * (1 - discount)


def get_total(items: list[tuple[float, int]]) -> float:
    """Sepetteki ürünlerin toplamını döner."""
    return sum(price * qty for price, qty in items)
