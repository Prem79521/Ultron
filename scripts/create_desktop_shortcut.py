"""
ULTRON Desktop Shortcut Generator — Automatically registers ULTRON with the Windows Desktop.
"""

import os
import sys
import win32com.client

def main():
    print("[ULTRON] Registering Desktop Launcher...")
    
    # 1. Resolve paths
    project_dir = r"c:\Users\craft\Desktop\Ultron"
    target_path = os.path.join(project_dir, "run_ultron.bat")
    icon_path = os.path.join(project_dir, "assets", "icons", "ultron.ico")
    
    # Resolve User Desktop path
    user_profile = os.environ.get("USERPROFILE")
    if not user_profile:
        print("[ERROR] Could not resolve USERPROFILE environment variable.")
        sys.exit(1)
        
    desktop_dir = os.path.join(user_profile, "Desktop")
    shortcut_path = os.path.join(desktop_dir, "ULTRON.lnk")
    
    # 2. Verify target files exist
    if not os.path.exists(target_path):
        print(f"[ERROR] Target launcher not found at: {target_path}")
        sys.exit(1)
        
    if not os.path.exists(icon_path):
        print(f"[ERROR] Icon file not found at: {icon_path}")
        sys.exit(1)

    # 3. Create Windows Shortcut using WScript COM shell
    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.TargetPath = target_path
        shortcut.WorkingDirectory = project_dir
        shortcut.IconLocation = f"{icon_path},0"
        shortcut.Description = "ULTRON Cognitive OS"
        
        # Style 7 runs the batch script minimized to hide unnecessary cmd windows
        shortcut.WindowStyle = 7
        shortcut.Save()
        
        # 4. Verify shortcut creation
        if os.path.exists(shortcut_path):
            print(f"[SUCCESS] Desktop shortcut created successfully: {shortcut_path}")
            print(f"Target: {target_path}")
            print(f"Icon: {icon_path}")
        else:
            print("[ERROR] Shortcut path verification failed after Save call.")
            sys.exit(1)
            
    except Exception as e:
        print(f"[ERROR] Shortcut installation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
