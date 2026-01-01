#!/usr/bin/env python3
"""
Génère un fichier `localstorage_seed.json` contenant une liste d'images
(relative URLs) à utiliser pour préremplir le localStorage via l'interface.
Par défaut cherche d'abord dans `images/.thumbs/` puis dans `images/`.
"""
import os
import json

ROOT = os.path.dirname(__file__)
IMAGES_DIR = os.path.join(ROOT, 'images')
THUMBS_DIR = os.path.join(IMAGES_DIR, '.thumbs')
OUT = os.path.join(ROOT, 'localstorage_seed.json')

EXTS = ('.jpg', '.jpeg', '.png', '.webp')

items = []

# prefer thumbs if available
if os.path.isdir(THUMBS_DIR):
    for dirpath, dirnames, filenames in os.walk(THUMBS_DIR):
        for fn in filenames:
            if fn.lower().endswith(EXTS):
                rel = os.path.relpath(os.path.join(dirpath, fn), ROOT).replace('\\', '/')
                items.append({'dataUrl': rel, 'title': '', 'desc': ''})
# fallback to images/
if not items and os.path.isdir(IMAGES_DIR):
    for dirpath, dirnames, filenames in os.walk(IMAGES_DIR):
        # skip .thumbs if present
        if os.path.basename(dirpath) == '.thumbs':
            continue
        for fn in filenames:
            if fn.lower().endswith(EXTS):
                rel = os.path.relpath(os.path.join(dirpath, fn), ROOT).replace('\\', '/')
                items.append({'dataUrl': rel, 'title': '', 'desc': ''})

# limit to 24 images for performance
items = items[:24]

with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(items, f, ensure_ascii=False, indent=2)

print(f'Wrote {len(items)} entries to {OUT}')
