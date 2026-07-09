from PIL import Image
import os

png_path = r"C:\Users\craft\.gemini\antigravity\brain\c0f01a1c-67b5-4767-9929-9a507b2a154d\ultron_icon_1783347765634.png"
ico_dir = r"c:\Users\craft\Desktop\Ultron\assets\icons"
ico_path = os.path.join(ico_dir, "ultron.ico")

os.makedirs(ico_dir, exist_ok=True)
img = Image.open(png_path)
img.save(ico_path, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
print("Icon conversion successful!")
