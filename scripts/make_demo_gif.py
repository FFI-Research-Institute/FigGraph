"""Render the README demo GIF — a simulated terminal running `figraph search`.

Self-contained and reproducible (no ttyd/ffmpeg/vhs): draws frames with Pillow
and writes an animated GIF. Shows real FigGraph output text only — never a figure
image — so it is copyright-safe.

    python scripts/make_demo_gif.py
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT_DIR = "/usr/share/fonts/truetype/dejavu"
FONT = ImageFont.truetype(f"{FONT_DIR}/DejaVuSansMono.ttf", 17)
BOLD = ImageFont.truetype(f"{FONT_DIR}/DejaVuSansMono-Bold.ttf", 17)
CW = FONT.getlength("M")
LH = 26
W, H = 920, 326
PAD, TOP = 26, 60

BG, BAR, BORDER = (13, 17, 23), (22, 27, 34), (48, 54, 61)
C = {
    "prompt": (63, 185, 80), "cmd": (230, 237, 243), "num": (110, 118, 129),
    "journal": (88, 166, 255), "dot": (110, 118, 129), "title": (139, 148, 158),
    "path": (121, 192, 255), "tag": (210, 168, 255), "hint": (88, 96, 105),
}

# (command, [(title, path, tags), ...]) — real output captured from the tool.
SCREENS = [
    ('$ figraph search "kaplan-meier survival hazard ratio"', [
        ("Nature 2023 · Clinical trial links oncolytic immunoactivation to survival",
         "figures/nature/2023/s41586-023-06623-2_Fig1.png", "survival"),
        ("Nature 2023 · Y chromosome loss in cancer drives immune evasion",
         "figures/nature/2023/s41586-023-06234-x_Fig1.png", "box heatmap survival"),
    ]),
    ('$ figraph search "single-cell umap clusters" --tag umap-tsne', [
        ("Nature 2023 · Diverse clonal fates emerge on drug treatment of cancer",
         "figures/nature/2023/s41586-023-06342-8_Fig1.png", "umap-tsne schematic"),
        ("Nature 2023 · A pan-grass transcriptome of cellular divergence in crops",
         "figures/nature/2023/s41586-023-06053-0_Fig1.png", "heatmap umap-tsne"),
    ]),
    ('$ figraph search "phylogenetic tree"', [
        ("Nature 2023 · Mirusviruses link herpesviruses to giant viruses",
         "figures/nature/2023/s41586-023-05962-4_Fig2.png", "tree"),
        ("Nature 2023 · Tracking lung-cancer dissemination in TRACERx via ctDNA",
         "figures/nature/2023/s41586-023-05776-4_Fig5.png", "survival tree"),
    ]),
]


def base():
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W - 1, 36], fill=BAR)
    d.line([0, 36, W, 36], fill=BORDER)
    for i, col in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse([20 + i * 22, 12, 32 + i * 22, 24], fill=col)
    d.text((W / 2, 18), "figraph — search a folder of figures", font=FONT,
           fill=(110, 118, 129), anchor="mm")
    return img, d


def seg_line(d, y, segs):
    x = PAD
    for text, col in segs:
        d.text((x, y), text, font=FONT, fill=col)
        x += len(text) * CW


def render(lines):
    img, d = base()
    for i, segs in enumerate(lines):
        seg_line(d, TOP + i * LH, segs)
    return img


def add(frames, lines, dur):
    frames.append((render(lines), dur))


def build():
    frames = []
    for cmd, results in SCREENS:
        body = cmd[2:]
        # type the command out
        for n in range(0, len(body) + 1, 3):
            add(frames, [[("$ ", C["prompt"]), (body[:n], C["cmd"]),
                          ("█", C["cmd"])]], 35)
        cmdline = [("$ ", C["prompt"]), (body, C["cmd"])]
        lines = [cmdline, []]
        add(frames, lines, 350)
        # reveal results line by line
        for j, (title, path, tags) in enumerate(results, 1):
            lines = lines + [[(f"  {j}. ", C["num"]),
                              (title[:11], C["journal"]), (title[11:], C["title"])]]
            add(frames, lines, 130)
            lines = lines + [[("     ", C["num"]), (path, C["path"]),
                              ("   [" + tags + "]", C["tag"])]]
            add(frames, lines, 130)
        lines = lines + [[], [("  → open the top path to see the exemplar",
                               C["hint"])]]
        add(frames, lines, 2100)
    return frames


def main():
    frames = build()
    imgs = [f[0].convert("P", palette=Image.ADAPTIVE) for f in frames]
    durs = [f[1] for f in frames]
    out = Path("docs/demo.gif")
    imgs[0].save(out, save_all=True, append_images=imgs[1:], duration=durs,
                 loop=0, disposal=2, optimize=True)
    kb = out.stat().st_size / 1024
    print(f"wrote {out}  ({len(frames)} frames, {kb:.0f} KB)")


if __name__ == "__main__":
    main()
