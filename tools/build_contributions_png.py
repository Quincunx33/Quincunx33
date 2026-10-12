from datetime import date
from pathlib import Path
import re
import requests
from PIL import Image, ImageDraw, ImageFont

USER = "Quincunx33"
html = requests.get(f"https://github.com/users/{USER}/contributions", timeout=20).text
cells = re.findall(r'<td[^>]*data-date="([^"]+)"[^>]*data-level="([0-4])"[^>]*>', html)
if not cells:
    raise RuntimeError("GitHub contribution calendar was not found")
levels = {day: int(level) for day, level in cells}
first = date.fromisoformat(cells[0][0])
last = date.fromisoformat(cells[-1][0])
active_days = sum(level > 0 for level in levels.values())

W, H = 1320, 300
img = Image.new("RGB", (W, H), "#0b1220")
d = ImageDraw.Draw(img)
font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
bold_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
title = ImageFont.truetype(bold_path, 24)
small = ImageFont.truetype(font_path, 14)
label = ImageFont.truetype(font_path, 13)

d.rounded_rectangle((0, 0, W - 1, H - 1), radius=16, fill="#0b1220", outline="#1e293b", width=2)
d.text((28, 22), "GitHub Contributions - Last Year", font=title, fill="#f8fafc")
summary = f"{active_days} active days"
summary_w = d.textbbox((0, 0), summary, font=small)[2]
d.text((W - 28 - summary_w, 29), summary, font=small, fill="#94a3b8")

left, top, cell, gap = 78, 78, 18, 5
colors = ["#172554", "#164e63", "#0891b2", "#22d3ee", "#a5f3fc"]
for text, row in [("Mon", 1), ("Wed", 3), ("Fri", 5)]:
    d.text((18, top + row * (cell + gap) + 2), text, font=label, fill="#94a3b8")

for index, (day, _) in enumerate(cells):
    current = date.fromisoformat(day)
    offset = (current - first).days
    x = left + (offset // 7) * (cell + gap)
    y = top + (offset % 7) * (cell + gap)
    d.rounded_rectangle((x, y, x + cell, y + cell), radius=4, fill=colors[levels[day]])

seen = set()
for index, (day, _) in enumerate(cells):
    current = date.fromisoformat(day)
    key = (current.year, current.month)
    if current.day <= 7 and current.weekday() == 0 and key not in seen:
        seen.add(key)
        offset = (current - first).days
        x = left + (offset // 7) * (cell + gap)
        d.text((x, 235), current.strftime("%b"), font=label, fill="#94a3b8")

legend_text = "Less"
legend_x, legend_y = W - 275, 255
d.text((legend_x, legend_y), legend_text, font=label, fill="#94a3b8")
for i, color in enumerate(colors):
    x = legend_x + 42 + i * 22
    d.rounded_rectangle((x, legend_y + 1, x + 16, legend_y + 17), radius=4, fill=color)
d.text((legend_x + 42 + len(colors) * 22 + 7, legend_y), "More", font=label, fill="#94a3b8")

out = Path(__file__).resolve().parents[1] / "assets" / "github-contributions.png"
img.save(out, optimize=True)
print(f"Wrote {out} with {len(cells)} days and {active_days} active days")
