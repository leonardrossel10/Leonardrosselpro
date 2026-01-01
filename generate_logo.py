#!/usr/bin/env python3
import os
from PIL import Image, ImageDraw, ImageFont

# Logo generator: white monogram on transparent background (no white fill)
w, h = 760, 180

# Transparent base
result = Image.new('RGBA', (w, h), (0, 0, 0, 0))
draw = ImageDraw.Draw(result)

# Load font
font = None
for path in ['/Library/Fonts/Arial Bold.ttf', '/Library/Fonts/Arial.ttf', '/System/Library/Fonts/SFNSDisplay.ttf', '/System/Library/Fonts/HelveticaNeueDeskInterface.ttc']:
    try:
        font = ImageFont.truetype(path, 140)
        break
    except Exception:
        font = None
if font is None:
    font = ImageFont.load_default()

text = 'LR'
if hasattr(draw, 'textbbox'):
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
else:
    tw, th = font.getsize(text)

text_x = (w - tw) / 2
text_y = (h - th) / 2 - 6

# White monogram text only — bars are rendered via CSS in the banner
draw.text((text_x, text_y), text, font=font, fill=(255,255,255,255))

# Save as PNG with transparency
project_path = os.path.join(os.path.dirname(__file__), 'logo_white.png')
desktop_path = os.path.expanduser('~/Desktop/logo_white.png')
result.save(project_path, format='PNG')
result.save(desktop_path, format='PNG')
print('Saved:', project_path)
print('Saved:', desktop_path)
