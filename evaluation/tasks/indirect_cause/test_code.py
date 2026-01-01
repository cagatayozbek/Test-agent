# indirect_cause/test_code.py
# Testler üst seviye davranışı test ediyor, Config default'larını değil

import pytest
from source_code import Config, load_config, APIClient, DataService


class TestConfig:
    """Config testleri - default değerler kontrol edilmiyor."""
    
    def test_default_config(self):
        config = Config()
        assert config.api_url == "https://api.example.com"
        assert config.max_retries == 3
        # NOT: timeout_ms'in 0 olup olmadığı KONTROL EDİLMİYOR
    
    def test_load_config_with_overrides(self):
        config = load_config({"debug_mode": True})
        assert config.debug_mode is True


class TestAPIClient:
    """Client testleri - timeout=0 durumu test edilmiyor."""
    
    def test_connect_success(self):
        # Override ile timeout veriliyor - default test edilmiyor
        config = Config(timeout_ms=5000)
        client = APIClient(config)
        assert client.connect() is True
    
    def test_fetch_data(self):
        config = Config(timeout_ms=5000)
        client = APIClient(config)
        client.connect()
        result = client.fetch_data("/test")
        assert "data" in result
    
    def test_fetch_without_connection(self):
        config = Config(timeout_ms=5000)
        client = APIClient(config)
        with pytest.raises(RuntimeError):
            client.fetch_data("/test")


class TestDataService:
    """Service testleri - her zaman explicit config ile çalışıyor."""
    
    def test_initialize(self):
        # Explicit config - default test edilmiyor
        config = Config(timeout_ms=3000)
        service = DataService(config)
        assert service.initialize() is True
    
    def test_get_user_profile(self):
        config = Config(timeout_ms=3000)
        service = DataService(config)
        service.initialize()
        profile = service.get_user_profile("user123")
        assert profile["user_id"] == "user123"
    
    # EKSIK TEST: Default config ile servis kullanımı
    # def test_default_config_behavior(self):
    #     service = DataService()  # Default config kullanır
    #     service.initialize()  # timeout_ms=0 ile çalışır
    #     # Bu test PASS oluyor ama production'da sorun çıkar!
