import os
from pathlib import Path
import html
import time
import subprocess
import datetime
import shutil
import json


# Project root and images folder
d = os.path.expanduser('~/Desktop/MonSitePhotos')
imgdir = os.path.join(d, 'images')

# Pillow for thumbnails
try:
    from PIL import Image
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

valid_ext = ('.jpg', '.jpeg', '.png', '.webp', '.gif')
# Bigger thumbnails: change this to adjust thumbnail pixel size
# Increased so regenerated thumbnails are larger for the gallery display
THUMB_MAX_SIZE = (2400, 1800)
THUMB_DIRNAME = '.thumbs'
# Toggle thumbnail generation. Set to False to always use original images in galleries.
USE_THUMBS = False

def slug(name: str) -> str:
    s = ''.join(c if c.isalnum() else '_' for c in name).strip('_')
    return s.lower() or 'group'

def ensure_thumb(src_rel):
    """Return relative thumbnail path for a source image path (e.g. 'images/folder/pic.jpg').
    Create thumbnail if PIL available and thumb missing or stale."""
    src_path = Path(d) / src_rel
    parts = src_rel.split(os.sep)
    if parts[0] != 'images':
        return src_rel
    # if thumbs are disabled, always use the original image
    if not USE_THUMBS:
        return src_rel
    thumb_parts = ['images', THUMB_DIRNAME] + parts[1:]
    thumb_rel = os.path.join(*thumb_parts)
    thumb_path = Path(d) / thumb_rel

    if not PIL_AVAILABLE:
        return src_rel

    try:
        src_mtime = src_path.stat().st_mtime
    except Exception:
        return src_rel

    thumb_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        if not thumb_path.exists() or thumb_path.stat().st_mtime < src_mtime:
            with Image.open(src_path) as im:
                # Use high-quality resampling
                resample = getattr(Image, 'Resampling', Image).LANCZOS
                im.thumbnail(THUMB_MAX_SIZE, resample=resample)
                if im.mode in ('RGBA', 'LA'):
                    thumb_path = thumb_path.with_suffix('.png')
                    im.save(thumb_path, format='PNG', optimize=True)
                else:
                    thumb_path = thumb_path.with_suffix('.jpg')
                    # Save as high-quality JPEG (less chroma subsampling, progressive)
                    im_rgb = im.convert('RGB')
                    im_rgb.save(
                        thumb_path,
                        format='JPEG',
                        quality=100,
                        optimize=True,
                        progressive=True,
                        subsampling=0,
                    )
                    # Also write a WebP variant for browsers that support it
                    try:
                        webp_path = thumb_path.with_suffix('.webp')
                        im_rgb.save(webp_path, format='WEBP', quality=95, method=6)
                    except Exception:
                        pass
    except Exception:
        return src_rel

    rel = os.path.relpath(thumb_path, d)
    return rel.replace('\\', '/')


def create_top_hero(src_abs_paths, out_rel='images/top_hero.jpg', height=1080):
    """Create a side-by-side image from up to two absolute image paths.
    Returns the project-relative path (posix) or None on failure.
    """
    if not PIL_AVAILABLE:
        return None
    try:
        imgs = []
        for p in src_abs_paths[:2]:
            if os.path.isfile(p):
                im = Image.open(p)
                imgs.append(im.copy())
                im.close()
        if not imgs:
            return None

        # Resize images to the same height while keeping aspect ratio
        resample = getattr(Image, 'Resampling', Image).LANCZOS
        resized = []
        for im in imgs:
            w, h = im.size
            new_w = int(w * (height / h))
            resized.append(im.resize((new_w, height), resample=resample))

        total_w = sum(im.size[0] for im in resized)
        mode = 'RGB'
        out_img = Image.new(mode, (total_w, height), (0, 0, 0))
        x = 0
        for im in resized:
            if im.mode != 'RGB':
                im = im.convert('RGB')
            out_img.paste(im, (x, 0))
            x += im.size[0]

        out_path = Path(d) / out_rel
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_img.save(str(out_path), format='JPEG', quality=100, optimize=True, progressive=True, subsampling=0)
        # Also write a WebP top-hero for modern browsers
        try:
            out_webp = out_path.with_suffix('.webp')
            out_img.save(out_webp, format='WEBP', quality=100, method=6)
        except Exception:
            pass
        out_img.close()
        for im in resized:
            im.close()
        rel = os.path.relpath(out_path, d).replace('\\', '/')
        return rel
    except Exception:
        return None


def collect_groups():
    groups = {}
    if os.path.isdir(imgdir):
        for entry in sorted(os.listdir(imgdir)):
            full = os.path.join(imgdir, entry)
            # Skip the profil folder (we don't want a "profil" group in galleries)
            if entry.lower() == 'profil':
                continue
            # Skip thumbnail cache folder and other hidden folders
            if entry == THUMB_DIRNAME or entry.startswith('.'):
                continue
            # Skip any dedicated miniature folders used as thumbnail repositories
            low = entry.lower()
            if low.startswith('miniature') or low == 'miniatures':
                continue
            if os.path.isdir(full):
                imgs = [os.path.join('images', entry, f) for f in sorted(os.listdir(full))
                        if f.lower().endswith(valid_ext)]
                if imgs:
                    groups[entry] = imgs
            elif os.path.isfile(full) and entry.lower().endswith(valid_ext):
                # skip loose files at project root (do not create a 'Général' group)
                continue
    return groups


def write_group_page(name, imgs):
    gslug = slug(name)
    outp = os.path.join(d, f'gallery_{gslug}.html')
    with open(outp, 'w', encoding='utf-8') as h:
        h.write('<!doctype html>\n<html>\n<head>\n  <meta charset="utf-8">\n')
        h.write(f'  <title>Portfolio — {html.escape(name)}</title>\n')
        h.write('  <meta name="viewport" content="width=device-width,initial-scale=1">\n')
        h.write('  <style>body{font-family:system-ui;padding:20px;padding-top:130px;padding-bottom:64px;max-width:1100px;margin:auto} '
            'h1{font-size:28px;margin-bottom:0.4rem} .gallery{display:flex;flex-wrap:wrap;gap:16px;margin-top:18px} '
            '.gallery a{display:block}.gallery img{width:420px;height:300px;object-fit:cover;border-radius:8px} '
            '.top-banner{position:fixed;left:0;right:0;top:0;height:110px;background:linear-gradient(90deg,#062047,#043059);z-index:1000;box-shadow:0 2px 6px rgba(0,0,0,0.25);display:flex;justify-content:center;align-items:center;padding:0 22px} .top-logo{height:72px;display:block;margin:0} '
            '.bottom-bar{position:fixed;left:0;right:0;bottom:0;height:48px;background:linear-gradient(90deg,#062047,#043059);display:flex;align-items:center;justify-content:center;color:#fff;font-weight:600;z-index:1000;transform:translateY(100%);transition:transform 220ms ease-in-out} .bottom-bar.visible{transform:translateY(0)} .bottom-bar a{color:#fff;text-decoration:none;margin:0 8px}</style>\n')
        h.write('</head>\n<body>\n')
        # fixed top banner with logo (logo_white.png expected at project root)
        logo_src = f'logo_white.png?v={int(time.time())}'
        h.write(f'<div class="top-banner"><img class="top-logo" src="{logo_src}" alt="LR"></div>\n')
        h.write(f'<h1>{html.escape(name)}</h1>\n')
        h.write('<p><a href="gallery.html">&larr; Retour</a></p>\n')
        h.write('<div class="section-label">Portfolio</div>\n')
        h.write('<div class="gallery">')
        for src in imgs:
                thumb = ensure_thumb(src)
                src_attr = thumb if thumb and thumb != src else src
                h.write(f'<a href="{src}" target="_blank">')
                # prefer webp if available
                if thumb and thumb != src:
                    webp_rel = os.path.splitext(thumb)[0] + '.webp'
                    if (Path(d) / webp_rel).exists():
                        h.write(f'<picture><source srcset="{webp_rel}" type="image/webp"><img src="{thumb}" loading="lazy" alt=""></picture>')
                    else:
                        h.write(f'<img src="{thumb}" loading="lazy" alt="">')
                else:
                    h.write(f'<img src="{src_attr}" loading="lazy" alt="">')
                h.write('</a>')
        h.write('</div>\n')
        # bottom contact bar
        h.write(f'<div class="bottom-bar"><span style="margin-right:8px">Mon Insta:</span><a href="https://instagram.com/leonard_rossel" target="_blank">@leonard_rossel</a><span style="margin:0 12px">·</span><span style="margin-right:8px">Mon mail:</span><a href="mailto:leonardrosselpro@gmail.com">leonardrosselpro@gmail.com</a></div>\n')
        h.write('<script>\n(function(){var bar=document.querySelector(\'.bottom-bar\');function check(){if(!bar) return; if((window.innerHeight+window.scrollY)>=document.documentElement.scrollHeight-2){bar.classList.add(\'visible\');}else{bar.classList.remove(\'visible\');}}window.addEventListener(\'scroll\',check,{passive:true});window.addEventListener(\'resize\',check);document.addEventListener(\'DOMContentLoaded\',check);check();})();\n</script>\n')
        h.write('<script>\n// profile video modal: open modal and play when play button clicked\n(function(){var play=document.querySelector(\'.play-button\');var modal=document.getElementById(\'video-modal\');var vid=modal?modal.querySelector(\'#profile-video\'):null;var closeBtn=modal?modal.querySelector(\'.video-close\'):null;function openVideo(){if(!modal||!vid) return;modal.classList.add(\'open\');try{vid.currentTime=0;vid.play();}catch(e){}}function closeVideo(){if(!modal||!vid) return;try{vid.pause();}catch(e){}modal.classList.remove(\'open\');}if(play){play.addEventListener(\'click\',function(e){e.preventDefault();openVideo();});}if(closeBtn){closeBtn.addEventListener(\'click\',function(e){e.preventDefault();closeVideo();});}if(modal){modal.addEventListener(\'click\',function(e){if(e.target===modal){closeVideo();}});document.addEventListener(\'keydown\',function(e){if(e.key===\'Escape\') closeVideo();});} })();\n</script>\n')
        h.write('<script>\n// profile video modal: open modal and play when play button clicked\n(function(){var play=document.querySelector(\'.play-button\');var modal=document.getElementById(\'video-modal\');var vid=modal?modal.querySelector(\'#profile-video\'):null;var closeBtn=modal?modal.querySelector(\'.video-close\'):null;function openVideo(){if(!modal||!vid) return;modal.classList.add(\'open\');try{vid.currentTime=0;vid.play();}catch(e){}}function closeVideo(){if(!modal||!vid) return;try{vid.pause();}catch(e){}modal.classList.remove(\'open\');}if(play){play.addEventListener(\'click\',function(e){e.preventDefault();openVideo();});}if(closeBtn){closeBtn.addEventListener(\'click\',function(e){e.preventDefault();closeVideo();});}if(modal){modal.addEventListener(\'click\',function(e){if(e.target===modal){closeVideo();}});document.addEventListener(\'keydown\',function(e){if(e.key===\'Escape\') closeVideo();});} })();\n</script>\n')
        h.write('<script>\n// profile video modal: open modal and play when play button clicked\n(function(){var play=document.querySelector(\'.play-button\');var modal=document.getElementById(\'video-modal\');var vid=modal?modal.querySelector(\'#profile-video\'):null;var closeBtn=modal?modal.querySelector(\'.video-close\'):null;function openVideo(){if(!modal||!vid) return;modal.classList.add(\'open\');try{vid.currentTime=0;vid.play();}catch(e){}}function closeVideo(){if(!modal||!vid) return;try{vid.pause();}catch(e){}modal.classList.remove(\'open\');}if(play){play.addEventListener(\'click\',function(e){e.preventDefault();openVideo();});}if(closeBtn){closeBtn.addEventListener(\'click\',function(e){e.preventDefault();closeVideo();});}if(modal){modal.addEventListener(\'click\',function(e){if(e.target===modal){closeVideo();}});document.addEventListener(\'keydown\',function(e){if(e.key===\'Escape\') closeVideo();});} })();\n</script>\n')
        h.write('</body>\n</html>')
    print('wrote', outp)


def write_index(groups):
    index_out = os.path.join(d, 'gallery.html')
    with open(index_out, 'w', encoding='utf-8') as h:
        h.write('<!doctype html>\n<html>\n<head>\n  <meta charset="utf-8">\n  <title>Portfolio</title>\n')
        h.write('  <meta name="viewport" content="width=device-width,initial-scale=1">\n')
        h.write('  <style>\n')
        h.write('    body{font-family:system-ui;padding:20px;padding-top:130px;padding-bottom:64px;max-width:1100px;margin:auto}\n')
        h.write('    h1{font-size:48px;margin-bottom:12px}\n')
        h.write('    .section-label{font-size:24px;color:#222;margin-bottom:14px;text-transform:uppercase;letter-spacing:0.08em;font-weight:800}\n')
        h.write('    p.lead{font-size:18px;color:#444;margin-top:0.2rem;margin-bottom:1rem;line-height:1.4}\n')
        h.write('    .top-banner{position:fixed;left:0;right:0;top:0;height:110px;background:linear-gradient(90deg,#062047,#043059);z-index:1000;box-shadow:0 2px 6px rgba(0,0,0,0.25);display:flex;align-items:center;padding-left:22px}\n')
        h.write('    .top-logo{height:72px;display:block}\n')
        h.write('    .hero{padding:12px 0 18px}\n')
        h.write('    .top-hero{display:flex;justify-content:center;gap:0;margin:0 auto 48px;max-width:1400px;position:relative;overflow:hidden}\n')
        h.write('    .top-hero img{width:50%;height:auto;object-fit:cover;border-radius:0;display:block;transition:transform 700ms ease}\n')
        h.write('    .top-hero.combined img{width:100%;height:auto;object-fit:cover;border-radius:0;display:block}\n')
        h.write('    .top-hero img + img{margin-left:0}\n')
        h.write('    .top-hero-caption{position:absolute;left:0;right:0;bottom:0;background:rgba(0,0,0,0.45);color:#fff;padding:12px 0;text-align:center;font-weight:800;font-size:28px;letter-spacing:0.02em;box-sizing:border-box}\n')
        h.write('    .play-button{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);width:84px;height:84px;border-radius:50%;background:rgba(0,0,0,0.55);border:2px solid rgba(255,255,255,0.9);display:flex;align-items:center;justify-content:center;cursor:pointer;z-index:20;transition:transform 220ms ease,box-shadow 220ms ease} .play-button:after{content:"";display:block;margin-left:6px;border-style:solid;border-width:12px 0 12px 20px;border-color:transparent transparent transparent #fff} .play-button:hover{transform:translate(-50%,-50%) scale(1.04);box-shadow:0 8px 20px rgba(6,32,71,0.18)}\n')
        h.write('    .groups{display:grid;grid-template-columns:repeat(2,1fr);gap:36px}\n')
        h.write('    .group{text-align:center;padding:6px}\n')
        h.write('    .group img{width:100%;height:380px;object-fit:cover;border-radius:8px;transition:transform 320ms cubic-bezier(.2,.8,.2,1),box-shadow 320ms ease}\n')
        h.write('    .group:hover img{transform:scale(1.04);box-shadow:0 12px 30px rgba(6,32,71,0.12)}\n')
        h.write('    .animate-on-scroll{opacity:0;transform:translateY(18px);transition:opacity 600ms ease,transform 600ms ease}\n')
        h.write('    .animate-on-scroll.visible{opacity:1;transform:none}\n')
        h.write('    @keyframes pulse{0%{transform:scale(1)}50%{transform:scale(1.06)}100%{transform:scale(1)}}\n')
        h.write('    .play-button{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);width:84px;height:84px;border-radius:50%;background:rgba(0,0,0,0.55);border:2px solid rgba(255,255,255,0.9);display:flex;align-items:center;justify-content:center;cursor:pointer;z-index:20} .play-button:after{content:\"\";display:block;margin-left:6px;border-style:solid;border-width:12px 0 12px 20px;border-color:transparent transparent transparent #fff}\n')
        h.write('    .video-modal{position:fixed;left:0;top:0;right:0;bottom:0;background:rgba(0,0,0,0.75);display:none;align-items:center;justify-content:center;z-index:2000} .video-modal.open{display:flex} .video-wrap{position:relative;max-width:92%;max-height:92%} .video-wrap video{width:100%;height:auto;border-radius:6px;background:#000} .video-close{position:absolute;right:-10px;top:-10px;background:#fff;color:#000;border:none;border-radius:50%;width:36px;height:36px;font-size:18px;cursor:pointer}\n')
        h.write('    .groups{display:grid;grid-template-columns:repeat(2,1fr);gap:36px}\n')
        h.write('    .group{text-align:center;padding:6px}\n')
        h.write('    .group img{width:100%;height:380px;object-fit:cover;border-radius:8px}\n')
        h.write('    .group .title{margin-top:10px;font-size:18px;font-weight:700;color:#222}\n')
        h.write('    .group a{color:inherit;text-decoration:none}\n')
        h.write('    @media(max-width:900px){.groups{grid-template-columns:1fr}.top-hero{flex-direction:column;align-items:center}.top-hero img{width:100%;height:auto;margin-left:0}}\n')
        h.write('    @media(max-width:600px){.top-logo{height:48px;padding-left:12px}}\n')
        h.write('    .bottom-bar{position:fixed;left:0;right:0;bottom:0;height:48px;background:linear-gradient(90deg,#062047,#043059);display:flex;align-items:center;justify-content:center;color:#fff;font-weight:600;z-index:1000;transform:translateY(100%);transition:transform 220ms ease-in-out} .bottom-bar.visible{transform:translateY(0)} .bottom-bar a{color:#fff;text-decoration:none;margin:0 8px}\n')
        h.write('    .section{margin-bottom:140px}\n')
        h.write('  </style>\n')
        h.write('</head>\n<body>\n')
        # fixed top banner with logo (logo_white.png expected at project root)
        logo_src = f'logo_white.png?v={int(time.time())}'
        h.write(f'<div class="top-banner"><img class="top-logo" src="{logo_src}" alt="LR"></div>\n')
        # Section 1 — Profil (deux images)
        h.write('<section class="section profile-section">')
        prof_dir = os.path.join(d, 'images', 'profil')
        if os.path.isdir(prof_dir):
            prof_imgs = [f for f in sorted(os.listdir(prof_dir)) if f.lower().endswith(valid_ext)]
            if prof_imgs:
                abs_paths = [os.path.join(prof_dir, f) for f in prof_imgs[:2]]
                # detect first video in profil/videos if present
                vids_dir = os.path.join(prof_dir, 'videos')
                video_rel = None
                if os.path.isdir(vids_dir):
                    vids = [f for f in sorted(os.listdir(vids_dir)) if f.lower().endswith(('.mp4', '.webm', '.mov', '.m4v', '.ogg'))]
                    if vids:
                        video_rel = os.path.join('images', 'profil', 'videos', vids[0]).replace('\\', '/')
                try:
                    create_top_hero(abs_paths, out_rel='images/top_hero.jpg', height=720)
                except Exception:
                    pass
                h.write('<div class="top-hero animate-on-scroll">')
                for fname in prof_imgs[:2]:
                    p = os.path.join('images', 'profil', fname)
                    h.write(f'<img src="{p}" alt="">')
                # overlay caption across both profile images
                h.write('<div class="top-hero-caption">Léonard Rossel</div>')
                # play button if a video is available
                if video_rel:
                    h.write(f'<button class="play-button" data-video="{video_rel}" aria-label="Play video"></button>')
                h.write('</div>\n')
                # video modal markup (outside top-hero) if video present
                if video_rel:
                    h.write(f'<div class="video-modal" id="video-modal">')
                    h.write('<div class="video-wrap">')
                    h.write(f'<video id="profile-video" controls playsinline preload="metadata">')
                    h.write(f'<source src="{video_rel}" />')
                    h.write('Your browser does not support the video tag.')
                    h.write('</video>')
                    h.write('<button class="video-close" aria-label="Close video">×</button>')
                    h.write('</div></div>')
        h.write('</section>\n')

        # Section 2 — Introspection (texte)
        h.write('<section class="section introspection-section">')
        h.write('<div class="section-label">Introspection</div>')
        h.write('<div class="hero">')
        h.write('  <p class="lead">Je m’appelle Léonard Rossel, j’ai 19 ans. Je suis en 3ᵉ année au CPNV en polymécanique et le sport fait partie de mon quotidien.</p>\n')
        h.write('  <p class="lead">La photo et la vidéo me passionnent depuis longtemps. J’ai toujours eu envie de raconter et de créer des histoires à travers elles. Je ne me suis simplement jamais lancé.</p>\n')
        h.write('  <p class="lead">Aujourd’hui, je prends ce rêve en main pour créer et transmettre. Je veux vous permettre de raconter votre histoire à travers la photo ou la vidéo.</p>\n')
        h.write('</div>')
        h.write('</section>\n')

        # Bottom contact bar (script will toggle visibility)
        h.write(f'<div class="bottom-bar"><span style="margin-right:8px">Mon Insta:</span><a href="https://instagram.com/leonard_rossel" target="_blank">@leonard_rossel</a><span style="margin:0 12px">·</span><span style="margin-right:8px">Mon mail:</span><a href="mailto:leonardrosselpro@gmail.com">leonardrosselpro@gmail.com</a></div>\n')
        h.write('<script>\n(function(){var bar=document.querySelector(\'.bottom-bar\');function check(){if(!bar) return; if((window.innerHeight+window.scrollY)>=document.documentElement.scrollHeight-2){bar.classList.add(\'visible\');}else{bar.classList.remove(\'visible\');}}window.addEventListener(\'scroll\',check,{passive:true});window.addEventListener(\'resize\',check);document.addEventListener(\'DOMContentLoaded\',check);check();})();\n</script>\n')
        # Video modal script (index) — open modal and play when play button clicked
        h.write('<script>\n(function(){var play=document.querySelector(\'.play-button\');var modal=document.getElementById(\'video-modal\');var vid=modal?modal.querySelector(\'#profile-video\'):null;var closeBtn=modal?modal.querySelector(\'.video-close\'):null;function openVideo(){if(!modal||!vid) return;modal.classList.add(\'open\');try{vid.currentTime=0;vid.play();}catch(e){}}function closeVideo(){if(!modal||!vid) return;try{vid.pause();}catch(e){}modal.classList.remove(\'open\');}if(play){play.addEventListener(\'click\',function(e){e.preventDefault();openVideo();});}if(closeBtn){closeBtn.addEventListener(\'click\',function(e){e.preventDefault();closeVideo();});}if(modal){modal.addEventListener(\'click\',function(e){if(e.target===modal){closeVideo();}});document.addEventListener(\'keydown\',function(e){if(e.key===\'Escape\') closeVideo();});} })();\n</script>\n')

        # Section 3 — Portfolio (grid of groups)
        h.write('<section class="section gallery-section">')
        h.write('<div class="section-label">Portfolio</div>\n')
        h.write('<div class="groups">')

        # order groups in a specific preferred order
        preferred_order = ['sport', 'portrait', 'paysage', 'voiture']
        all_keys = list(groups.keys())
        def _key(k):
            kl = k.lower()
            if kl in preferred_order:
                return (preferred_order.index(kl), '')
            return (len(preferred_order), kl)
        keys = sorted(all_keys, key=_key)

        for key in keys:
            imgs = groups[key]
            gslug = slug(key)
            # allow override with a dedicated miniature folder
            mini_found = None
            candidates = [
                os.path.join('images', f'miniature_{gslug}'),
                os.path.join('images', f'miniature {gslug}'),
                os.path.join('images', 'miniatures', gslug),
                os.path.join('images', f'miniature_{key}'),
                os.path.join('images', f'miniature {key}'),
            ]
            for md in candidates:
                md_full = Path(d) / md
                if md_full.is_dir():
                    files = [f for f in sorted(os.listdir(md_full)) if f.lower().endswith(valid_ext)]
                    if files:
                        mini_found = os.path.join(md, files[0]).replace('\\', '/')
                        break

            rep = imgs[0]
            # if a miniature override exists, prefer it as representative image
            if mini_found:
                rep = mini_found

            rep_thumb = ensure_thumb(rep)
            write_group_page(key, imgs)
            h.write('<div class="group animate-on-scroll">')
            h.write(f'<a href="gallery_{gslug}.html">')
            # group representative: prefer webp if present
            rep_src = (rep_thumb if rep_thumb and rep_thumb != rep else rep)
            if rep_thumb and rep_thumb != rep:
                rep_webp = os.path.splitext(rep_thumb)[0] + '.webp'
                if (Path(d) / rep_webp).exists():
                    h.write(f'<picture><source srcset="{rep_webp}" type="image/webp"><img src="{rep_thumb}" alt="{html.escape(key)}"></picture>')
                else:
                    h.write(f'<img src="{rep_thumb}" alt="{html.escape(key)}">')
            else:
                h.write(f'<img src="{rep_src}" alt="{html.escape(key)}">')
            h.write(f'<div>{html.escape(key)}</div>')
            h.write('</a></div>')

        h.write('</div>\n')
        # JS: intersection observer for animate-on-scroll and small parallax for top-hero
        h.write("<script>\n(function(){var io=new IntersectionObserver(function(entries){entries.forEach(function(e){if(e.isIntersecting){e.target.classList.add('visible');io.unobserve(e.target);}});},{threshold:0.12});document.querySelectorAll('.animate-on-scroll').forEach(function(el){io.observe(el)});var topHero=document.querySelector('.top-hero');if(topHero){var imgs=topHero.querySelectorAll(\"img\");window.addEventListener('scroll',function(){var rect=topHero.getBoundingClientRect();var h=window.innerHeight;var pct=1-Math.max(0,Math.min(1,(rect.top+h)/(h+rect.height)));imgs.forEach(function(img,i){var offset=(pct-0.5)*(i%2?6:-6);img.style.transform='translateY('+offset+'px)';});},{passive:true});} })();\n</script>\n")
        h.write('</body>\n</html>')

    print('Index written:', index_out)


def write_localstorage_seed(groups, outname='localstorage_seed.json', limit=24):
    """Génère un fichier JSON contenant une liste d'objets {dataUrl,title,desc}
    pour préremplir le localStorage via l'interface. Préfère les vignettes si présentes."""
    items = []
    # iterate groups in deterministic (alphabetical) order
    keys = sorted(groups.keys())

    for k in keys:
        for src in groups[k]:
            thumb = ensure_thumb(src)
            dataUrl = thumb if thumb and thumb != src else src
            items.append({'dataUrl': dataUrl, 'title': '', 'desc': ''})
            if len(items) >= limit:
                break
        if len(items) >= limit:
            break

    outpath = os.path.join(d, outname)
    try:
        with open(outpath, 'w', encoding='utf-8') as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        print(f'Wrote {len(items)} entries to {outpath}')
    except Exception as e:
        print('Failed to write seed:', e)


if __name__ == '__main__':
    groups = collect_groups()
    if not groups:
        print('No images found in', imgdir)
    else:
        write_index(groups)
        try:
            write_localstorage_seed(groups)
        except Exception as e:
            print('Could not write localstorage seed:', e)
        # create a project-local Backup folder and store a timestamped ZIP inside it
        try:
            def create_project_backup():
                backup_dir = os.path.join(d, 'Backup')
                os.makedirs(backup_dir, exist_ok=True)
                ts = datetime.datetime.now().strftime('%Y-%m-%d_%H%M%S')
                dest = os.path.join(backup_dir, f'MonSitePhotos_backup_{ts}.zip')
                # use zip to avoid including the backup file itself; exclude common unwanted folders
                cmd = [
                    'zip', '-r', dest, '.',
                    '-x', 'Backup/*', '*.DS_Store', '__pycache__/*', '.venv/*', 'venv/*', '*.zip'
                ]
                try:
                    subprocess.check_call(cmd, cwd=d)
                    print('Project backup created:', dest)
                except Exception as e:
                    # fallback to shutil.make_archive if zip is not available
                    try:
                        base = os.path.join(backup_dir, f'MonSitePhotos_backup_{ts}')
                        shutil.make_archive(base, 'zip', root_dir=d)
                        print('Project backup created (shutil):', base + '.zip')
                    except Exception as e2:
                        print('Failed to create project backup:', e, e2)

        except Exception:
            pass
        try:
            create_project_backup()
        except Exception:
            pass

