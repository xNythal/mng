from PIL import Image
import typer
import av

app = typer.Typer()

HEADER_SIZE = 8


@app.command()
def view(path: str):
    import pygame

    with open(path, "rb") as f:
        data = f.read()

    if data[:3] != b"MNG":
        raise ValueError("Invalid MNG file: invalid magic bytes")

    if len(data) < HEADER_SIZE:
        raise ValueError("Invalid MNG file: missing width, height, or FPS")

    width = int.from_bytes(data[3:5], "big")
    height = int.from_bytes(data[5:7], "big")
    fps = data[7]
    pixels = data[HEADER_SIZE:]

    if fps == 0:
        raise ValueError("Invalid MNG file: FPS cannot be 0")

    frame_size = width * height * 4

    if len(pixels) % frame_size != 0:
        raise ValueError(
            f"Invalid MNG file: pixel data is not divisible by frame size "
            f"({frame_size} bytes)"
        )

    frame_count = len(pixels) // frame_size

    if frame_count == 0:
        raise ValueError("Invalid MNG file: contains no frames")

    pygame.init()

    screen = pygame.display.set_mode(
        (width, height),
        pygame.RESIZABLE | pygame.SCALED,
    )

    pygame.display.set_caption(f"{path} ({width}x{height} @ {fps} FPS)")

    clock = pygame.time.Clock()

    running = True
    frame_index = 0

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        start = frame_index * frame_size
        end = start + frame_size

        surface = pygame.image.frombytes(
            pixels[start:end],
            (width, height),
            "RGBA",
        )

        screen.blit(surface, (0, 0))
        pygame.display.flip()

        frame_index = (frame_index + 1) % frame_count

        clock.tick(fps)

    pygame.quit()

    typer.echo(
        f"Displayed {path} " f"({width}x{height} @ {fps} FPS, {frame_count} frames)"
    )


@app.command()
def convert(input_path: str, output_path: str, fps: int = 30):
    if not 0 <= fps <= 255:
        raise ValueError("FPS must be between 0 and 255")

    if input_path.lower().endswith(".mng"):
        with open(input_path, "rb") as f:
            data = f.read()

        if data[:3] != b"MNG":
            raise ValueError("Invalid MNG file: invalid magic bytes")

        if len(data) < HEADER_SIZE:
            raise ValueError("Invalid MNG file: missing width, height, or FPS")

        width = int.from_bytes(data[3:5], "big")
        height = int.from_bytes(data[5:7], "big")
        fps = data[7]
        pixels = data[HEADER_SIZE:]

        frame_size = width * height * 4

        if len(pixels) % frame_size != 0:
            raise ValueError(
                f"Invalid MNG file: pixel data is not divisible by frame size "
                f"({frame_size} bytes)"
            )

        frame_count = len(pixels) // frame_size

        typer.echo(
            f"Converted {input_path} → {output_path} "
            f"({width}x{height} @ {fps} FPS, {frame_count} frames)"
        )

        # For now, only save the first frame.
        image = Image.frombytes("RGBA", (width, height), pixels[:frame_size])

        try:
            image.save(output_path)
        except OSError:
            image.convert("RGB").save(output_path)

        return

    try:
        container = av.open(input_path)
    except av.error.FFmpegError as e:
        raise ValueError(f"Unable to open input file: {e}") from e

    width = None
    height = None
    frame_count = 0

    with container:
        video_stream = next(
            (stream for stream in container.streams if stream.type == "video"),
            None,
        )

        if video_stream is None:
            raise ValueError("Input file contains no video stream")

        with open(output_path, "wb") as f:
            for frame in container.decode(video=video_stream.index):
                image = frame.to_image().convert("RGBA")

                frame_width, frame_height = image.size

                if width is None:
                    width = frame_width
                    height = frame_height

                    if width > 65535 or height > 65535:
                        raise ValueError("MNG dimensions cannot exceed 65535x65535")

                    f.write(b"MNG")
                    f.write(width.to_bytes(2, "big"))
                    f.write(height.to_bytes(2, "big"))
                    f.write(bytes([fps]))

                elif image.size != (width, height):
                    raise ValueError(
                        f"All MNG frames must have the same dimensions: "
                        f"expected {width}x{height}, got {frame_width}x{frame_height}"
                    )

                f.write(image.tobytes())
                frame_count += 1

    if frame_count == 0:
        raise ValueError("Input contains no frames")

    typer.echo(
        f"Converted {input_path} → {output_path} "
        f"({width}x{height} @ {fps} FPS, {frame_count} frames)"
    )


if __name__ == "__main__":
    app()
