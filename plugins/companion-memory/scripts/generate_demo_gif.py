#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from typing import Iterable


WIDTH = 960
HEIGHT = 540
SCALE = 4
FONT_W = 5
FONT_H = 7
CHAR_W = (FONT_W + 1) * SCALE
LINE_H = 11 * SCALE
OUT = Path(__file__).resolve().parents[1] / "assets" / "demo.gif"

PALETTE = [
    (11, 16, 32),
    (17, 24, 39),
    (229, 231, 235),
    (52, 211, 153),
    (251, 113, 133),
    (250, 204, 21),
    (100, 116, 139),
    (248, 113, 113),
]

FONT = {
    " ": ["00000", "00000", "00000", "00000", "00000", "00000", "00000"],
    "$": ["01110", "10100", "10100", "01110", "00101", "00101", "11110"],
    "-": ["00000", "00000", "00000", "11111", "00000", "00000", "00000"],
    ":": ["00000", "00100", "00100", "00000", "00100", "00100", "00000"],
    ".": ["00000", "00000", "00000", "00000", "00000", "01100", "01100"],
    ",": ["00000", "00000", "00000", "00000", "00100", "00100", "01000"],
    ">": ["10000", "01000", "00100", "00010", "00100", "01000", "10000"],
    "0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
    "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    "2": ["01110", "10001", "00001", "00010", "00100", "01000", "11111"],
    "3": ["11110", "00001", "00001", "01110", "00001", "00001", "11110"],
    "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
    "5": ["11111", "10000", "10000", "11110", "00001", "00001", "11110"],
    "6": ["01110", "10000", "10000", "11110", "10001", "10001", "01110"],
    "7": ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
    "8": ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
    "9": ["01110", "10001", "10001", "01111", "00001", "00001", "01110"],
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "B": ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
    "C": ["01111", "10000", "10000", "10000", "10000", "10000", "01111"],
    "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "F": ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
    "G": ["01111", "10000", "10000", "10011", "10001", "10001", "01110"],
    "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    "I": ["01110", "00100", "00100", "00100", "00100", "00100", "01110"],
    "J": ["00111", "00010", "00010", "00010", "00010", "10010", "01100"],
    "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    "Q": ["01110", "10001", "10001", "10001", "10101", "10010", "01101"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    "V": ["10001", "10001", "10001", "10001", "10001", "01010", "00100"],
    "W": ["10001", "10001", "10001", "10101", "10101", "10101", "01010"],
    "X": ["10001", "10001", "01010", "00100", "01010", "10001", "10001"],
    "Y": ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
    "Z": ["11111", "00001", "00010", "00100", "01000", "10000", "11111"],
}


def blank() -> list[int]:
    return [0] * (WIDTH * HEIGHT)


def rect(pixels: list[int], x: int, y: int, w: int, h: int, color: int) -> None:
    x0 = max(0, x)
    y0 = max(0, y)
    x1 = min(WIDTH, x + w)
    y1 = min(HEIGHT, y + h)
    for yy in range(y0, y1):
        start = yy * WIDTH
        pixels[start + x0 : start + x1] = [color] * (x1 - x0)


def text(pixels: list[int], x: int, y: int, value: str, color: int) -> None:
    cursor = x
    for char in value.upper():
        glyph = FONT.get(char, FONT[" "])
        for gy, row in enumerate(glyph):
            for gx, bit in enumerate(row):
                if bit == "1":
                    rect(pixels, cursor + gx * SCALE, y + gy * SCALE, SCALE, SCALE, color)
        cursor += CHAR_W


def frame(lines: list[tuple[str, int]]) -> list[int]:
    pixels = blank()
    rect(pixels, 42, 34, 876, 472, 1)
    rect(pixels, 42, 34, 876, 48, 6)
    rect(pixels, 66, 52, 12, 12, 7)
    rect(pixels, 88, 52, 12, 12, 5)
    rect(pixels, 110, 52, 12, 12, 3)
    text(pixels, 154, 49, "AI RELATIONSHIP MEMORY", 2)
    y = 116
    for line, color in lines:
        text(pixels, 78, y, line, color)
        y += LINE_H
    return pixels


def bitpack(codes: Iterable[tuple[int, int]]) -> bytes:
    data = bytearray()
    acc = 0
    bits = 0
    for code, size in codes:
        acc |= code << bits
        bits += size
        while bits >= 8:
            data.append(acc & 0xFF)
            acc >>= 8
            bits -= 8
    if bits:
        data.append(acc & 0xFF)
    return bytes(data)


def lzw(indices: list[int], min_size: int = 3) -> bytes:
    clear = 1 << min_size
    end = clear + 1
    next_code = end + 1
    code_size = min_size + 1
    table = {(i,): i for i in range(clear)}
    pending: list[tuple[int, int]] = [(clear, code_size)]
    phrase: tuple[int, ...] = ()
    for index in indices:
        candidate = phrase + (index,)
        if candidate in table:
            phrase = candidate
            continue
        pending.append((table[phrase], code_size))
        if next_code < 4096:
            table[candidate] = next_code
            next_code += 1
            if next_code == (1 << code_size) and code_size < 12:
                code_size += 1
        phrase = (index,)
    if phrase:
        pending.append((table[phrase], code_size))
    pending.append((end, code_size))
    return bitpack(pending)


def subblocks(data: bytes) -> bytes:
    chunks = bytearray()
    for i in range(0, len(data), 255):
        chunk = data[i : i + 255]
        chunks.append(len(chunk))
        chunks.extend(chunk)
    chunks.append(0)
    return bytes(chunks)


def write_gif(frames: list[list[int]], path: Path, delay: int = 90) -> None:
    payload = bytearray(b"GIF89a")
    payload.extend(WIDTH.to_bytes(2, "little"))
    payload.extend(HEIGHT.to_bytes(2, "little"))
    payload.extend(bytes([0xF2, 0, 0]))
    for red, green, blue in PALETTE:
        payload.extend(bytes([red, green, blue]))
    payload.extend(b"!\xFF\x0BNETSCAPE2.0\x03\x01\x00\x00\x00")
    for pixels in frames:
        payload.extend(b"!\xF9\x04\x04")
        payload.extend(delay.to_bytes(2, "little"))
        payload.extend(b"\x00\x00")
        payload.extend(b",\x00\x00\x00\x00")
        payload.extend(WIDTH.to_bytes(2, "little"))
        payload.extend(HEIGHT.to_bytes(2, "little"))
        payload.append(0)
        payload.append(3)
        payload.extend(subblocks(lzw(pixels)))
    payload.append(0x3B)
    path.write_bytes(payload)


def main() -> None:
    frames = [
        frame([("$ REMEMBER: CALL ME KAI", 3)]),
        frame([("$ REMEMBER: CALL ME KAI", 3), ("> SAVED LOCALLY IN SQLITE", 2)]),
        frame([
            ("$ RECALL NICKNAME", 3),
            ("> PREFERENCE: CALL USER KAI", 2),
            ("> SENSITIVE MEMORIES HIDDEN", 5),
        ]),
        frame([
            ("$ FORGET NICKNAME --PREVIEW", 3),
            ("> 1 MATCH, DRY RUN", 5),
            ("> NOTHING DELETED YET", 2),
        ]),
        frame([
            ("$ FORGET NICKNAME --CONFIRM", 3),
            ("> SOFT DELETED", 4),
            ("> EXPORT AND LIST STILL AVAILABLE", 2),
        ]),
    ]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    write_gif(frames, OUT)
    print(OUT)


if __name__ == "__main__":
    main()
