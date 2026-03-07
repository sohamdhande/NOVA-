import os
import urllib.request

def download_kokoro():
    models_dir = os.path.expanduser(
        "~/.nova/models"
    )
    os.makedirs(models_dir, exist_ok=True)
    
    files = {
        "kokoro-v0_19.onnx": 
            "https://github.com/thewh1teagle/"
            "kokoro-onnx/releases/download/"
            "model-files/kokoro-v0_19.onnx",
        "voices.bin":
            "https://github.com/thewh1teagle/"
            "kokoro-onnx/releases/download/"
            "model-files/voices.bin"
    }
    
    for fname, url in files.items():
        path = os.path.join(models_dir, fname)
        if os.path.exists(path):
            print(f"✅ {fname} already exists")
            continue
        print(f"Downloading {fname}...")
        urllib.request.urlretrieve(url, path)
        print(f"✅ {fname} downloaded")
    
    print("\nKokoro models ready at:", models_dir)
    print("Update VoiceConfig to point to these paths.")

if __name__ == "__main__":
    download_kokoro()
