from PIL import Image
import os


def convert():
    if not os.path.exists("app_icon.png"):
        print("Error: app_icon.png not found")
        return

    try:
        img = Image.open("app_icon.png")
        # Save as ICO with multiple sizes for best Windows compatibility
        img.save(
            "app.ico",
            format="ICO",
            sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)],
        )
        print("Successfully created app.ico")
    except Exception as e:
        print(f"Error converting icon: {e}")


if __name__ == "__main__":
    convert()
