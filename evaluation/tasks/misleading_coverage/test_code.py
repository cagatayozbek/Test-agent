# misleading_coverage/test_code.py
# Bu testler %100 coverage veriyor ama bug'ı yakalamıyor

import pytest
from source_code import calculate_discount, get_total


class TestCalculateDiscount:
    """Yanıltıcı: Tüm branch'ler cover ediliyor ama kombinasyon test yok."""
    
    def test_no_discount(self):
        """Normal müşteri, az adet."""
        result = calculate_discount(100.0, is_vip=False, quantity=5)
        assert result == 100.0
    
    def test_vip_discount(self):
        """VIP müşteri, az adet - %20 indirim."""
        result = calculate_discount(100.0, is_vip=True, quantity=5)
        assert result == 80.0
    
    def test_quantity_discount(self):
        """Normal müşteri, çok adet - %10 indirim."""
        result = calculate_discount(100.0, is_vip=False, quantity=15)
        assert result == 90.0
    
    # EKSIK TEST: VIP + çok adet kombinasyonu test edilmemiş!
    # def test_vip_and_quantity_discount(self):
    #     result = calculate_discount(100.0, is_vip=True, quantity=15)
    #     assert result == 72.0  # Bu test başarısız olurdu


class TestGetTotal:
    def test_empty_cart(self):
        assert get_total([]) == 0.0
    
    def test_single_item(self):
        assert get_total([(10.0, 2)]) == 20.0
    
    def test_multiple_items(self):
        assert get_total([(10.0, 2), (5.0, 3)]) == 35.0
