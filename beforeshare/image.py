"""Image scanning and cleaning with Pillow (EXIF, GPS, embedded metadata)."""
from PIL import Image, ExifTags
from .models import Finding, Severity

C = "image"
_GPS_IFD = 0x8825


def _exif(img):
    try:
        return img.getexif()
    except Exception:
        return {}


def scan(path):
    out = []
    with Image.open(path) as img:
        ex = _exif(img)
        gps = {}
        try:
            gps = dict(ex.get_ifd(_GPS_IFD))
        except Exception:
            pass
        if gps:
            out.append(Finding("image.gps", Severity.HIGH, "GPS location is stored in this image"))
        tags = {ExifTags.TAGS.get(k, k): v for k, v in ex.items()}
        try:
            exif_ifd = ex.get_ifd(0x8769)
        except Exception:
            exif_ifd = {}
        if tags.get("DateTime") or exif_ifd.get(0x9003):
            out.append(Finding("image.datetime", Severity.MEDIUM, "Capture date and time"))
        device = [str(tags[k]).strip() for k in ("Make", "Model") if tags.get(k)]
        if device:
            out.append(Finding("image.device", Severity.MEDIUM, f"Camera or phone model ({' '.join(device)})"))
        for k in ("Artist", "Copyright", "Software", "HostComputer", "ImageDescription", "XPAuthor", "XPComment"):
            if tags.get(k):
                out.append(Finding("image.owner_info", Severity.MEDIUM, f"Embedded {k}: {str(tags[k])[:60]}"))
        extra = [k for k in img.info if k in ("xmp", "XML:com.adobe.xmp", "icc_profile", "comment", "photoshop")
                 or str(k).lower() in ("author", "description", "software", "comment")]
        if extra and not any(f.code.startswith("image.") and f.code != "image.other" for f in out):
            out.append(Finding("image.other", Severity.LOW, f"Embedded metadata blocks: {', '.join(map(str, extra))}"))
        elif extra:
            out.append(Finding("image.other", Severity.LOW, f"Other embedded metadata blocks: {', '.join(map(str, extra))}"))
    # collapse duplicate owner_info codes into one finding each (keep messages)
    return out


def clean(src, dst, codes):
    """Rebuild the image from its pixels so no metadata is carried over.

    Metadata in an image is removed all together (partial removal is not offered).
    JPEG is saved again at quality 95, which is lossy.
    """
    with Image.open(src) as img:
        fmt = img.format or "PNG"
        img.load()
        clean_img = Image.frombytes(img.mode, img.size, img.tobytes())
        if img.mode == "P" and img.getpalette():
            clean_img.putpalette(img.getpalette())
        kwargs = {}
        if fmt == "JPEG":
            kwargs = {"quality": 95, "subsampling": 0}
        clean_img.save(dst, format=fmt, **kwargs)
