# MNG

**Mango Network Graphics**

A simple binary media format I made to learn how binary file formats work.

Currently, MNG supports:

- Images
- Multiple frames for video/animation
- Raw RGBA pixel data

Audio is planned, but isn't implemented yet.

## Format

```text
MNG
├── Header
│   ├── Width
│   ├── Height
│   ├── FPS
│   └── Frame count
└── Raw RGBA frames
```

The header uses big-endian integers.

The frame count is stored as a 3-byte unsigned integer because 2 bytes wasn't enough and 4 bytes felt unnecessary.

## Current state

MNG is still being worked on.

Currently implemented:

- Binary header
- Image/video conversion
- Raw RGBA frames
- MNG playback
- Multiple video frames
- 24-bit frame count

Planned:

- Audio support
- Compression

## Why?

Mostly because I wanted to learn how file formats actually work instead of just using existing ones.

It's also a project for learning more about binary data and how programs actually interpret files.

## Usage

If you downloaded the executable:

```bash
./mng convert input.mp4 output.mng
```

And to view an MNG file:

```bash
./mng view output.mng
```

If `mng` is installed somewhere in your `PATH`, you can just use:

```bash
mng convert input.mp4 output.mng
mng view output.mng
```

## Warning

MNG is **not** meant to replace PNG, WebP, MP4, etc.

It's currently extremely inefficient because frames are stored as raw RGBA data, so even a small video can produce a massive file.

That's kind of the point.
