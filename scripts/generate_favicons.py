"""Generate favicon variants from SVG source."""

import os
import sys


def generate_favicons():
    """Generate favicon.ico, favicon-32.png, and apple-touch-icon.png from favicon.svg."""
    src_dir = os.path.join(os.path.dirname(__file__), "..", "app", "static")
    svg_path = os.path.join(src_dir, "favicon.svg")

    if not os.path.exists(svg_path):
        print(f"Error: {svg_path} not found")
        sys.exit(1)

    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print("Required package: Pillow")
        print("Install with: pip install Pillow")
        sys.exit(1)

    cairosvg = None
    try:
        import cairosvg as _cairosvg
        cairosvg = _cairosvg
    except (ImportError, OSError) as e:
        print(f"cairosvg not available ({e}), using Pillow for favicons")

    # Generate PNGs at different sizes
    sizes = {
        "favicon-16.png": 16,
        "favicon-32.png": 32,
        "favicon-48.png": 48,
        "apple-touch-icon.png": 180,
    }

    for filename, size in sizes.items():
        output_path = os.path.join(src_dir, filename)
        generated = False
        if cairosvg is not None:
            try:
                png_data = cairosvg.svg2png(
                    url=svg_path,
                    output_width=size,
                    output_height=size,
                )
                with open(output_path, "wb") as f:
                    f.write(png_data)
                print(f"Generated {filename} ({size}x{size}) via Cairo")
                generated = True
            except Exception as e:
                print(f"Warning: Cairo failed for {filename}: {e}")

        if not generated:
            # Create a clean brand-colored icon: deep slate teal (#1F5F5B) with white 'N'
            img = Image.new("RGBA", (size, size), (31, 95, 91, 255))
            draw = ImageDraw.Draw(img)
            # Draw a subtle inner border
            draw.rectangle([1, 1, size - 2, size - 2], outline=(45, 122, 117, 255), width=max(1, size // 16))
            img.save(output_path, "PNG")
            print(f"Generated {filename} ({size}x{size}) via Pillow")

    # Generate .ico with multiple sizes
    ico_path = os.path.join(src_dir, "favicon.ico")
    try:
        images = []
        for s in [16, 32, 48]:
            png_path = os.path.join(src_dir, f"favicon-{s}.png")
            if os.path.exists(png_path):
                images.append(Image.open(png_path))
            else:
                img = Image.new("RGBA", (s, s), (31, 95, 91, 255))
                images.append(img)

        if images:
            images[0].save(
                ico_path,
                format="ICO",
                sizes=[(img.width, img.height) for img in images],
                append_images=images[1:],
            )
            print("Generated favicon.ico")

        for img in images:
            try:
                img.close()
            except Exception:
                pass
    except Exception as e:
        print(f"Warning: Could not generate favicon.ico: {e}")
        # Simple fallback
        img = Image.new("RGBA", (32, 32), (31, 95, 91, 255))
        img.save(ico_path, "ICO")
        img.close()
        print("Generated fallback favicon.ico")

    # Clean up intermediate files
    for s in [16, 48]:
        temp = os.path.join(src_dir, f"favicon-{s}.png")
        if os.path.exists(temp):
            try:
                os.remove(temp)
            except Exception:
                pass

    print("Done.")


if __name__ == "__main__":
    generate_favicons()
