import sounddevice as sd
import time
import sys

print("Python version:", sys.version)
print("Sounddevice version:", sd.__version__)

devices = sd.query_devices()
print("\nAvailable Devices:")
for idx, d in enumerate(devices):
    print(f"[{idx}] {d['name']} (Inputs: {d.get('max_input_channels', 0)})")

default_input = sd.default.device[0]
print(f"\nDefault input device index: {default_input}")

# Try to capture a few samples
callback_count = 0
def callback(indata, frames, time_info, status):
    global callback_count
    callback_count += 1
    if callback_count <= 5:
        print(f"Callback {callback_count}: {len(indata)} frames, status: {status}, sample peak: {indata.max()}")

try:
    with sd.InputStream(samplerate=16000, channels=1, callback=callback):
        print("\nInputStream successfully opened. Recording for 2 seconds...")
        time.sleep(2.0)
except Exception as e:
    print(f"\nFailed to open InputStream: {e}")

print(f"\nTotal audio callbacks received: {callback_count}")
