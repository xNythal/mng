from PIL import Image
import typer

app = typer.Typer()


@app.command()
def view(path: str):
    with open(path, "rb") as f:
        data = f.read()

    if data[:3] != b"MNG":
        raise ValueError("Invalid MNG file: invalid magic bytes")

    width = int.from_bytes(data[3:5], "big")
    height = int.from_bytes(data[5:7], "big")
    pixels = data[7:]

    Image.frombytes("RGBA", (width, height), pixels).show()
    typer.echo(f"Displayed {path} ({width}x{height})")


@app.command()
def convert(input_path: str, output_path: str):
    if input_path.lower().endswith(".mng"):
        with open(input_path, "rb") as f:
            data = f.read()

        if data[:3] != b"MNG":
            raise ValueError("Invalid MNG file: invalid magic bytes")

        width = int.from_bytes(data[3:5], "big")
        height = int.from_bytes(data[5:7], "big")
        pixels = data[7:]

        expected_size = width * height * 4
        if len(pixels) != expected_size:
            raise ValueError(
                f"Invalid MNG file: expected {expected_size} pixel bytes, "
                f"got {len(pixels)}"
            )

        image = Image.frombytes("RGBA", (width, height), pixels)

        try:
            image.save(output_path)
        except OSError:
            image.convert("RGB").save(output_path)

        typer.echo(f"Converted {input_path} → {output_path}")

    else:
        image = Image.open(input_path).convert("RGBA")

        width, height = image.size
        pixels = image.tobytes()

        with open(output_path, "wb") as f:
            f.write(b"MNG")
            f.write(width.to_bytes(2, "big"))
            f.write(height.to_bytes(2, "big"))
            f.write(pixels)

        typer.echo(f"Converted {input_path} → {output_path} ({width}x{height})")


if __name__ == "__main__":
    app()
