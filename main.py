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
    # Ensure Windows taskbar groups and shows the custom app icon
    try:
        import ctypes
        myappid = "motorsparessystem.inventory.pos.1.0"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass

    app = QApplication(sys.argv)
    app.setApplicationName("Motor Spares System")
    app.setApplicationDisplayName("Motor Spares System")

    # Set application favicon/window icon
    import os
    from PySide6.QtGui import QIcon
    base_dir = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(base_dir, "assets", "icons", "favicon.ico")
    if not os.path.exists(icon_path):
        icon_path = os.path.join(base_dir, "assets", "icons", "favicon.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

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
