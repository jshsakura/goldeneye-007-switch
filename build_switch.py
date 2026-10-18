#!/usr/bin/env python3
"""
GoldenEye 007 Nintendo Switch Port - All-in-One Automated Builder
Includes automatic Korean patch application (BPS), asset conversion,
and Switch homebrew (.nro) compilation.

Credits:
  - Original Game: Rare / Nintendo (1997)
  - GoldenEye Decompilation: n64decomp / ge007 team
  - PC Port: jkdansereau and contributors
  - N64 Korean Fan Translation (v1.0): retrace (RetroDB)
  - Nintendo Switch Native Port & Gyro Aiming: jshsakura & Antigravity
"""

import os
import sys
import shutil
import hashlib
import argparse
import subprocess
import zipfile

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STOCK_JP_SHA1 = "2a5dade32f7fad6c73c659d2026994632c1b3174"
KOREAN_JP_SHA1 = "bf2062a64738fbf36ee91da72211d0d180e01c01"
DEFAULT_BPS_PATH = os.path.join(SCRIPT_DIR, "patches", "ge007_korean.bps")

DEFAULT_INI = """# GoldenEye 007 Switch Configuration
[Audio]
BufferSize = 512
QueueLimit = 2880
MasterVolume = 100
Device = 

[Debug]
InputLog = 0
FrameDump = 

[Input]
PadPreset = 0
PadPreset2 = 0
PadPreset3 = 0
PadPreset4 = 0
MPMode = 0
MouseEnabled = 0
CrosshairCursor = 1
AimAbsolute = 1
NaturalPitch = 1
ControlScheme = 0
PadDeadzone = 7500
PadLookSensX = 100
PadLookSensY = 100
PadLookInvertY = 0
CrouchMode = 1
RumbleScale = 0.5
Gyro = 1
GyroSensitivity = 100
GyroInvertY = 0

[Video]
DisplayFPS = 0
CrosshairHide = 0
CrosshairPersistent = 0
CrosshairColor = 0
CrosshairRed = 255
CrosshairGreen = 255
CrosshairBlue = 255
CrosshairSize = 100
CrosshairStyle = 0
CrosshairAlpha = 100
CrosshairHealthColor = 0
VSync = 1
FpsCap = 60
MSAA = 1
TextureFilter = 1
FixMipTextures = 1
DetailBaseTile = 1
WrapFix = 0
WidescreenAuto = 1
NativeWidescreen = 1
DrawDistance = 100
FogDistance = 100
LodDistance = 100
Anisotropy = 4
SafeAreaCrop = 1
AspectMode = 0
Fullscreen = 0
FovScale = 100
"""

def log(msg, prefix="[*]"):
    print(f"{prefix} {msg}")

def error_exit(msg):
    print(f"\n[!] ERROR: {msg}", file=sys.stderr)
    sys.exit(1)

def sha1_file(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def apply_bps(src_bytes, patch_bytes):
    """Pure-Python BPS patch applicator (beat / flips standard)."""
    if patch_bytes[:4] != b'BPS1':
        raise ValueError("Invalid BPS patch header")
    p = 4
    def read_varint():
        nonlocal p
        res = 0
        shift = 0
        while True:
            b = patch_bytes[p]
            p += 1
            res += (b & 0x7F) << shift
            if b & 0x80:
                break
            shift += 7
            res += 1 << shift
        return res

    src_len = read_varint()
    dst_len = read_varint()
    meta_len = read_varint()
    meta = patch_bytes[p:p + meta_len]
    p += meta_len

    dst = bytearray(dst_len)
    dst_off = 0
    src_rel = 0
    dst_rel = 0

    while p < len(patch_bytes) - 12:
        val = read_varint()
        cmd = val & 3
        length = (val >> 2) + 1
        if cmd == 0:  # SourceRead
            dst[dst_off:dst_off + length] = src_bytes[dst_off:dst_off + length]
            dst_off += length
        elif cmd == 1:  # TargetRead
            dst[dst_off:dst_off + length] = patch_bytes[p:p + length]
            p += length
            dst_off += length
        elif cmd == 2:  # SourceCopy
            offset_val = read_varint()
            src_rel += -(offset_val >> 1) if (offset_val & 1) else (offset_val >> 1)
            dst[dst_off:dst_off + length] = src_bytes[src_rel:src_rel + length]
            src_rel += length
            dst_off += length
        elif cmd == 3:  # TargetCopy
            offset_val = read_varint()
            dst_rel += -(offset_val >> 1) if (offset_val & 1) else (offset_val >> 1)
            for _ in range(length):
                dst[dst_off] = dst[dst_rel]
                dst_off += 1
                dst_rel += 1
    return bytes(dst)

def resolve_rom(user_rom_path):
    candidates = []
    if user_rom_path:
        candidates.append(user_rom_path)
    candidates.extend([
        os.path.join(SCRIPT_DIR, "baserom.j.z64"),
        os.path.join(SCRIPT_DIR, "data", "ge007.jpn-final.z64"),
        os.path.join(SCRIPT_DIR, "ge007.j.z64"),
        os.path.join(SCRIPT_DIR, "GoldenEye 007 (Japan).z64"),
        os.path.join(SCRIPT_DIR, "ge007.korean.j.z64"),
    ])

    found = None
    for c in candidates:
        if c and os.path.exists(c):
            found = c
            break

    if not found:
        error_exit(
            "ROM not found! Please place 'baserom.j.z64' (Japanese N64 ROM) in the root directory "
            "or specify via --rom <path>."
        )

    log(f"Found ROM: {found}")
    h = sha1_file(found)
    log(f"ROM SHA-1: {h}")

    os.makedirs(os.path.join(SCRIPT_DIR, "data"), exist_ok=True)
    target_rom_path = os.path.join(SCRIPT_DIR, "data", "ge007.jpn-final.z64")
    root_base_path = os.path.join(SCRIPT_DIR, "baserom.j.z64")

    if h == KOREAN_JP_SHA1:
        log("ROM is already patched with Korean translation.")
        if found != target_rom_path:
            shutil.copyfile(found, target_rom_path)
        if found != root_base_path:
            shutil.copyfile(found, root_base_path)
        return target_rom_path

    elif h == STOCK_JP_SHA1:
        log("Stock Japanese GoldenEye 007 ROM detected. Applying Korean translation patch...")
        if not os.path.exists(DEFAULT_BPS_PATH):
            error_exit(f"Korean BPS patch not found at {DEFAULT_BPS_PATH}")
        with open(found, "rb") as f_src, open(DEFAULT_BPS_PATH, "rb") as f_bps:
            src_bytes = f_src.read()
            bps_bytes = f_bps.read()
        patched_bytes = apply_bps(src_bytes, bps_bytes)
        patched_sha1 = hashlib.sha1(patched_bytes).hexdigest()
        if patched_sha1 != KOREAN_JP_SHA1:
            log(f"Warning: patched SHA-1 ({patched_sha1}) differs from expected ({KOREAN_JP_SHA1})", prefix="[!]")
        with open(target_rom_path, "wb") as f_out:
            f_out.write(patched_bytes)
        with open(root_base_path, "wb") as f_out:
            f_out.write(patched_bytes)
        log("Korean patch applied successfully!")
        return target_rom_path

    else:
        log("Warning: Unrecognized ROM SHA-1. Proceeding anyway...", prefix="[!]")
        shutil.copyfile(found, target_rom_path)
        shutil.copyfile(found, root_base_path)
        return target_rom_path

def generate_sidecars():
    log("Generating ROM-derived sidecars (pcmodels and pccg)...")
    cwd = SCRIPT_DIR
    cmds = [
        [sys.executable, "tools_pc/d43_emit.py", "jpn-final"],
        [sys.executable, "tools_pc/d69_emit.py", "jpn-final"],
        [sys.executable, "tools_pc/d88_emit.py", "jpn-final"],
    ]
    for cmd in cmds:
        res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
        if res.returncode != 0:
            error_exit(f"Sidecar generation failed: {' '.join(cmd)}\n{res.stderr}")
    log("Sidecars generated successfully.")

def build_switch_nro(use_docker=True, jobs=None):
    if jobs is None:
        jobs = os.cpu_count() or 4

    icon_path = os.path.join(SCRIPT_DIR, "docs", "img", "icon", "ge007-user-icon.png")
    if not os.path.exists(icon_path):
        icon_path = os.path.join(SCRIPT_DIR, "docs", "img", "icon", "ge007.png")

    log("Compiling Switch native binary (ge007.nro)...")
    if use_docker:
        docker_cmd = shutil.which("docker")
        if not docker_cmd:
            error_exit("Docker command not found! Install Docker or pass --no-docker.")
        
        script = f"""
set -e
cmake -B /src/build-switch -S /src -DCMAKE_TOOLCHAIN_FILE=/opt/devkitpro/cmake/Switch.cmake -DASSET_REGION=j -DCMAKE_BUILD_TYPE=Release
make -C /src/build-switch -j{jobs}
elf2nro /src/build-switch/ge007.jpn.aarch64.elf /src/build-switch/ge007.nro --icon=/src/{os.path.relpath(icon_path, SCRIPT_DIR)} --nacp=/src/build-switch/ge007.nacp
"""
        cmd = [
            "docker", "run", "--rm",
            "-v", f"{SCRIPT_DIR}:/src",
            "devkitpro/devkita64",
            "bash", "-c", script
        ]
        res = subprocess.run(cmd)
        if res.returncode != 0:
            error_exit("Docker compilation failed!")
    else:
        # Local devkitA64
        env = os.environ.copy()
        devkitpro = env.get("DEVKITPRO", "/opt/devkitpro")
        toolchain = os.path.join(devkitpro, "cmake", "Switch.cmake")
        if not os.path.exists(toolchain):
            error_exit(f"Switch CMake toolchain not found at {toolchain}")

        res = subprocess.run([
            "cmake", "-B", "build-switch", "-S", ".",
            f"-DCMAKE_TOOLCHAIN_FILE={toolchain}",
            "-DASSET_REGION=j", "-DCMAKE_BUILD_TYPE=Release"
        ], cwd=SCRIPT_DIR)
        if res.returncode != 0:
            error_exit("CMake configuration failed!")

        res = subprocess.run(["make", "-C", "build-switch", f"-j{jobs}"], cwd=SCRIPT_DIR)
        if res.returncode != 0:
            error_exit("Make build failed!")

        elf2nro = os.path.join(devkitpro, "tools", "bin", "elf2nro")
        res = subprocess.run([
            elf2nro,
            "build-switch/ge007.jpn.aarch64.elf",
            "build-switch/ge007.nro",
            f"--icon={icon_path}",
            "--nacp=build-switch/ge007.nacp"
        ], cwd=SCRIPT_DIR)
        if res.returncode != 0:
            error_exit("elf2nro packaging failed!")

    nro_path = os.path.join(SCRIPT_DIR, "build-switch", "ge007.nro")
    if not os.path.exists(nro_path):
        error_exit("ge007.nro was not produced!")
    log(f"Successfully compiled ge007.nro ({os.path.getsize(nro_path)} bytes)")

def package_dist(make_zip=False):
    log("Assembling distribution bundle...")
    dist_dir = os.path.join(SCRIPT_DIR, "dist", "switch", "ge007")
    dist_data = os.path.join(dist_dir, "data")
    if os.path.exists(dist_dir):
        shutil.rmtree(dist_dir)
    os.makedirs(dist_data, exist_ok=True)

    # 1. Copy NRO
    shutil.copyfile(os.path.join(SCRIPT_DIR, "build-switch", "ge007.nro"), os.path.join(dist_dir, "ge007.nro"))

    # 2. Copy ROM
    rom_src = os.path.join(SCRIPT_DIR, "data", "ge007.jpn-final.z64")
    shutil.copyfile(rom_src, os.path.join(dist_data, "ge007.jpn-final.z64"))

    # 3. Copy Sidecars
    shutil.copytree(os.path.join(SCRIPT_DIR, "data", "pccg-jpn-final"), os.path.join(dist_data, "pccg-jpn-final"))
    shutil.copytree(os.path.join(SCRIPT_DIR, "data", "pcmodels-jpn-final"), os.path.join(dist_data, "pcmodels-jpn-final"))

    # 4. Write default ge007.ini
    ini_path = os.path.join(dist_data, "ge007.ini")
    with open(ini_path, "w") as f:
        f.write(DEFAULT_INI)

    log(f"Bundle successfully created at: {dist_dir}")

    if make_zip:
        zip_path = os.path.join(SCRIPT_DIR, "dist", "ge007-switch-korean.zip")
        log(f"Creating ZIP archive: {zip_path}")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(dist_dir):
                for f in files:
                    full = os.path.join(root, f)
                    rel = os.path.relpath(full, os.path.join(SCRIPT_DIR, "dist", "switch"))
                    zf.write(full, rel)
        log(f"ZIP archive created: {zip_path}")

def print_credits():
    print("""
========================================================================
                      골든아이 007 스위치 포트 완성!
========================================================================
[설치 방법]
  1. SD 카드를 PC에 연결합니다.
  2. dist/switch/ge007/ 폴더를 SD 카드의 /switch/ 폴더로 복사합니다.
     -> 최종 경로: sdmc:/switch/ge007/ge007.nro
  3. 홈브루 메뉴(HBL)에서 '007 GoldenEye'를 실행합니다.

[주요 기능]
  - 100% 한국어 자막 완벽 지원 (한글 글자 뭉개짐/중복 버그 해결)
  - 젤다의 전설 / 스플래툰 스타일 1:1 카메라 자이로 조준 내장
  - 커스텀 고화질 홈브루 아이콘 적용

[크레딧 & 출처]
  - 원작 게임: Rare / Nintendo (1997)
  - N64 디컴파일: n64decomp / ge007 팀
  - PC 포트: jkdansereau 및 기여자 일동
  - N64 한국어 패치 (v1.0): retrace 님 (RetroDB)
  - 닌텐도 스위치 네이티브 포팅 & 자이로 조준: jshsakura
========================================================================
""")

def main():
    parser = argparse.ArgumentParser(description="GoldenEye 007 Switch Port Automated Builder")
    parser.add_argument("--rom", help="Path to Japanese GoldenEye 007 ROM (.z64)")
    parser.add_argument("--no-docker", action="store_true", help="Use local devkitA64 instead of Docker")
    parser.add_argument("--zip", action="store_true", help="Create a distribution ZIP archive")
    parser.add_argument("-j", "--jobs", type=int, help="Number of parallel compilation jobs")
    parser.add_argument("--skip-build", action="store_true", help="Skip compilation (packaging only)")
    args = parser.parse_args()

    resolve_rom(args.rom)
    generate_sidecars()
    if not args.skip_build:
        build_switch_nro(use_docker=not args.no_docker, jobs=args.jobs)
    package_dist(make_zip=args.zip)
    print_credits()

if __name__ == "__main__":
    main()
