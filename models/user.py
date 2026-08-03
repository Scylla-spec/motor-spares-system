class User:
    """Data model representing a system user."""
    def __init__(self, user_id: int, username: str, password_hash: str, role: str):
        self.user_id = user_id
        self.username = username
        self.password_hash = password_hash
        self.role = role  # 'Cashier' or 'Admin'

    def is_admin(self) -> bool:
        return self.role == 'Admin'

    def __repr__(self):
        return f"<User id={self.user_id} username='{self.username}' role='{self.role}'>"