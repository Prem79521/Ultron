"""
SAPI5 Recognizer and Capability Inspector
Enumerates installed recognizers, their attributes, registry properties,
active engine status, and queries SAPI capabilities for command-and-control.
"""

import sys
import os
import winreg
import pythoncom
import win32com.client

def inspect_registry_recognizers():
    print("=== INSPECTING REGISTRY RECOGNIZERS ===")
    key_path = r"SOFTWARE\Microsoft\Speech\Recognizers"
    try:
        reg_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path)
    except Exception as e:
        print(f"Failed to open registry key: {e}")
        return

    num_subkeys, num_values, last_modified = winreg.QueryInfoKey(reg_key)
    print(f"Found {num_subkeys} installed recognizer subkeys.")

    for i in range(num_subkeys):
        subkey_name = winreg.EnumKey(reg_key, i)
        print(f"\n[{i}] Recognizer Subkey: {subkey_name}")
        subkey_path = f"{key_path}\\{subkey_name}"
        try:
            subkey = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, subkey_path)
            # Print values in the main key
            num_val = winreg.QueryInfoKey(subkey)[1]
            for j in range(num_val):
                val_name, val_data, val_type = winreg.EnumValue(subkey, j)
                print(f"  - {val_name}: {val_data}")
            
            # Print attributes
            try:
                attr_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, f"{subkey_path}\\Attributes")
                num_attr = winreg.QueryInfoKey(attr_key)[1]
                print("  Attributes:")
                for j in range(num_attr):
                    val_name, val_data, val_type = winreg.EnumValue(attr_key, j)
                    print(f"    * {val_name}: {val_data}")
                winreg.CloseKey(attr_key)
            except Exception:
                print("  No 'Attributes' subkey found.")
                
            winreg.CloseKey(subkey)
        except Exception as e:
            print(f"  Error reading subkey: {e}")
            
    winreg.CloseKey(reg_key)

def inspect_sapi_objects():
    print("\n=== INSPECTING SAPI OBJECTS AND CAPABILITIES ===")
    pythoncom.CoInitialize()
    try:
        # Create InProc Recognizer
        engine = win32com.client.Dispatch("SAPI.SpInprocRecognizer")
        
        # Enumerate tokens using SAPI SpObjectTokenCategory
        cat = win32com.client.Dispatch("SAPI.SpObjectTokenCategory")
        cat.SetId(r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\Recognizers", False)
        tokens = cat.EnumerateTokens()
        print(f"SAPI Reports {tokens.Count} recognizers installed.")
        for i in range(tokens.Count):
            token = tokens.Item(i)
            print(f"\nSAPI Recognizer [{i}]:")
            print(f"  Id: {token.Id}")
            print(f"  Description: {token.GetDescription()}")
            
            # Query Attributes via Token helper
            try:
                # Languages are usually space separated LCIDs in hex
                languages = token.GetAttribute("Language")
                print(f"  Language Attribute: {languages}")
            except Exception as e:
                print(f"  Could not get Language attribute: {e}")
                
            try:
                attributes = token.GetAttribute("Attributes")
                print(f"  Attributes: {attributes}")
            except Exception as e:
                print(f"  Could not get Attributes: {e}")

        # Active Recognizer
        print("\nActive Recognizer info:")
        try:
            active_token = engine.Recognizer
            print(f"  Active Recognizer Id: {active_token.Id}")
            print(f"  Active Description: {active_token.GetDescription()}")
        except Exception as e:
            print(f"  Could not retrieve engine.Recognizer: {e}")
            
        # Audio Format Capabilities
        try:
            audio_token = engine.AudioInput
            print(f"\nBound Audio Input: {audio_token.GetDescription() if audio_token else 'None'}")
        except Exception as e:
            print(f"  Could not query AudioInput: {e}")

    except Exception as e:
        print(f"SAPI error: {e}")
    finally:
        pythoncom.CoUninitialize()

if __name__ == "__main__":
    inspect_registry_recognizers()
    inspect_sapi_objects()
