"""Render a word into scrolling frames for a 10x5 serpentine WS2812 matrix.

Outputs one hex frame per line (RRGGBB x 50) to stdout — the edge-net-gamepad
'frame' firmware blits each. Layout: 10 wide, 5 tall, serpentine (row 0 top,
left->right; row 1 right->left; ...). All the cleverness lives here, off-device.
"""
import sys

W, H = 10, 5
NUM = W * H

# 3x5 uppercase font: each glyph is 5 rows of 3 bits (top to bottom).
FONT = {
    "A": ["010", "101", "111", "101", "101"],
    "B": ["110", "101", "110", "101", "110"],
    "C": ["011", "100", "100", "100", "011"],
    "D": ["110", "101", "101", "101", "110"],
    "E": ["111", "100", "110", "100", "111"],
    "F": ["111", "100", "110", "100", "100"],
    "G": ["011", "100", "101", "101", "011"],
    "H": ["101", "101", "111", "101", "101"],
    "I": ["111", "010", "010", "010", "111"],
    "J": ["001", "001", "001", "101", "010"],
    "K": ["101", "101", "110", "101", "101"],
    "L": ["100", "100", "100", "100", "111"],
    "M": ["101", "111", "111", "101", "101"],
    "N": ["101", "111", "111", "111", "101"],
    "O": ["010", "101", "101", "101", "010"],
    "P": ["110", "101", "110", "100", "100"],
    "Q": ["010", "101", "101", "110", "011"],
    "R": ["110", "101", "110", "101", "101"],
    "S": ["011", "100", "010", "001", "110"],
    "T": ["111", "010", "010", "010", "010"],
    "U": ["101", "101", "101", "101", "111"],
    "V": ["101", "101", "101", "101", "010"],
    "W": ["101", "101", "111", "111", "101"],
    "X": ["101", "101", "010", "101", "101"],
    "Y": ["101", "101", "010", "010", "010"],
    "Z": ["111", "001", "010", "100", "111"],
    "0": ["111", "101", "101", "101", "111"],
    "1": ["010", "110", "010", "010", "111"],
    "2": ["111", "001", "111", "100", "111"],
    "3": ["111", "001", "111", "001", "111"],
    "4": ["101", "101", "111", "001", "001"],
    "5": ["111", "100", "111", "001", "111"],
    "6": ["111", "100", "111", "101", "111"],
    "7": ["111", "001", "010", "100", "100"],
    "8": ["111", "101", "111", "101", "111"],
    "9": ["111", "101", "111", "001", "111"],
    " ": ["000", "000", "000", "000", "000"],
    "-": ["000", "000", "111", "000", "000"],
    "!": ["010", "010", "010", "000", "010"],
}


def columns_for(text):
    """A list of columns; each column is a 5-bit list (top->bottom)."""
    cols = []
    for ch in text.upper():
        glyph = FONT.get(ch, FONT[" "])
        for c in range(3):
            cols.append([1 if glyph[r][c] == "1" else 0 for r in range(5)])
        cols.append([0, 0, 0, 0, 0])   # 1-col gap between letters
    return cols


def xy_to_index(x, y):
    """Serpentine: row 0 top L->R, row 1 R->L, ..."""
    return y * W + (x if y % 2 == 0 else (W - 1 - x))


def frame_hex(cols, start, colour):
    px = [(0, 0, 0)] * NUM
    for x in range(W):
        col = start + x
        if 0 <= col < len(cols):
            for y in range(H):
                if cols[col][y]:
                    px[xy_to_index(x, y)] = colour
    return "".join("%02x%02x%02x" % p for p in px)


def main():
    text = sys.argv[1] if len(sys.argv) > 1 else "EDGE NET"
    colour = (0, 200, 255)   # cyan text
    cols = [[0] * 5] * W + columns_for(text) + [[0] * 5] * W   # scroll in & out
    for start in range(len(cols) - W + 1):
        print(frame_hex(cols, start, colour))


if __name__ == "__main__":
    main()
