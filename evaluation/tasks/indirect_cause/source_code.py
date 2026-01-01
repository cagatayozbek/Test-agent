# indirect_cause/code.py
# Tuzak: Görünen hata başka bir yerde, asıl sebep farklı modülde

from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    """
    Uygulama konfigürasyonu.
    
    BUG: default değerler runtime'da beklenmedik davranışa yol açıyor.
    timeout_ms'in 0 olması downstream'de sonsuz beklemeye sebep oluyor.
    """
    api_url: str = "https://api.example.com"
    timeout_ms: int = 0  # BUG: 0 timeout = sonsuz bekleme
    max_retries: int = 3
    debug_mode: bool = False


def load_config(overrides: Optional[dict] = None) -> Config:
    """Config yükler, override varsa uygular."""
    config = Config()
    if overrides:
        for key, value in overrides.items():
            if hasattr(config, key):
                setattr(config, key, value)
    return config


# --- api_client.py gibi düşünün ---

class APIClient:
    """
    API istemcisi.
    
    Hata BURADA görünüyor ama asıl sebep Config'deki default timeout.
    """
    
    def __init__(self, config: Config):
        self.config = config
        self._connected = False
    
    def connect(self) -> bool:
        """
        API'ye bağlan.
        
        timeout_ms=0 ise bu metot 'başarılı' görünüyor
        ama aslında timeout kontrolü devre dışı kalıyor.
        """
        # Simülasyon: timeout 0 ise kontrol atlanıyor
        if self.config.timeout_ms == 0:
            # BUG: Timeout kontrolü yok - sessizce devam ediyor
            self._connected = True
            return True
        
        # Normal akış
        if self.config.timeout_ms > 0:
            self._connected = True
            return True
        
        return False
    
    def fetch_data(self, endpoint: str) -> dict:
        """
        Veri çek.
        
        Timeout 0 olduğunda bu metot sonsuza kadar bekleyebilir
        (gerçek senaryoda). Test ortamında sorun görünmüyor.
        """
        if not self._connected:
            raise RuntimeError("Not connected")
        
        # Simülasyon: Timeout 0 ise uyarı yok
        return {"endpoint": endpoint, "data": "mock_response"}


# --- service.py gibi düşünün ---

class DataService:
    """
    Üst seviye servis.
    
    Hata en üstte patlıyor ama:
    - DataService → APIClient → Config zinciri var
    - Asıl sorun Config'in default'unda
    """
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or load_config()
        self.client = APIClient(self.config)
    
    def initialize(self) -> bool:
        """Servisi başlat."""
        return self.client.connect()
    
    def get_user_profile(self, user_id: str) -> dict:
        """
        Kullanıcı profili getir.
        
        Production'da bu metot timeout olmadan sonsuza kadar bekleyebilir.
        Test'te sorun görünmüyor çünkü mock data anında dönüyor.
        """
        if not self.client._connected:
            if not self.initialize():
                raise RuntimeError("Failed to initialize")
        
        raw_data = self.client.fetch_data(f"/users/{user_id}")
        return {
            "user_id": user_id,
            "profile": raw_data
        }
