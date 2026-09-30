"""
QR Code Engine - Local image loading, enhancement, and webcam frame decoder.
"""
from typing import Tuple, List, Any
import numpy as np
from PIL import Image

try:
    from pyzbar import pyzbar
    PYZBAR_AVAILABLE = True
except Exception:
    PYZBAR_AVAILABLE = False

try:
    import cv2
    CV2_AVAILABLE = True
except Exception:
    CV2_AVAILABLE = False

import os
import hashlib
import math
from collections import Counter

def compute_shannon_entropy(data: str) -> float:
    """Computes Shannon entropy in bits per character/symbol."""
    if not data:
        return 0.0
    counts = Counter(data)
    length = len(data)
    return round(-sum((c / length) * math.log2(c / length) for c in counts.values()), 2)


def extract_optical_metadata(file_path: str) -> dict:
    """Extracts physical and cryptographic metadata from an image file."""
    if not file_path or not os.path.exists(file_path):
        return {
            "file_name": os.path.basename(file_path) if file_path else "Live Stream / Frame",
            "file_path": file_path or "In-Memory Buffer",
            "file_size": "In-Memory",
            "file_size_bytes": 0,
            "sha256": "N/A",
            "dimensions": "Unknown",
            "width": 0,
            "height": 0,
            "format": "RAW",
            "mode": "RGB",
            "aspect_ratio": "1:1",
        }

    size_bytes = os.path.getsize(file_path)
    if size_bytes < 1024:
        size_str = f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        size_str = f"{round(size_bytes / 1024, 1)} KB"
    else:
        size_str = f"{round(size_bytes / (1024 * 1024), 2)} MB"

    try:
        with open(file_path, "rb") as f:
            sha256 = hashlib.sha256(f.read()).hexdigest()
    except Exception:
        sha256 = "Unavailable"

    width, height, fmt, mode = 0, 0, "UNKNOWN", "UNKNOWN"
    aspect_ratio = "1:1"
    try:
        with Image.open(file_path) as img:
            width, height = img.size
            fmt = img.format or "RAW"
            mode = img.mode or "RGB"
            if height > 0:
                if width == height:
                    aspect_ratio = "1:1 (Square Matrix)"
                else:
                    aspect_ratio = f"{round(width / height, 2)}:1"
    except Exception:
        pass

    return {
        "file_name": os.path.basename(file_path),
        "file_path": file_path,
        "file_size": size_str,
        "file_size_bytes": size_bytes,
        "sha256": sha256,
        "dimensions": f"{width} x {height} px",
        "width": width,
        "height": height,
        "format": fmt,
        "mode": mode,
        "aspect_ratio": aspect_ratio,
    }


def decode_from_file_with_metadata(file_path: str) -> dict:
    """
    Decodes a QR code from a local image file and tracks which engine/pipeline succeeded,
    along with complete optical metadata.
    """
    opt_meta = extract_optical_metadata(file_path)
    res = {
        "success": False,
        "payload": "",
        "error": "",
        "engine": "Unknown Decoder",
        "optical_meta": opt_meta,
    }

    # Step 1: Attempt decode using Pillow & pyzbar
    if PYZBAR_AVAILABLE:
        try:
            with Image.open(file_path) as img:
                decoded_objects = pyzbar.decode(img)
                for obj in decoded_objects:
                    data = obj.data.decode("utf-8", errors="replace").strip()
                    if data:
                        res["success"] = True
                        res["payload"] = data
                        res["engine"] = "PyZBar zbar-0.10 (Direct Matrix)"
                        return res
        except Exception:
            pass  # Fall through to OpenCV fallback

    # Step 2 & 3: Fallback using OpenCV and preprocessing pipeline
    if not CV2_AVAILABLE:
        res["error"] = "Neither pyzbar nor OpenCV is available for QR decoding."
        return res

    try:
        # Load image via cv2.imdecode to safely handle Unicode paths on Windows
        with open(file_path, "rb") as f:
            file_bytes = np.frombuffer(f.read(), dtype=np.uint8)
            cv_img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

        if cv_img is None:
            res["error"] = f"Failed to load image file: {file_path}"
            return res

        detector = cv2.QRCodeDetector()

        # Try direct detection first
        payload, points, _ = detector.detectAndDecode(cv_img)
        if payload and payload.strip():
            res["success"] = True
            res["payload"] = payload.strip()
            res["engine"] = "OpenCV QRCodeDetector (Standard Direct)"
            return res

        # Preprocessing Fallback 1: Grayscale
        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
        payload, points, _ = detector.detectAndDecode(gray)
        if payload and payload.strip():
            res["success"] = True
            res["payload"] = payload.strip()
            res["engine"] = "OpenCV QRCodeDetector (Grayscale Preprocessed)"
            return res

        # Preprocessing Fallback 2: CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        clahe_img = clahe.apply(gray)
        payload, points, _ = detector.detectAndDecode(clahe_img)
        if payload and payload.strip():
            res["success"] = True
            res["payload"] = payload.strip()
            res["engine"] = "OpenCV QRCodeDetector (CLAHE Enhanced Pipeline)"
            return res

        # Preprocessing Fallback 3: Adaptive Thresholding
        adaptive_thresh = cv2.adaptiveThreshold(
            clahe_img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 51, 5
        )
        payload, points, _ = detector.detectAndDecode(adaptive_thresh)
        if payload and payload.strip():
            res["success"] = True
            res["payload"] = payload.strip()
            res["engine"] = "OpenCV QRCodeDetector (Adaptive Threshold)"
            return res

        # Also try pyzbar on enhanced versions if pyzbar is available
        if PYZBAR_AVAILABLE:
            _, otsu_thresh = cv2.threshold(clahe_img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            inverted_gray = cv2.bitwise_not(gray)
            for enhanced, name in [
                (gray, "PyZBar (Grayscale Preprocessed)"),
                (clahe_img, "PyZBar (CLAHE Equalized)"),
                (adaptive_thresh, "PyZBar (Adaptive Thresholded)"),
                (otsu_thresh, "PyZBar (Otsu Thresholded)"),
                (inverted_gray, "PyZBar (Inverted / Dark Mode)"),
            ]:
                try:
                    enhanced_pil = Image.fromarray(enhanced)
                    objs = pyzbar.decode(enhanced_pil)
                    for obj in objs:
                        data = obj.data.decode("utf-8", errors="replace").strip()
                        if data:
                            res["success"] = True
                            res["payload"] = data
                            res["engine"] = name
                            return res
                except Exception:
                    pass

        res["error"] = "No QR code detected in image even after multi-pass enhancement."
        return res
    except Exception as e:
        res["error"] = f"Error decoding image: {str(e)}"
        return res


def decode_from_file(file_path: str) -> Tuple[bool, str, str]:
    """
    Decodes a QR code from a local image file.
    Backwards-compatible wrapper around decode_from_file_with_metadata.
    """
    res = decode_from_file_with_metadata(file_path)
    return res["success"], res["payload"], res["error"]


# Cached singletons for high-performance zero-allocation frame analysis
_CV_QR_DETECTOR = cv2.QRCodeDetector() if CV2_AVAILABLE else None
_CLAHE_FILTER = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8)) if CV2_AVAILABLE else None
_SHARPEN_KERNEL = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]], dtype=np.float32) if (CV2_AVAILABLE and np is not None) else None


def scan_webcam_frame(
    frame: Any,
    boost_contrast: bool = False,
    return_meta: bool = False,
) -> Any:
    """
    Takes an OpenCV video capture frame, searches for QR codes in real-time,
    extracts points, and returns payload text if present.
    
    Optimized High-Performance Pipeline:
      - Pass 1: Direct PyZBar decode on raw frame (Fastest, ~2-4ms)
      - Pass 2: Cached OpenCV QRCodeDetector direct pass
      - Pass 3: Grayscale conversion with PyZBar (Robust & Fast, ~3ms)
      - Pass 4: CLAHE & Edge Sharpening (Executed when boost_contrast=True for screen glare / low light)
      
    Returns:
        If return_meta is False:
            (success: bool, raw_payload: str, points: list)
        If return_meta is True:
            (success: bool, raw_payload: str, points: list, engine_name: str)
    """
    if frame is None or not CV2_AVAILABLE:
        return (False, "", [], "Sensor Unavailable") if return_meta else (False, "", [])

    def _normalize_cv_pts(points_arr) -> List[Tuple[int, int]]:
        try:
            if points_arr is None or len(points_arr) == 0:
                return []
            pts = points_arr[0] if getattr(points_arr, "ndim", 2) == 3 else points_arr
            return [(int(round(float(pt[0]))), int(round(float(pt[1])))) for pt in pts]
        except Exception:
            return []

    global _CV_QR_DETECTOR, _CLAHE_FILTER, _SHARPEN_KERNEL
    detector = _CV_QR_DETECTOR if _CV_QR_DETECTOR is not None else cv2.QRCodeDetector()

    # Pass 1: Direct PyZbar decode on raw frame
    if PYZBAR_AVAILABLE:
        try:
            objs = pyzbar.decode(frame)
            for obj in objs:
                data = obj.data.decode("utf-8", errors="replace").strip()
                if data:
                    polygon = [(int(p.x), int(p.y)) for p in obj.polygon] if obj.polygon else []
                    engine = "PyZBar Real-Time Sensor"
                    return (True, data, polygon, engine) if return_meta else (True, data, polygon)
        except Exception:
            pass

    # Pass 2: Quick OpenCV detector direct
    try:
        payload, points, _ = detector.detectAndDecode(frame)
        if payload and payload.strip():
            pts = _normalize_cv_pts(points)
            engine = "OpenCV Real-Time Sensor"
            return (True, payload.strip(), pts, engine) if return_meta else (True, payload.strip(), pts)
    except Exception:
        pass

    # Quick Grayscale PyZbar pass (fast fallback even when boost is off)
    try:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if PYZBAR_AVAILABLE:
            objs = pyzbar.decode(gray)
            for obj in objs:
                data = obj.data.decode("utf-8", errors="replace").strip()
                if data:
                    polygon = [(int(p.x), int(p.y)) for p in obj.polygon] if obj.polygon else []
                    engine = "PyZBar (Grayscale Standard)"
                    return (True, data, polygon, engine) if return_meta else (True, data, polygon)
    except Exception:
        gray = None

    # Pass 3: Tactical Boost Passes (Executed when boost_contrast is True)
    if boost_contrast and gray is not None:
        try:
            clahe = _CLAHE_FILTER if _CLAHE_FILTER is not None else cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            clahe_img = clahe.apply(gray)

            # Pass 3A: CLAHE Contrast Boost
            if PYZBAR_AVAILABLE:
                try:
                    objs = pyzbar.decode(clahe_img)
                    for obj in objs:
                        data = obj.data.decode("utf-8", errors="replace").strip()
                        if data:
                            polygon = [(int(p.x), int(p.y)) for p in obj.polygon] if obj.polygon else []
                            engine = "PyZBar (CLAHE Contrast Boost)"
                            return (True, data, polygon, engine) if return_meta else (True, data, polygon)
                except Exception:
                    pass

            payload, points, _ = detector.detectAndDecode(clahe_img)
            if payload and payload.strip():
                pts = _normalize_cv_pts(points)
                engine = "OpenCV (CLAHE Contrast Boost)"
                return (True, payload.strip(), pts, engine) if return_meta else (True, payload.strip(), pts)

            # Pass 3B: Adaptive Thresholding (Crucial for screen glare and washed out modules)
            adaptive = cv2.adaptiveThreshold(
                clahe_img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 41, 6
            )
            if PYZBAR_AVAILABLE:
                try:
                    objs = pyzbar.decode(adaptive)
                    for obj in objs:
                        data = obj.data.decode("utf-8", errors="replace").strip()
                        if data:
                            polygon = [(int(p.x), int(p.y)) for p in obj.polygon] if obj.polygon else []
                            engine = "PyZBar (Adaptive Threshold Boost)"
                            return (True, data, polygon, engine) if return_meta else (True, data, polygon)
                except Exception:
                    pass

            payload, points, _ = detector.detectAndDecode(adaptive)
            if payload and payload.strip():
                pts = _normalize_cv_pts(points)
                engine = "OpenCV (Adaptive Threshold Boost)"
                return (True, payload.strip(), pts, engine) if return_meta else (True, payload.strip(), pts)

            # Pass 3C: Otsu Bimodal Thresholding (Isolates QR grid against glowing LCD backlight)
            _, otsu = cv2.threshold(clahe_img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            if PYZBAR_AVAILABLE:
                try:
                    objs = pyzbar.decode(otsu)
                    for obj in objs:
                        data = obj.data.decode("utf-8", errors="replace").strip()
                        if data:
                            polygon = [(int(p.x), int(p.y)) for p in obj.polygon] if obj.polygon else []
                            engine = "PyZBar (Otsu Threshold Boost)"
                            return (True, data, polygon, engine) if return_meta else (True, data, polygon)
                except Exception:
                    pass

            # Pass 3D: Dark-Mode Inversion (White QR modules on dark background / inverted screens)
            inv_gray = cv2.bitwise_not(gray)
            if PYZBAR_AVAILABLE:
                try:
                    objs = pyzbar.decode(inv_gray)
                    for obj in objs:
                        data = obj.data.decode("utf-8", errors="replace").strip()
                        if data:
                            polygon = [(int(p.x), int(p.y)) for p in obj.polygon] if obj.polygon else []
                            engine = "PyZBar (Inverted Dark Mode Boost)"
                            return (True, data, polygon, engine) if return_meta else (True, data, polygon)
                except Exception:
                    pass

            # Pass 3E: Anti-Glare Gamma Correction (Cuts severe phone screen backlight flare)
            lut_glare = np.array([int(((i / 255.0) ** 1.6) * 255) for i in range(256)], dtype=np.uint8)
            glare_reduced = cv2.LUT(gray, lut_glare)
            if PYZBAR_AVAILABLE:
                try:
                    objs = pyzbar.decode(glare_reduced)
                    for obj in objs:
                        data = obj.data.decode("utf-8", errors="replace").strip()
                        if data:
                            polygon = [(int(p.x), int(p.y)) for p in obj.polygon] if obj.polygon else []
                            engine = "PyZBar (Anti-Glare Gamma Boost)"
                            return (True, data, polygon, engine) if return_meta else (True, data, polygon)
                except Exception:
                    pass

            # Pass 3F: Unsharp Mask Sharpening (For out-of-focus or low-resolution webcams)
            kernel = _SHARPEN_KERNEL if _SHARPEN_KERNEL is not None else np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]], dtype=np.float32)
            sharpened = cv2.filter2D(gray, -1, kernel)
            if PYZBAR_AVAILABLE:
                try:
                    objs = pyzbar.decode(sharpened)
                    for obj in objs:
                        data = obj.data.decode("utf-8", errors="replace").strip()
                        if data:
                            polygon = [(int(p.x), int(p.y)) for p in obj.polygon] if obj.polygon else []
                            engine = "PyZBar (Edge Sharpened)"
                            return (True, data, polygon, engine) if return_meta else (True, data, polygon)
                except Exception:
                    pass
        except Exception:
            pass

    return (False, "", [], "No QR Detected") if return_meta else (False, "", [])


def create_webcam_metadata(
    cam_index: int = 0,
    width: int = 1280,
    height: int = 720,
    payload: str = "",
    engine_name: str = "PyZBar / OpenCV Multi-Pass Real-Time Sensor",
) -> dict:
    """Creates rich zero-trust forensic metadata for a frame captured from live webcam stream."""
    raw_bytes = payload.encode("utf-8") if payload else b""
    sha256_hash = hashlib.sha256(raw_bytes).hexdigest() if payload else "N/A"

    gcd = math.gcd(width, height) if width > 0 and height > 0 else 1
    aspect_w = width // gcd if gcd else 16
    aspect_h = height // gcd if gcd else 9

    return {
        "file_name": f"Live Stream (Camera #{cam_index})",
        "file_path": f"DirectShow Video Device {cam_index} (Sensor Stream)",
        "file_size": f"{width}x{height} RAW",
        "file_size_bytes": len(raw_bytes),
        "sha256": sha256_hash,
        "dimensions": f"{width} x {height} px (HD Sensor Feed)",
        "width": width,
        "height": height,
        "format": "Real-Time Sensor Frame",
        "mode": "RGB (OpenCV DirectShow)",
        "aspect_ratio": f"{aspect_w}:{aspect_h} (Widescreen HD)" if (aspect_w == 16 and aspect_h == 9) else f"{aspect_w}:{aspect_h}",
        "camera_index": cam_index,
        "engine": engine_name,
    }

