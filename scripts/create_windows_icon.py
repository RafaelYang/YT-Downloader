"""Generate the Windows icon from the shared branded application artwork."""

from pathlib import Path

from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCE = PROJECT_ROOT / "assets" / "app-icon.png"
OUTPUT = PROJECT_ROOT / "build" / "windows" / "app-icon.ico"


def main() -> None:
    if not SOURCE.is_file():
        raise FileNotFoundError(f"Missing application icon artwork: {SOURCE}")

    with Image.open(SOURCE) as source:
        image = source.convert("RGBA")
    if image.width != image.height:
        raise ValueError("Application icon artwork must be square")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(
        OUTPUT,
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print(f"Created Windows icon: {OUTPUT}")


if __name__ == "__main__":
    main()
