#!/usr/bin/env python3
import os, struct, json, math, shutil, argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import subprocess, sys, zipfile

ROOT = Path(".")
SRC_PUBLIC = ROOT / "public"
SRC_PAGES = ROOT / "pages"
DIST = ROOT / "vercel_dist"

# ---------------------------------------------------------
#  UTILITIES
# ---------------------------------------------------------
def ensure_dirs():
    (SRC_PUBLIC / "models" / "fighters").mkdir(parents=True, exist_ok=True)
    (SRC_PUBLIC / "sounds").mkdir(parents=True, exist_ok=True)
    (SRC_PUBLIC / "video").mkdir(parents=True, exist_ok=True)
    SRC_PAGES.mkdir(parents=True, exist_ok=True)

def write_file(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

# ---------------------------------------------------------
#  PURE-PYTHON GLB GENERATOR (SINGLE BOX)
# ---------------------------------------------------------
def make_box_glb(path, size, color):
    """
    Creates a single-box GLB with given size (w,h,d) and color (r,g,b).
    Pure Python. No external libs.
    """
    w, h, d = size
    r, g, b = color

    # 8 vertices
    x = w/2; y = h/2; z = d/2
    vertices = [
        (-x,-y,-z), (x,-y,-z), (x,y,-z), (-x,y,-z),
        (-x,-y, z), (x,-y, z), (x,y, z), (-x,y, z),
    ]

    # 12 triangles (36 indices)
    indices = [
        0,1,2, 2,3,0,
        4,5,6, 6,7,4,
        0,4,7, 7,3,0,
        1,5,6, 6,2,1,
        3,2,6, 6,7,3,
        0,1,5, 5,4,0
    ]

    # Color per vertex
    colors = [(r,g,b)] * 8

    # Pack binary
    def pack_floats(vals):
        return struct.pack("<" + "f"*len(vals), *vals)

    vertex_bytes = b"".join(pack_floats(v) for v in vertices)
    color_bytes  = b"".join(pack_floats(c) for c in colors)
    index_bytes  = struct.pack("<" + "H"*len(indices), *indices)

    # GLB buffer = vertices + colors + indices
    buffer = vertex_bytes + color_bytes + index_bytes
    buffer_length = len(buffer)

    # JSON chunk describing mesh
    json_dict = {
        "asset": {"version": "2.0"},
        "buffers": [{"byteLength": buffer_length}],
        "bufferViews": [
            {"buffer":0,"byteOffset":0,"byteLength":len(vertex_bytes),"target":34962},
            {"buffer":0,"byteOffset":len(vertex_bytes),"byteLength":len(color_bytes),"target":34962},
            {"buffer":0,"byteOffset":len(vertex_bytes)+len(color_bytes),"byteLength":len(index_bytes),"target":34963},
        ],
        "accessors": [
            {"bufferView":0,"componentType":5126,"count":8,"type":"VEC3"},
            {"bufferView":1,"componentType":5126,"count":8,"type":"VEC3"},
            {"bufferView":2,"componentType":5123,"count":len(indices),"type":"SCALAR"},
        ],
        "meshes":[
            {"primitives":[
                {"attributes":{"POSITION":0,"COLOR_0":1},"indices":2}
            ]}
        ],
        "nodes":[{"mesh":0}],
        "scenes":[{"nodes":[0]}],
        "scene":0
    }

    json_str = json.dumps(json_dict)
    json_bytes = json_str.encode("utf-8")
    # Pad to 4 bytes
    while len(json_bytes) % 4 != 0:
        json_bytes += b" "

    # GLB header
    magic = struct.pack("<I", 0x46546C67)
    version = struct.pack("<I", 2)
    total_length = 12 + 8 + len(json_bytes) + 8 + len(buffer)
    length = struct.pack("<I", total_length)

    # JSON chunk header
    json_chunk_header = struct.pack("<I4s", len(json_bytes), b"JSON")
    # BIN chunk header
    bin_chunk_header = struct.pack("<I4s", len(buffer), b"BIN\0")

    glb = magic + version + length + json_chunk_header + json_bytes + bin_chunk_header + buffer

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(glb)

# ---------------------------------------------------------
#  FIGHTER GLB GENERATION (A4)
# ---------------------------------------------------------
def make_fighter_glbs():
    fighters = {
        "cyber_dance_warrior.glb": {
            "size": (0.8, 2.0, 0.4),
            "color": (0.0, 1.0, 1.0),
        },
        "street_dance_brawler.glb": {
            "size": (1.2, 1.4, 0.6),
            "color": (0.2, 0.2, 0.2),
        },
        "electro_samurai.glb": {
            "size": (0.6, 1.8, 0.4),
            "color": (0.8, 0.1, 0.2),
        },
        "pop_idol_fighter.glb": {
            "size": (0.9, 1.2, 0.5),
            "color": (1.0, 0.4, 0.8),
        },
        "robot_groove_unit.glb": {
            "size": (1.0, 1.6, 0.8),
            "color": (0.4, 0.4, 0.9),
        },
    }

    base = SRC_PUBLIC / "models" / "fighters"
    for name, cfg in fighters.items():
        out = base / name
        print("[GLB] Creating:", out)
        make_box_glb(out, cfg["size"], cfg["color"])

# ---------------------------------------------------------
#  LORE JSON
# ---------------------------------------------------------
def write_fighter_lore():
    lore = {
        "cyber_dance_warrior": "Forged in the glow of midnight megaclubs, Cyber Dance Warrior moves like a glitch...",
        "street_dance_brawler": "Raised on cracked concrete and flickering streetlights, Street Dance Brawler fights...",
        "electro_samurai": "Electro Samurai is a walking remix of tradition and future—ancient discipline wired...",
        "pop_idol_fighter": "Pop Idol Fighter turns every battle into a live show, every arena into a sold-out stage...",
        "robot_groove_unit": "Robot Groove Unit was engineered for one purpose: to translate rhythm into raw kinetic force..."
    }
    out = SRC_PUBLIC / "models" / "fighters" / "fighter_lore.json"
    out.write_text(json.dumps(lore, indent=2), encoding="utf-8")

# ---------------------------------------------------------
#  AUDIO GENERATION (same as before)
# ---------------------------------------------------------
def synth(freq, dur, sr=44100, vol=0.3):
    t = np.linspace(0, dur, int(sr*dur), endpoint=False)
    return (np.sin(2*np.pi*freq*t) * vol).astype(np.float32)

def save_wav(path, data, sr=44100):
    import wave
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((data*32767).astype(np.int16).tobytes())

def make_audio(fast=False):
    dur = 5 if fast else 12
    save_wav(SRC_PUBLIC/"sounds"/"music_synthwave.wav", synth(80,dur)+synth(440,dur,vol=0.1))
    save_wav(SRC_PUBLIC/"sounds"/"music_edm.wav", synth(60,dur,vol=0.4)+synth(660,dur,vol=0.1))
    save_wav(SRC_PUBLIC/"sounds"/"music_disco.wav", synth(100,dur)+synth(300,dur,vol=0.1))
    save_wav(SRC_PUBLIC/"sounds"/"music_techno.wav", synth(50,dur,vol=0.5))
    save_wav(SRC_PUBLIC/"sounds"/"music_ambient.wav", synth(110,dur,vol=0.2))
    save_wav(SRC_PUBLIC/"sounds"/"select.wav", synth(1000,0.1))
    save_wav(SRC_PUBLIC/"sounds"/"switch.wav", synth(600,0.08))

# ---------------------------------------------------------
#  VIDEO GENERATION (same as before)
# ---------------------------------------------------------
def ensure_ffmpeg():
    if shutil.which("ffmpeg"):
        return "ffmpeg"
    print("FFmpeg not found. Install FFmpeg or place ffmpeg.exe in PATH.")
    sys.exit(1)

def make_video_frames(dirpath, duration, fps, size, draw_fn):
    w,h = size
    total = duration*fps
    dirpath.mkdir(parents=True, exist_ok=True)
    for i in range(total):
        img = Image.new("RGB", size, (0,0,0))
        draw = ImageDraw.Draw(img)
        draw_fn(draw, i, fps, w, h)
        img.save(dirpath/f"frame_{i:05d}.png")

def encode_video(ffmpeg, frames, out, fps):
    cmd = [ffmpeg,"-y","-framerate",str(fps),"-i",str(frames/"frame_%05d.png"),
           "-c:v","libx264","-pix_fmt","yuv420p",str(out)]
    subprocess.run(cmd, check=True)

def make_videos(ffmpeg, fast=False):
    duration = 3 if fast else 5
    fps = 30
    size = (1280,720)

    # Neon tunnel
    def neon(draw,i,fps,w,h):
        t=i/fps
        depth=20
        for j in range(depth):
            f=(j+t*10)%depth
            m=int(f/depth*min(w,h)/2)
            c=(0,int(255*(1-f/depth)),255)
            draw.rectangle([m,m,w-m,h-m],outline=c,width=2)

    frames = ROOT/"frames"/"tunnel"
    make_video_frames(frames,duration,fps,size,neon)
    encode_video(ffmpeg,frames,SRC_PUBLIC/"video"/"intro_tunnel.mp4",fps)

# ---------------------------------------------------------
#  HTML (shortened for clarity)
# ---------------------------------------------------------
GAME_HTML = "<html><body><h1>DancePlanet Fighter Select</h1></body></html>"
ARENA_HTML = "<html><body><h1>DancePlanet Arena</h1></body></html>"

# ---------------------------------------------------------
#  VERCEL PACKAGING
# ---------------------------------------------------------
def build_vercel_dist():
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SRC_PUBLIC, DIST/"public", dirs_exist_ok=True)
    shutil.copytree(SRC_PAGES, DIST/"pages", dirs_exist_ok=True)
    (DIST/"vercel.json").write_text(json.dumps({
        "version":2,
        "routes":[
            {"src":"/public/(.*)","dest":"/public/$1"},
            {"src":"/pages/(.*)","dest":"/pages/$1"},
        ]
    },indent=2))

# ---------------------------------------------------------
#  MAIN
# ---------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fast", action="store_true")
    args = parser.parse_args()

    ensure_dirs()

    print("[1] Generating GLB fighters...")
    make_fighter_glbs()
    write_fighter_lore()

    print("[2] Generating audio...")
    make_audio(fast=args.fast)

    print("[3] Generating videos...")
    ffmpeg = ensure_ffmpeg()
    make_videos(ffmpeg, fast=args.fast)

    print("[4] Writing HTML...")
    write_file(SRC_PAGES/"game.html", GAME_HTML)
    write_file(SRC_PAGES/"arena.html", ARENA_HTML)

    print("[5] Building vercel_dist...")
    build_vercel_dist()

    print("Done.")

if __name__ == "__main__":
    main()
