# state_dependent_bug/test_code.py
# Testler izole çalışıyor - state geçişlerini test etmiyor

import pytest
from source_code import SessionManager, Counter


class TestSessionManager:
    """Her test izole - login→logout→tekrar erişim senaryosu yok."""
    
    def test_login_success(self):
        sm = SessionManager()
        result = sm.login("alice", "password123")
        assert result is True
        assert sm.is_logged_in() is True
    
    def test_login_failure(self):
        sm = SessionManager()
        result = sm.login("", "")
        assert result is False
        assert sm.is_logged_in() is False
    
    def test_logout(self):
        sm = SessionManager()
        sm.login("alice", "password123")
        sm.logout()
        assert sm.is_logged_in() is False
    
    def test_get_user_data_when_logged_in(self):
        sm = SessionManager()
        sm.login("alice", "password123")
        data = sm.get_user_data()
        assert data is not None
        assert data["user"] == "alice"
    
    def test_get_user_data_when_not_logged_in(self):
        sm = SessionManager()
        data = sm.get_user_data()
        assert data is None
    
    # EKSIK TEST: login → logout → get_raw_session senaryosu
    # def test_session_data_cleared_after_logout(self):
    #     sm = SessionManager()
    #     sm.login("alice", "password123")
    #     sm.logout()
    #     raw = sm.get_raw_session()
    #     assert raw == {}  # Bu test FAIL olur!


class TestCounter:
    """Izole testler - reset sonrası history kontrolü yok."""
    
    def test_increment(self):
        c = Counter()
        assert c.increment() == 1
        assert c.increment() == 2
    
    def test_reset(self):
        c = Counter()
        c.increment()
        c.increment()
        c.reset()
        assert c.get_value() == 0
    
    def test_history(self):
        c = Counter()
        c.increment()
        c.increment()
        c.increment()
        assert c.get_history() == [1, 2, 3]
    
    # EKSIK TEST: reset sonrası history tutarsızlığı
    # def test_history_after_reset(self):
    #     c = Counter()
    #     c.increment()
    #     c.increment()
    #     c.reset()
    #     c.increment()
    #     # Beklenen: [1] ama gerçekte [1, 2, 1] dönüyor!
    #     assert c.get_history() == [1]  # FAIL
