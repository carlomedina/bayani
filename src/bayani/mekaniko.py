from pathlib import Path
import math
from PIL import Image, ImageFilter
import os
import subprocess
import shutil
import logging

log = logging.getLogger("mekaniko")

# CRUNCHING
def crunch_images_in_path(path):
    # check if crunch is available
    if not shutil.which("crunch"):
        log.warning("Crunch not found. Skipping crunching")
        return None
    log.info("Crunch found. Crunching pngs")
    pngs = get_pngs_in_path(path)

    cmd = ["crunch"] + pngs

    cp = subprocess.run(
        cmd, universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

    if cp.returncode == 0:
        log.info("Crunch successful")
        log.info(str(cp.stdout))
    else:
        log.error("Something went wrong with crunch")
    return None


def get_pngs_in_path(path):
    pngs = []
    for path in Path(path).rglob("*.png"):
        pngs.append(str(path))
    return pngs


def delete_processed_pngs(path, patterns=[]):
    pngs = get_pngs_in_path(path)
    crunched_pngs = [png for png in pngs if any(pattern in png for pattern in patterns)]
    for crunched_png in crunched_pngs:
        os.remove(crunched_png)
        log.info(f"Deleted { crunched_png }")
    return None


def resize_image(input):
    # file_name = input_path
    file_name = os.path.basename(input)
    path = os.path.dirname(input)
    name_no_ext, ext = os.path.splitext(file_name)
    output = name_no_ext + "-resized"

    img = Image.open(input)
    width, height = img.size
    max_width = 380
    if width > max_width:
        ratio = height / width
        newheight = math.floor(ratio * max_width)
        img = img.resize((max_width, newheight), Image.BICUBIC)
        # .filter(ImageFilter.SHARPEN)
    formats = {".jpg": "JPEG", ".png": "PNG", ".jpeg": "JPEG"}

    output = f"{ path }/{ output }{ext}"
    img.save(output, format=formats[ext])
    log.info(f"Resized { input } => { output }")
    return None


def resize_images_in_path(path):
    pngs = get_pngs_in_path(path)
    for png in pngs:
        resize_image(png)
    return None
