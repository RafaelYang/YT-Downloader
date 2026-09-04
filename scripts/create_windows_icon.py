"""Generate the Windows application icon used by PyInstaller and Inno Setup."""

from pathlib import Path

from PIL import Image, ImageDraw


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT = PROJECT_ROOT / "build" / "windows" / "app-icon.ico"


def main() -> None:
    size = 256
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        (8, 8, size - 8, size - 8),
        radius=58,
        fill=(92, 69, 220, 255),
    )
    draw.polygon(
        ((96, 66), (96, 190), (194, 128)),
        fill=(255, 255, 255, 255),
    )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(
        OUTPUT,
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print(f"Created Windows icon: {OUTPUT}")


if __name__ == "__main__":
    main()
