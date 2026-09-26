from PIL import Image
import typer
from pathlib import Path
import lz4.frame
import time

app = typer.Typer()

HEADER_SIZE = 8
LENGTH_PREFIX_SIZE = 4


def read_header(f):
    magic = f.read(3)
    if magic != b"MNG":
        raise ValueError("Invalid MNG file: invalid magic bytes")

    rest = f.read(HEADER_SIZE - 3)
    if len(rest) < HEADER_SIZE - 3:
        raise ValueError("Invalid MNG file: missing width, height, or FPS")

    width = int.from_bytes(rest[0:2], "big")
    height = int.from_bytes(rest[2:4], "big")
    fps = rest[4]

    if fps == 0:
        raise ValueError("Invalid MNG file: FPS cannot be 0")

    return width, height, fps


def write_header(f, width, height, fps):
    f.write(b"MNG")
    f.write(width.to_bytes(2, "big"))
    f.write(height.to_bytes(2, "big"))
    f.write(bytes([fps]))


def read_compressed_frame(f):
    """Read and lz4-decompress one length-prefixed frame. Returns None at EOF."""
    length_bytes = f.read(LENGTH_PREFIX_SIZE)
    if len(length_bytes) == 0:
        return None
    if len(length_bytes) < LENGTH_PREFIX_SIZE:
        raise ValueError("Invalid MNG file: truncated frame length")

    length = int.from_bytes(length_bytes, "big")
    compressed = f.read(length)
    if len(compressed) < length:
        raise ValueError("Invalid MNG file: truncated frame data")

    return lz4.frame.decompress(compressed)


def write_compressed_frame(f, raw_bytes):
    compressed = lz4.frame.compress(raw_bytes)
    f.write(len(compressed).to_bytes(LENGTH_PREFIX_SIZE, "big"))
    f.write(compressed)


# Module-level accumulators for timing diagnostics
_timing_totals = {"read_lz4": 0.0, "count": 0}


def read_frame(f, frame_size):
    t0 = time.perf_counter()
    raw = read_compressed_frame(f)
    t1 = time.perf_counter()

    if raw is None:
        return None

    _timing_totals["read_lz4"] += (t1 - t0) * 1000
    _timing_totals["count"] += 1

    if _timing_totals["count"] % 30 == 0:
        n = _timing_totals["count"]
        print(f"[avg over {n} frames] read+lz4: {_timing_totals['read_lz4']/n:.1f}ms")

    if len(raw) != frame_size:
        raise ValueError(
            f"Invalid MNG file: decoded frame size {len(raw)} "
            f"does not match expected {frame_size} bytes"
        )

    return raw


def write_frame(f, raw_bytes):
    write_compressed_frame(f, raw_bytes)


@app.command()
def view(path: str):
    import pygame

    with open(path, "rb") as f:
        width, height, fps = read_header(f)
        frame_size = width * height * 4

        pygame.init()

        screen = pygame.display.set_mode(
            (width, height),
            pygame.RESIZABLE | pygame.SCALED,
        )

        pygame.display.set_caption(f"{path} ({width}x{height} @ {fps} FPS)")

        clock = pygame.time.Clock()

        first_frame_offset = f.tell()
        frame_count = 0
        running = True

        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
            if not running:
                break

            raw = read_frame(f, frame_size)

            if raw is None:
                if frame_count == 0:
                    raise ValueError("Invalid MNG file: contains no frames")
                f.seek(first_frame_offset)
                continue

            frame_count += 1

            surface = pygame.image.frombuffer(raw, (width, height), "RGBA").convert(
                screen
            )
            screen.blit(surface, (0, 0))
            pygame.display.flip()
            clock.tick(fps)

    pygame.quit()

    typer.echo(f"Displayed {path} ({width}x{height} @ {fps} FPS, {frame_count} frames)")


@app.command()
def convert(input_path: str, output_path: str, fps: int = 30):
    if not 0 <= fps <= 255:
        raise ValueError("FPS must be between 0 and 255")

    if input_path.lower().endswith(".mng"):
        with open(input_path, "rb") as f:
            width, height, in_fps = read_header(f)
            frame_size = width * height * 4

            output_extension = Path(output_path).suffix.lower()

            image_extensions = {
                ".png",
                ".jpg",
                ".jpeg",
                ".webp",
                ".bmp",
                ".tiff",
                ".tif",
            }

            if output_extension in image_extensions:
                raw = read_frame(f, frame_size)
                if raw is None:
                    raise ValueError("Invalid MNG file: contains no frames")

                image = Image.frombytes("RGBA", (width, height), raw)

                try:
                    image.save(output_path)
                except OSError:
                    image.convert("RGB").save(output_path)

                typer.echo(
                    f"Converted {input_path} -> {output_path} "
                    f"(first frame, {width}x{height})"
                )

                return

            import av

            try:
                output = av.open(output_path, mode="w")
            except av.error.FFmpegError as e:
                raise ValueError(f"Unable to open output file: {e}") from e

            with output:
                stream = output.add_stream("libx264", rate=in_fps)
                stream.width = width
                stream.height = height
                stream.pix_fmt = "yuv420p"

                frame_count = 0

                while True:
                    raw = read_frame(f, frame_size)
                    if raw is None:
                        break

                    image = Image.frombytes("RGBA", (width, height), raw)
                    frame = av.VideoFrame.from_image(image)

                    for packet in stream.encode(frame):
                        output.mux(packet)

                    frame_count += 1

                for packet in stream.encode():
                    output.mux(packet)

            if frame_count == 0:
                raise ValueError("Invalid MNG file: contains no frames")

            typer.echo(
                f"Converted {input_path} -> {output_path} "
                f"({width}x{height} @ {in_fps} FPS, {frame_count} frames)"
            )

            return

    import av

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

                    write_header(f, width, height, fps)

                elif image.size != (width, height):
                    raise ValueError(
                        f"All MNG frames must have the same dimensions: "
                        f"expected {width}x{height}, "
                        f"got {frame_width}x{frame_height}"
                    )

                write_frame(f, image.tobytes())
                frame_count += 1

    if frame_count == 0:
        raise ValueError("Input contains no frames")

    typer.echo(
        f"Converted {input_path} -> {output_path} "
        f"({width}x{height} @ {fps} FPS, {frame_count} frames)"
    )


if __name__ == "__main__":
    app()
