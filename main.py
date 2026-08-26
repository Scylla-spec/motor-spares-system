import sys
import logging
from PySide6.QtWidgets import QApplication

# Ensure paths are correct if running from root directory
from database.db_manager import initialize_database
from managers.auth_manager import ensure_default_admin
from ui.login_window import LoginWindow
from ui.dashboard import DashboardWindow

def main():
    # 1. Initialize Database Schema
    initialize_database()
    
    # 2. Ensure default admin exists
    ensure_default_admin()
    
    # 3. Setup GUI Application
    app = QApplication(sys.argv)
    
    # Set global modern ERP theme
    from ui.theme import GLOBAL_APP_QSS
    app.setStyle("Fusion")
    app.setStyleSheet(GLOBAL_APP_QSS)
    
    # 4. Show Login Window
    login = LoginWindow()
    
    # Variable to hold the dashboard reference so it doesn't get garbage collected
    dashboard = None 
    
    def on_login_success(user):
        nonlocal dashboard
        logging.info(f"Transitioning to dashboard for user: {user.username}")
        dashboard = DashboardWindow(current_user=user)
        dashboard.show()
    
    login.login_successful.connect(on_login_success)
    
    # We show the login window, and if it is accepted (login successful),
    # the event loop continues running the dashboard.
    login.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
