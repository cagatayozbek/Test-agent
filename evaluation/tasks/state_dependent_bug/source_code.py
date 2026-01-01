# state_dependent_bug/code.py
# Tuzak: Bug yalnızca belirli çağrı sırasında ortaya çıkıyor

class SessionManager:
    """
    Kullanıcı oturumu yönetimi.
    
    BUG: logout() sonrası get_user_data() çağrılırsa,
    _current_user None ama _session_data hâlâ eski veriyi tutuyor.
    Bu durum güvenlik açığı oluşturabilir.
    """
    
    def __init__(self):
        self._current_user: str | None = None
        self._session_data: dict = {}
        self._is_authenticated: bool = False
    
    def login(self, username: str, password: str) -> bool:
        """Kullanıcı girişi."""
        # Basitleştirilmiş auth (gerçekte DB kontrolü olur)
        if username and password:
            self._current_user = username
            self._is_authenticated = True
            self._session_data = {
                "user": username,
                "login_time": "2025-01-01T10:00:00",
                "permissions": ["read", "write"]
            }
            return True
        return False
    
    def logout(self) -> None:
        """Kullanıcı çıkışı."""
        self._current_user = None
        self._is_authenticated = False
        # BUG: _session_data temizlenmiyor!
        # self._session_data = {}  # Bu satır eksik
    
    def get_user_data(self) -> dict | None:
        """
        Oturum verisini döner.
        
        BUG: _is_authenticated kontrolü var ama
        _session_data'nın stale olup olmadığı kontrol edilmiyor.
        """
        if self._is_authenticated:
            return self._session_data
        # Burada None dönmeli ama...
        # Bazı edge case'lerde _session_data hâlâ erişilebilir kalabilir
        return None
    
    def is_logged_in(self) -> bool:
        return self._is_authenticated
    
    def get_raw_session(self) -> dict:
        """
        Debug amaçlı - doğrudan session data erişimi.
        
        GÜVENLİK AÇIĞI: Bu metot logout sonrası bile
        eski session verisini döner!
        """
        return self._session_data


class Counter:
    """
    Basit sayaç - state-dependent davranış örneği.
    
    BUG: reset() sonrası increment() çağrılırsa,
    _history listesi temizlenmediği için yanlış veri gösterir.
    """
    
    def __init__(self):
        self._value: int = 0
        self._history: list[int] = []
    
    def increment(self) -> int:
        self._value += 1
        self._history.append(self._value)
        return self._value
    
    def reset(self) -> None:
        self._value = 0
        # BUG: _history temizlenmiyor
        # self._history = []  # Eksik
    
    def get_history(self) -> list[int]:
        return self._history.copy()
    
    def get_value(self) -> int:
        return self._value
