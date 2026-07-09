import os
import win32com.client

user_profile = os.environ.get("USERPROFILE")
desktop_dir = os.path.join(user_profile, "Desktop")
shortcut_path = os.path.join(desktop_dir, "ULTRON.lnk")

if os.path.exists(shortcut_path):
    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(shortcut_path)
    print(f"Target: {shortcut.TargetPath}")
    print(f"Start In: {shortcut.WorkingDirectory}")
    print(f"Icon Location: {shortcut.IconLocation}")
    print(f"Arguments: {shortcut.Arguments}")
    
    print(f"Target Exists: {os.path.exists(shortcut.TargetPath)}")
    print(f"Start In Exists: {os.path.exists(shortcut.WorkingDirectory)}")
    
    # Extract icon path (ignore the comma index)
    icon_path = shortcut.IconLocation.split(",")[0] if shortcut.IconLocation else ""
    print(f"Icon Exists: {os.path.exists(icon_path)}")
else:
    print("Shortcut does not exist!")
