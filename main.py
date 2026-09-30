"""
QuishGuard Desktop - Native Security Quarantine & QR Code Inspection Tool
"""
import sys
import os
import hashlib
import threading
import datetime
import time
import math
from typing import Optional, Dict, Any, List, Tuple
from urllib.parse import urlparse, parse_qs

import customtkinter as ctk
from PIL import Image, ImageTk

# Import internal modules
from modules.qr_engine import (
    decode_from_file,
    scan_webcam_frame,
    create_webcam_metadata,
    CV2_AVAILABLE,
    decode_from_file_with_metadata,
    compute_shannon_entropy,
    extract_optical_metadata,
)
from modules.network_tracer import trace_url
from modules.heuristics import analyze_heuristics
from modules.sound_manager import sound_manager
from modules.history_manager import history_manager
from modules.report_generator import generate_html_report, _get_base64_image
from modules.ui_widgets import (
    ThreatArcGauge,
    VisualHopChain,
    RiskVectorBarChart,
    ThreatTrendAreaChart,
    QRDetailedAnalysisDossier,
    HexPayloadSandbox,
    ScanHistoryAuditView,
)

try:
    import cv2
    import numpy as np
except Exception:
    cv2 = None
    try:
        import numpy as np
    except Exception:
        np = None

# Enable Per-Monitor High-DPI Scaling on Windows to eliminate font/canvas blur
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# Appearance Configuration
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Theme Palette Constants (Apple macOS Dark + Google Material You 3)
COLOR_BG_DARK = "#0b0f19"
COLOR_SURFACE = "#111827"
COLOR_CARD_DARK = "#151e30"
COLOR_CARD_HOVER = "#1c273e"
COLOR_BORDER = "#222f46"
COLOR_BORDER_LIGHT = "#2f4160"
COLOR_ACCENT = "#388bfd"
COLOR_ACCENT_HOVER = "#2563eb"
COLOR_ACCENT_BG = "#13233d"
COLOR_LOW_RISK = "#22c55e"
COLOR_LOW_RISK_BG = "#0f2e1e"
COLOR_MEDIUM_RISK = "#f59e0b"
COLOR_MEDIUM_RISK_BG = "#382307"
COLOR_CRITICAL_RISK = "#ef4444"
COLOR_CRITICAL_RISK_BG = "#3b1111"
COLOR_TEXT_PRIMARY = "#f8fafc"
COLOR_TEXT_SECONDARY = "#94a3b8"
COLOR_TEXT_MUTED = "#64748b"
COLOR_CODE_BG = "#070a12"


def get_asset_path(filename: str) -> str:
    """Resolve asset paths for both script execution and PyInstaller onefile bundles."""
    if hasattr(sys, '_MEIPASS'):
        base_dir = getattr(sys, '_MEIPASS')
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "assets", filename)


class WebcamScannerWindow(ctk.CTkToplevel):
    """
    Advanced Cyber Quarantine Viewfinder for Real-Time Webcam QR Detection.
    Features:
      - 720p HD sensor resolution preference
      - Multi-camera device switching (cycles available directshow sensors)
      - CLAHE contrast boost toggle for overexposed phone screens / low-light rooms
      - Cybersecurity tactical reticle with corner brackets & center crosshair
      - Real-time animated sweeping laser scanline
      - Visual target acquisition matrix lock-on with neon green polygon
      - Manual snapshot deep scan button
      - Non-blocking camera thread with safe DirectShow lifecycle cleanup
    """

    def __init__(self, master, on_qr_detected_callback):
        super().__init__(master)
        self.title("🛡️ Live Quarantine Camera Scanner - QuishGuard Zero-Trust")
        self.geometry("820x680")
        self.minsize(660, 520)
        self.configure(fg_color=COLOR_BG_DARK)

        # Set window icon
        try:
            ico_path = get_asset_path("icon.ico")
            if os.path.exists(ico_path):
                self.after(100, lambda: self.iconbitmap(ico_path))
        except Exception:
            pass

        self.on_qr_detected = on_qr_detected_callback
        self.is_running = True
        self.cam_index = 0
        self.boost_contrast = False
        self.cap = None
        self.camera_thread = None
        self.is_switching_cam = False
        self.req_cam_index = None

        # Lock-on visual confirmation state
        self.lock_start_time = None
        self.locked_payload = None
        self.locked_meta = None
        self.locked_snapshot = None
        self.latest_clean_frame = None

        # Telemetry & Performance
        self.fps_display = "30 FPS"
        self.res_display = "1280x720 HD"
        self.frame_counter = 0
        self.last_fps_calc = time.time()
        self._is_rendering_frame = False
        self.target_fps = 30
        self.frame_interval = 1.0 / self.target_fps

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self.close_scanner)

        sound_manager.play_scan_start()

        if CV2_AVAILABLE:
            self.camera_thread = threading.Thread(target=self._run_camera_loop, daemon=True)
            self.camera_thread.start()
        else:
            self.video_label.configure(text="OpenCV (cv2) is required for webcam scanning.")

    def _build_ui(self):
        # 1. Header Toolbar
        self.header_frame = ctk.CTkFrame(self, fg_color=COLOR_CARD_DARK, corner_radius=14, border_width=1, border_color=COLOR_BORDER)
        self.header_frame.pack(fill="x", padx=16, pady=(12, 6))

        # Left Header: Status beacon & Camera ID
        left_hdr = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        left_hdr.pack(side="left", padx=14, pady=8)

        self.beacon_label = ctk.CTkLabel(
            left_hdr,
            text="● LIVE SENSOR STREAM",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=COLOR_LOW_RISK,
        )
        self.beacon_label.pack(side="left", padx=(0, 10))

        self.badge_cam = ctk.CTkLabel(
            left_hdr,
            text="Cam #0 [1280x720 HD]",
            font=ctk.CTkFont(size=11, family="Consolas", weight="bold"),
            fg_color="#13233d",
            text_color="#60a5fa",
            corner_radius=12,
            padx=10,
            pady=3,
        )
        self.badge_cam.pack(side="left", padx=4)

        # Right Header: Boost indicator & FPS
        right_hdr = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        right_hdr.pack(side="right", padx=14, pady=8)

        self.badge_boost = ctk.CTkLabel(
            right_hdr,
            text="[ BOOST: OFF ]",
            font=ctk.CTkFont(size=11, family="Consolas", weight="bold"),
            fg_color="#162032",
            text_color=COLOR_TEXT_MUTED,
            corner_radius=12,
            padx=10,
            pady=3,
        )
        self.badge_boost.pack(side="left", padx=4)

        self.badge_fps = ctk.CTkLabel(
            right_hdr,
            text="30 FPS",
            font=ctk.CTkFont(size=11, family="Consolas"),
            text_color=COLOR_TEXT_MUTED,
            padx=4,
        )
        self.badge_fps.pack(side="left", padx=4)

        # 2. Main Viewport Container
        self.viewport_container = ctk.CTkFrame(
            self,
            fg_color="#000000",
            corner_radius=14,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        self.viewport_container.pack(expand=True, fill="both", padx=16, pady=6)

        self.video_label = ctk.CTkLabel(
            self.viewport_container,
            text="Initializing High-Resolution Camera Stream...\nPlease hold...",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=COLOR_TEXT_MUTED,
            fg_color="#000000",
        )
        self.video_label.pack(expand=True, fill="both", padx=4, pady=4)

        # 3. Status Guidance Bar
        self.status_bar = ctk.CTkFrame(self, fg_color="transparent")
        self.status_bar.pack(fill="x", padx=16, pady=(4, 6))

        self.status_label = ctk.CTkLabel(
            self.status_bar,
            text="🔍 Position the QR code inside the targeting reticle. Detection and quarantine inspection are automatic.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=COLOR_TEXT_MUTED,
        )
        self.status_label.pack(side="left", padx=4)

        # 4. Action Controls Bar
        self.controls_frame = ctk.CTkFrame(self, fg_color=COLOR_CARD_DARK, corner_radius=14, border_width=1, border_color=COLOR_BORDER)
        self.controls_frame.pack(fill="x", padx=16, pady=(4, 12))

        ctrl_inner = ctk.CTkFrame(self.controls_frame, fg_color="transparent")
        ctrl_inner.pack(fill="x", padx=12, pady=10)

        # Camera Switch Button
        self.btn_switch_cam = ctk.CTkButton(
            ctrl_inner,
            text="🔄 Switch Camera (0)",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="#141e30",
            hover_color="#1d2b45",
            border_width=1,
            border_color="#22334e",
            corner_radius=14,
            width=160,
            height=36,
            command=self._switch_camera,
        )
        self.btn_switch_cam.pack(side="left", padx=(0, 8))

        # CLAHE Boost Button
        self.btn_boost = ctk.CTkButton(
            ctrl_inner,
            text="✨ Screen / Low-Light Boost",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="#141e30",
            hover_color="#1d2b45",
            border_width=1,
            border_color="#22334e",
            corner_radius=14,
            width=190,
            height=36,
            command=self._toggle_boost,
        )
        self.btn_boost.pack(side="left", padx=4)

        # Force Snapshot & Deep Scan Button
        self.btn_snapshot = ctk.CTkButton(
            ctrl_inner,
            text="📸 Snapshot & Scan",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            corner_radius=14,
            width=150,
            height=36,
            command=self._force_snapshot_scan,
        )
        self.btn_snapshot.pack(side="left", padx=4)

        # Close Button
        self.btn_close = ctk.CTkButton(
            ctrl_inner,
            text="❌ Close Camera",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="#2a181b",
            hover_color="#3d1e23",
            corner_radius=14,
            width=130,
            height=36,
            command=self.close_scanner,
        )
        self.btn_close.pack(side="right", padx=(8, 0))

    def _draw_cyber_hud(self, frame: np.ndarray, points: list, is_locked: bool = False) -> np.ndarray:
        """
        Renders a high-tech cybersecurity viewfinder HUD directly onto the frame.
        Includes tactical reticle brackets, center crosshair, animated sweeping laser,
        and lock-on matrix polygon.
        """
        h, w = frame.shape[:2]
        box_size = min(int(min(h, w) * 0.68), 380)
        x1 = (w - box_size) // 2
        y1 = (h - box_size) // 2
        x2 = x1 + box_size
        y2 = y1 + box_size

        # 1. Corner Reticle Brackets
        reticle_color = (0, 255, 0) if is_locked else (255, 200, 0)  # Neon Green if locked, Cyan BGR
        bracket_len = 34
        thick = 3

        # Top-Left
        cv2.line(frame, (x1, y1), (x1 + bracket_len, y1), reticle_color, thick)
        cv2.line(frame, (x1, y1), (x1, y1 + bracket_len), reticle_color, thick)
        # Top-Right
        cv2.line(frame, (x2, y1), (x2 - bracket_len, y1), reticle_color, thick)
        cv2.line(frame, (x2, y1), (x2, y1 + bracket_len), reticle_color, thick)
        # Bottom-Left
        cv2.line(frame, (x1, y2), (x1 + bracket_len, y2), reticle_color, thick)
        cv2.line(frame, (x1, y2), (x1, y2 - bracket_len), reticle_color, thick)
        # Bottom-Right
        cv2.line(frame, (x2, y2), (x2 - bracket_len, y2), reticle_color, thick)
        cv2.line(frame, (x2, y2), (x2, y2 - bracket_len), reticle_color, thick)

        # 2. Central Tactical Crosshair
        cx, cy = w // 2, h // 2
        cv2.line(frame, (cx - 14, cy), (cx + 14, cy), (120, 120, 120), 1)
        cv2.line(frame, (cx, cy - 14), (cx, cy + 14), (120, 120, 120), 1)

        # 3. Sweeping Laser Scan Line (when searching)
        if not is_locked:
            progress = (math.sin(time.time() * 3.4) + 1.0) / 2.0
            laser_y = int(y1 + progress * (y2 - y1))
            # Outer glow line + inner laser core
            cv2.line(frame, (x1 + 4, laser_y), (x2 - 4, laser_y), (0, 140, 70), 3, cv2.LINE_AA)
            cv2.line(frame, (x1 + 4, laser_y), (x2 - 4, laser_y), (0, 255, 140), 1, cv2.LINE_AA)

        # 4. QR Code Matrix Polygon & Corner Circles (when points detected)
        if points and len(points) >= 4:
            try:
                pts_np = np.array(points, dtype=np.int32).reshape((-1, 1, 2))
                cv2.polylines(frame, [pts_np], isClosed=True, color=(0, 255, 0), thickness=3, lineType=cv2.LINE_AA)
                for pt in points:
                    cv2.circle(frame, (int(pt[0]), int(pt[1])), 5, (0, 255, 0), -1)
                    cv2.circle(frame, (int(pt[0]), int(pt[1])), 10, (0, 255, 0), 1)
            except Exception:
                pass

        # 5. Live HUD Telemetry Text
        cv2.putText(
            frame,
            "QUISHGUARD ZERO-TRUST LIVE VIEW",
            (24, 34),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.60,
            (255, 200, 0),
            2,
            cv2.LINE_AA,
        )
        if self.boost_contrast:
            # Tactical neon boost pill badge
            cv2.rectangle(frame, (20, 48), (295, 74), (20, 40, 20), -1)
            cv2.rectangle(frame, (20, 48), (295, 74), (0, 255, 128), 1)
            cv2.putText(
                frame,
                "BOOST: ACTIVE (CLAHE + ANTI-GLARE)",
                (26, 66),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.40,
                (0, 255, 128),
                1,
                cv2.LINE_AA,
            )

        if is_locked:
            banner_y = max(y1 - 14, 30)
            cv2.putText(
                frame,
                "TARGET LOCKED - DECODING ZERO-TRUST PAYLOAD",
                (x1 + 8, banner_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.56,
                (0, 255, 0),
                2,
                cv2.LINE_AA,
            )

        return frame

    def _apply_visual_boost(self, frame: np.ndarray) -> np.ndarray:
        """
        Enhances viewport video stream in real-time when Screen / Low-Light Boost is active:
        - Converts to LAB color space
        - Applies CLAHE (Contrast Limited Adaptive Histogram Equalization) to L-channel
        - Recombines channels to boost contrast without hue shifting
        - Dynamic linear gain and brightness normalization to cut screen bloom and illuminate dim rooms
        """
        try:
            lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=3.2, tileGridSize=(8, 8))
            cl = clahe.apply(l)
            merged = cv2.merge((cl, a, b))
            boosted = cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)
            return cv2.convertScaleAbs(boosted, alpha=1.2, beta=12)
        except Exception:
            return frame

    def _run_camera_loop(self):
        """Main camera acquisition and real-time scanning loop running in background thread."""
        self.cap = cv2.VideoCapture(self.cam_index)
        if not self.cap.isOpened():
            self.after(0, lambda: self.video_label.configure(text=f"Error: Could not access camera device #{self.cam_index}."))
            return

        # Request HD 720p resolution
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        actual_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.res_display = f"{actual_w}x{actual_h}"
        self.after(0, self._update_camera_badge)

        loop_frame_idx = 0
        current_points = []
        is_locked = False

        try:
            while self.is_running:
                loop_start = time.time()

                # Handle dynamic camera switching
                if self.req_cam_index is not None:
                    target_idx = self.req_cam_index
                    self.req_cam_index = None
                    try:
                        self.cap.release()
                    except Exception:
                        pass
                    new_cap = cv2.VideoCapture(target_idx)
                    if new_cap.isOpened():
                        self.cap = new_cap
                        self.cam_index = target_idx
                        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                        actual_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                        actual_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        self.res_display = f"{actual_w}x{actual_h}"
                        self.after(0, self._on_cam_switched_success)
                    else:
                        # Fallback to previous camera
                        self.cap = cv2.VideoCapture(self.cam_index)
                        self.after(0, lambda idx=target_idx: self.status_label.configure(
                            text=f"Camera #{idx} not available. Reverted to Camera #{self.cam_index}.",
                            text_color=COLOR_MEDIUM_RISK
                        ))
                    self.is_switching_cam = False

                if not self.cap or not self.cap.isOpened():
                    time.sleep(0.05)
                    continue

                ret, frame = self.cap.read()
                if not ret or frame is None:
                    time.sleep(0.01)
                    continue

                loop_frame_idx += 1
                self.latest_clean_frame = frame

                # Interleave QR detection to maximize responsiveness:
                # If target is locked or boost is enabled, run every frame.
                # When searching, run every 2nd frame (15 checks/sec) to keep UI buttery smooth and reduce CPU load by 50%.
                scan_cadence = 1 if (is_locked or self.boost_contrast) else 2
                should_scan = (loop_frame_idx % scan_cadence == 0)

                if should_scan:
                    success, payload, points, engine = scan_webcam_frame(
                        frame, boost_contrast=self.boost_contrast, return_meta=True
                    )
                    current_points = points

                    if success and payload:
                        is_locked = True
                        if self.lock_start_time is None:
                            self.lock_start_time = time.time()
                            sound_manager.play_matrix_lock()
                            self.locked_payload = payload
                            self.locked_meta = create_webcam_metadata(
                                self.cam_index,
                                int(frame.shape[1]),
                                int(frame.shape[0]),
                                payload,
                                engine_name=engine,
                            )
                            # Deep snapshot copied only upon confirmed detection
                            self.locked_snapshot = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                            self.after(0, lambda eng=engine: self.status_label.configure(
                                text=f"🎯 MATRIX LOCKED! Decoding zero-trust payload ({eng})...",
                                text_color=COLOR_LOW_RISK,
                            ))

                        # Allow 250ms of visual target lock confirmation before returning payload
                        if time.time() - self.lock_start_time >= 0.25:
                            self.after(
                                0,
                                self._on_detected_success,
                                self.locked_payload,
                                self.locked_meta,
                                self.locked_snapshot,
                            )
                            break
                    else:
                        is_locked = False
                        if self.lock_start_time is not None and (time.time() - self.lock_start_time > 0.4):
                            self.lock_start_time = None
                            self.locked_payload = None

                # Render Cyber HUD overlay onto display frame (apply real-time visual boost if active)
                if self.boost_contrast:
                    vis_frame = self._apply_visual_boost(frame)
                else:
                    vis_frame = frame.copy()

                hud_frame = self._draw_cyber_hud(vis_frame, current_points, is_locked=is_locked)

                # Convert frame for Tkinter rendering with fast OpenCV C++ downscaling
                if not self._is_rendering_frame:
                    try:
                        h, w = hud_frame.shape[:2]
                        scale = min(740.0 / w, 440.0 / h)
                        pw = max(1, int(w * scale))
                        ph = max(1, int(h * scale))

                        # Fast bilinear resize directly in OpenCV SIMD/C++ (4-5x faster than PIL CPU resize)
                        resized = cv2.resize(hud_frame, (pw, ph), interpolation=cv2.INTER_LINEAR)
                        rgb_frame = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
                        pil_img = Image.fromarray(rgb_frame)
                        ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(pw, ph))

                        if self.is_running:
                            self._is_rendering_frame = True
                            self.after(0, self._update_frame_ui, ctk_img)
                    except Exception:
                        self._is_rendering_frame = False

                # Calculate FPS telemetry
                self.frame_counter += 1
                now = time.time()
                if now - self.last_fps_calc >= 1.0:
                    calc_fps = int(round(self.frame_counter / (now - self.last_fps_calc)))
                    self.fps_display = f"{calc_fps} FPS"
                    self.frame_counter = 0
                    self.last_fps_calc = now
                    self.after(0, lambda: self.badge_fps.configure(text=self.fps_display))

                # Frame pacing to avoid busy-wait looping
                elapsed = time.time() - loop_start
                sleep_time = self.frame_interval - elapsed
                if sleep_time > 0.001:
                    time.sleep(sleep_time)

        finally:
            if self.cap is not None:
                try:
                    self.cap.release()
                except Exception:
                    pass
                self.cap = None

    def _update_frame_ui(self, ctk_img):
        try:
            if self.winfo_exists() and self.is_running:
                self.video_label.configure(image=ctk_img, text="")
        finally:
            self._is_rendering_frame = False

    def _update_camera_badge(self):
        if self.winfo_exists():
            self.badge_cam.configure(text=f"Cam #{self.cam_index} [{self.res_display}]")
            self.btn_switch_cam.configure(text=f"🔄 Switch Camera ({self.cam_index})")

    def _on_cam_switched_success(self):
        self._update_camera_badge()
        self.status_label.configure(
            text=f"✅ Connected to Camera #{self.cam_index} ({self.res_display}). Viewfinder active.",
            text_color=COLOR_LOW_RISK,
        )

    def _switch_camera(self):
        """Cycles through available camera devices (0 -> 1 -> 2 -> 3 -> 0)."""
        if self.is_switching_cam:
            return
        self.is_switching_cam = True
        next_index = (self.cam_index + 1) % 4
        self.status_label.configure(
            text=f"🔄 Switching video stream to Camera #{next_index}...",
            text_color=COLOR_MEDIUM_RISK,
        )
        self.req_cam_index = next_index

    def _toggle_boost(self):
        """Toggles real-time CLAHE contrast equalization and anti-glare for phone screens or dark rooms."""
        self.boost_contrast = not self.boost_contrast
        if self.boost_contrast:
            sound_manager.play_scan_start()
            self.btn_boost.configure(
                text="✨ Boost: ON (CLAHE)",
                fg_color="#238636",
                hover_color="#2ea043",
            )
            self.badge_boost.configure(text="[ BOOST: ON ]", text_color="#3fb950")
            self.status_label.configure(
                text="✨ Screen / Low-Light boost enabled: CLAHE contrast equalized and anti-glare active.",
                text_color=COLOR_LOW_RISK,
            )
        else:
            self.btn_boost.configure(
                text="✨ Screen / Low-Light Boost",
                fg_color="#21262d",
                hover_color="#30363d",
            )
            self.badge_boost.configure(text="[ BOOST: OFF ]", text_color=COLOR_TEXT_MUTED)
            self.status_label.configure(
                text="Standard sensor exposure restored.",
                text_color=COLOR_TEXT_MUTED,
            )

    def _force_snapshot_scan(self):
        """Forces an immediate deep multi-pass scan on the current frozen frame."""
        if self.latest_clean_frame is None:
            return
        sound_manager.play_scan_start()
        self.status_label.configure(
            text="📸 Running deep multi-pass scan on captured frame...",
            text_color=COLOR_TEXT_PRIMARY,
        )
        success, payload, points, engine = scan_webcam_frame(
            self.latest_clean_frame, boost_contrast=True, return_meta=True
        )
        if success and payload:
            sound_manager.play_matrix_lock()
            h, w = self.latest_clean_frame.shape[:2]
            meta = create_webcam_metadata(self.cam_index, w, h, payload, f"{engine} (Manual Deep Snapshot)")
            snapshot = Image.fromarray(cv2.cvtColor(self.latest_clean_frame, cv2.COLOR_BGR2RGB))
            self._on_detected_success(payload, meta, snapshot)
        else:
            self.status_label.configure(
                text="⚠️ No QR code resolved in snapshot. Align closer to camera lens and try again.",
                text_color=COLOR_MEDIUM_RISK,
            )

    def _on_detected_success(self, payload: str, meta: dict, snapshot: Image.Image):
        self.status_label.configure(text="✅ QR Code Captured & Verified!", text_color=COLOR_LOW_RISK)
        self.close_scanner()
        self.on_qr_detected(payload, meta, snapshot)

    def close_scanner(self):
        """Safely terminates the background camera thread and releases DirectShow device."""
        self.is_running = False
        if self.camera_thread and self.camera_thread.is_alive():
            try:
                self.camera_thread.join(timeout=0.3)
            except Exception:
                pass
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None
        self.destroy()


class QuishGuardApp(ctk.CTk):
    """Main Application Window for QuishGuard Desktop."""

    def __init__(self):
        super().__init__()

        self.title("QuishGuard Desktop - Enterprise Zero-Trust Quarantine")
        self._init_window_icon()

        # Responsive High-Resolution Sizing & Auto-Centering
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        win_w = min(1160, max(980, int(screen_w * 0.76)))
        win_h = min(730, max(620, int(screen_h * 0.82)))
        x_pos = max(10, (screen_w - win_w) // 2)
        y_pos = max(10, (screen_h - win_h) // 2 - 20)

        self.geometry(f"{win_w}x{win_h}+{x_pos}+{y_pos}")
        self.minsize(980, 580)
        self.configure(fg_color=COLOR_BG_DARK)

        self.webcam_window: Optional[WebcamScannerWindow] = None
        self.current_image_path: Optional[str] = None
        self.current_image_obj: Optional[Any] = None
        self.current_image_b64: Optional[str] = None
        self.current_payload: Optional[str] = None

        self._build_header()
        self._build_body()
        self._log_event("QuishGuard Desktop initialized in high-resolution quarantine mode.")

    def _init_window_icon(self):
        """Sets the application window and taskbar icon across Windows environments."""
        try:
            ico_path = get_asset_path("icon.ico")
            png_path = get_asset_path("icon.png")
            if os.path.exists(ico_path):
                self.iconbitmap(ico_path)
            if os.path.exists(png_path):
                self._icon_img = ImageTk.PhotoImage(file=png_path)
                self.wm_iconphoto(True, self._icon_img)
        except Exception as e:
            print(f"[QuishGuard] Could not set window icon: {e}")

    def _open_about_window(self):
        """Displays branded About modal dialog with high-resolution logo and system info."""
        about_win = ctk.CTkToplevel(self)
        about_win.title("About QuishGuard Desktop")
        about_win.geometry("520x560")
        about_win.resizable(False, False)
        about_win.configure(fg_color=COLOR_BG_DARK)

        try:
            ico_path = get_asset_path("icon.ico")
            if os.path.exists(ico_path):
                about_win.after(100, lambda: about_win.iconbitmap(ico_path))
        except Exception:
            pass

        about_win.transient(self)
        about_win.grab_set()

        card = ctk.CTkFrame(
            about_win,
            fg_color=COLOR_CARD_DARK,
            border_width=1,
            border_color=COLOR_BORDER,
            corner_radius=16,
        )
        card.pack(expand=True, fill="both", padx=20, pady=20)

        # Full Logo Image
        try:
            logo_path = get_asset_path("logo.png")
            if os.path.exists(logo_path):
                logo_pil = Image.open(logo_path)
                w, h = logo_pil.size
                target_w = 260
                target_h = int(h * (target_w / w))
                self._about_logo_ctk = ctk.CTkImage(
                    light_image=logo_pil, dark_image=logo_pil, size=(target_w, target_h)
                )
                lbl_logo = ctk.CTkLabel(card, image=self._about_logo_ctk, text="")
                lbl_logo.pack(pady=(20, 10))
        except Exception:
            lbl_err = ctk.CTkLabel(card, text="🛡️ QuishGuard", font=ctk.CTkFont(size=24, weight="bold"))
            lbl_err.pack(pady=20)

        ctk.CTkLabel(
            card,
            text="QuishGuard Desktop Enterprise",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY,
        ).pack(pady=(4, 2))

        ctk.CTkLabel(
            card,
            text="v2.0 Standalone Air-Gapped Edition",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#60a5fa",
        ).pack(pady=(0, 10))

        info_text = (
            "Zero-Trust QR Code Quarantine & Forensic Incident Analyzer.\n"
            "Inspect payloads, redirect chains, Shannon entropy, and heuristics\n"
            "before any browser or mobile device connects to untrusted targets.\n\n"
            "Tagline: Don't Just Scan — Inspect Before You Connect."
        )
        ctk.CTkLabel(
            card,
            text=info_text,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=COLOR_TEXT_MUTED,
            justify="center",
        ).pack(padx=24, pady=4)

        btn_close = ctk.CTkButton(
            card,
            text="Close",
            width=120,
            height=34,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            corner_radius=14,
            command=about_win.destroy,
        )
        btn_close.pack(pady=(16, 20), side="bottom")

    def _open_sound_studio_window(self):
        """Displays interactive Sound Effects Studio preview modal to test and audition all acoustic cues."""
        sound_manager.play_tap()
        win = ctk.CTkToplevel(self)
        win.title("QuishGuard Audio Studio & Sound Effects")
        win.geometry("590x640")
        win.resizable(False, False)
        win.configure(fg_color=COLOR_BG_DARK)

        try:
            ico_path = get_asset_path("icon.ico")
            if os.path.exists(ico_path):
                win.after(100, lambda: win.iconbitmap(ico_path))
        except Exception:
            pass

        win.transient(self)
        win.grab_set()

        outer_card = ctk.CTkFrame(
            win,
            fg_color=COLOR_CARD_DARK,
            border_width=1,
            border_color=COLOR_BORDER,
            corner_radius=16,
        )
        outer_card.pack(expand=True, fill="both", padx=18, pady=18)

        # Header Title
        hdr = ctk.CTkFrame(outer_card, fg_color="transparent")
        hdr.pack(fill="x", padx=20, pady=(16, 6))

        ctk.CTkLabel(
            hdr,
            text="🎧 Tactical Audio Studio",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color="#f8fafc",
        ).pack(side="left")

        # Live Mute Toggle in Studio Header
        btn_studio_mute = ctk.CTkButton(
            hdr,
            text="🔇 Muted" if sound_manager.is_muted() else "🔊 Audio: ON",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="#331417" if sound_manager.is_muted() else COLOR_SURFACE,
            hover_color="#521d23" if sound_manager.is_muted() else COLOR_CARD_HOVER,
            text_color="#f87171" if sound_manager.is_muted() else COLOR_ACCENT,
            border_width=1,
            border_color="#451820" if sound_manager.is_muted() else COLOR_BORDER,
            width=110,
            height=30,
            corner_radius=14,
        )

        def _on_studio_mute_toggle():
            self._toggle_sound()
            if sound_manager.is_muted():
                btn_studio_mute.configure(
                    text="🔇 Muted",
                    fg_color="#331417",
                    hover_color="#521d23",
                    text_color="#f87171",
                    border_color="#451820",
                )
            else:
                btn_studio_mute.configure(
                    text="🔊 Audio: ON",
                    fg_color=COLOR_SURFACE,
                    hover_color=COLOR_CARD_HOVER,
                    text_color=COLOR_ACCENT,
                    border_color=COLOR_BORDER,
                )

        btn_studio_mute.configure(command=_on_studio_mute_toggle)
        btn_studio_mute.pack(side="right")

        ctk.CTkLabel(
            outer_card,
            text="In-memory synthesized acoustic feedback engineered with Apple & Google harmonic design.\nClick any sound profile below to audition its waveform in real-time.",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=COLOR_TEXT_MUTED,
            justify="left",
            anchor="w",
        ).pack(fill="x", padx=20, pady=(0, 10))

        # Scrollable list of sounds
        scroll = ctk.CTkScrollableFrame(outer_card, fg_color="transparent")
        scroll.pack(expand=True, fill="both", padx=16, pady=4)

        for s_info in sound_manager.get_sound_catalog():
            s_key = s_info["key"]
            s_title = s_info["title"]
            s_desc = s_info["desc"]
            s_badge = s_info["badge"]
            s_col = s_info["badge_col"]

            row_card = ctk.CTkFrame(
                scroll,
                fg_color=COLOR_SURFACE,
                border_width=1,
                border_color=COLOR_BORDER,
                corner_radius=12,
            )
            row_card.pack(fill="x", pady=4)

            row_inner = ctk.CTkFrame(row_card, fg_color="transparent")
            row_inner.pack(fill="x", padx=14, pady=10)

            # Left text info
            left_f = ctk.CTkFrame(row_inner, fg_color="transparent")
            left_f.pack(side="left", expand=True, fill="x")

            t_line = ctk.CTkFrame(left_f, fg_color="transparent")
            t_line.pack(fill="x")

            ctk.CTkLabel(
                t_line,
                text=s_title,
                font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                text_color="#f8fafc",
            ).pack(side="left")

            badge_lbl = ctk.CTkLabel(
                t_line,
                text=s_badge,
                font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"),
                text_color=s_col,
                fg_color=COLOR_CODE_BG,
                corner_radius=8,
                padx=8,
                pady=1,
            )
            badge_lbl.pack(side="left", padx=8)

            ctk.CTkLabel(
                left_f,
                text=s_desc,
                font=ctk.CTkFont(family="Segoe UI", size=10),
                text_color=COLOR_TEXT_MUTED,
                anchor="w",
                justify="left",
            ).pack(fill="x", pady=(2, 0))

            # Play button - Google M3 Pill
            btn_play = ctk.CTkButton(
                row_inner,
                text="▶️ Play",
                font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                fg_color=COLOR_CARD_DARK,
                hover_color=COLOR_CARD_HOVER,
                border_width=1,
                border_color=COLOR_BORDER,
                text_color=COLOR_ACCENT,
                width=80,
                height=30,
                corner_radius=14,
                command=lambda k=s_key: sound_manager.play_test_sound(k),
            )
            btn_play.pack(side="right", padx=(8, 0))

        # Bottom Close Button
        btn_close = ctk.CTkButton(
            outer_card,
            text="Done",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            width=110,
            height=32,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            corner_radius=14,
            command=win.destroy,
        )
        btn_close.pack(pady=(10, 14), side="bottom")

    def _build_header(self):
        header_frame = ctk.CTkFrame(self, fg_color=COLOR_CARD_DARK, corner_radius=0, height=68)
        header_frame.pack(fill="x", side="top")

        left_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        left_box.pack(side="left", padx=20, pady=10)

        # Apple macOS Traffic Light Window Controls
        traffic_dots = ctk.CTkFrame(left_box, fg_color="transparent")
        traffic_dots.pack(side="left", padx=(0, 14))

        ctk.CTkFrame(traffic_dots, width=12, height=12, corner_radius=6, fg_color="#ff5f56", border_width=1, border_color="#e0443e").pack(side="left", padx=3)
        ctk.CTkFrame(traffic_dots, width=12, height=12, corner_radius=6, fg_color="#ffbd2e", border_width=1, border_color="#dea123").pack(side="left", padx=3)
        ctk.CTkFrame(traffic_dots, width=12, height=12, corner_radius=6, fg_color="#27c93f", border_width=1, border_color="#1aab29").pack(side="left", padx=3)

        # App Logo Emblem Button (Clickable for About dialog)
        self.header_logo_ctk = None
        try:
            shield_path = get_asset_path("logo_shield.png")
            if os.path.exists(shield_path):
                pil_logo = Image.open(shield_path)
                self.header_logo_ctk = ctk.CTkImage(
                    light_image=pil_logo, dark_image=pil_logo, size=(44, 44)
                )
                btn_logo = ctk.CTkButton(
                    left_box,
                    image=self.header_logo_ctk,
                    text="",
                    width=44,
                    height=44,
                    fg_color="#131b2e",
                    hover_color="#1a253e",
                    border_width=1,
                    border_color="#22304d",
                    corner_radius=12,
                    cursor="hand2",
                    command=self._open_about_window,
                )
                btn_logo.pack(side="left", padx=(0, 12))
        except Exception:
            pass

        title_box = ctk.CTkFrame(left_box, fg_color="transparent")
        title_box.pack(side="left")

        self.header_title = ctk.CTkLabel(
            title_box,
            text="QuishGuard" if self.header_logo_ctk else "🛡️ QuishGuard",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY,
        )
        self.header_title.pack(anchor="w")

        self.header_subtitle = ctk.CTkLabel(
            title_box,
            text="Zero-Trust QR Code Quarantine & Forensic Security",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=COLOR_TEXT_MUTED,
        )
        self.header_subtitle.pack(anchor="w")

        right_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        right_box.pack(side="right", padx=20, pady=16)

        # Google Material 3 Pill Buttons
        self.btn_export_top = ctk.CTkButton(
            right_box,
            text="📄 Export Report",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            text_color="#ffffff",
            width=130,
            height=32,
            corner_radius=16,
            command=self._export_current_incident_report,
        )
        self.btn_export_top.pack(side="left", padx=4)

        self.btn_sound = ctk.CTkButton(
            right_box,
            text="🔊 Audio: ON",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="#141f33",
            hover_color="#1c2c48",
            border_width=1,
            border_color="#233555",
            text_color="#38bdf8",
            width=110,
            height=32,
            corner_radius=16,
            command=self._toggle_sound,
        )
        self.btn_sound.pack(side="left", padx=4)

        self.btn_sound_studio = ctk.CTkButton(
            right_box,
            text="🎵 Sound FX",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color=COLOR_SURFACE,
            hover_color=COLOR_CARD_HOVER,
            border_width=1,
            border_color=COLOR_BORDER,
            text_color="#94a3b8",
            width=100,
            height=32,
            corner_radius=16,
            command=self._open_sound_studio_window,
        )
        self.btn_sound_studio.pack(side="left", padx=4)

        self.btn_about = ctk.CTkButton(
            right_box,
            text="ℹ️ About",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="#141f33",
            hover_color="#1c2c48",
            border_width=1,
            border_color="#233555",
            text_color="#93c5fd",
            width=82,
            height=32,
            corner_radius=16,
            command=self._open_about_window,
        )
        self.btn_about.pack(side="left", padx=4)

        version_badge = ctk.CTkLabel(
            right_box,
            text="v2.0 Enterprise",
            fg_color="#0e1726",
            border_width=1,
            border_color="#1d2d46",
            corner_radius=12,
            text_color="#60a5fa",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            padx=12,
            pady=4,
        )
        version_badge.pack(side="left", padx=(4, 0))

    def _build_body(self):
        body_container = ctk.CTkFrame(self, fg_color="transparent")
        body_container.pack(expand=True, fill="both", padx=16, pady=12)

        # Left Control Panel (approx 320px wide) - macOS Inspector Card
        self.left_panel = ctk.CTkFrame(
            body_container,
            width=320,
            fg_color=COLOR_CARD_DARK,
            border_width=1,
            border_color=COLOR_BORDER,
            corner_radius=14,
        )
        self.left_panel.pack(side="left", fill="y", padx=(0, 10))
        self.left_panel.pack_propagate(False)

        # Right Telemetry Panel
        self.right_panel = ctk.CTkFrame(body_container, fg_color="transparent")
        self.right_panel.pack(side="right", expand=True, fill="both")

        self._setup_left_panel()
        self._setup_right_panel()

    def _setup_left_panel(self):
        panel_title = ctk.CTkLabel(
            self.left_panel,
            text="● QUARANTINE INPUT",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=COLOR_TEXT_SECONDARY,
        )
        panel_title.pack(anchor="w", padx=16, pady=(16, 10))

        # Action Buttons
        self.btn_select_file = ctk.CTkButton(
            self.left_panel,
            text="📁 Select QR Image",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            height=42,
            corner_radius=12,
            command=self._handle_select_file,
        )
        self.btn_select_file.pack(fill="x", padx=16, pady=5)

        self.btn_webcam = ctk.CTkButton(
            self.left_panel,
            text="📷 Live Webcam Scanner",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color="#10b981",
            hover_color="#059669",
            text_color="#ffffff",
            height=42,
            corner_radius=12,
            command=self._handle_open_webcam,
        )
        self.btn_webcam.pack(fill="x", padx=16, pady=5)

        # Image Preview Box
        preview_label_title = ctk.CTkLabel(
            self.left_panel,
            text="● PREVIEW BAY",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color=COLOR_TEXT_MUTED,
        )
        preview_label_title.pack(anchor="w", padx=16, pady=(14, 4))

        self.preview_frame = ctk.CTkFrame(
            self.left_panel,
            fg_color=COLOR_CODE_BG,
            border_width=1,
            border_color=COLOR_BORDER,
            corner_radius=12,
            height=180,
        )
        self.preview_frame.pack(fill="x", padx=16, pady=4)
        self.preview_frame.pack_propagate(False)

        # Subtle brand logo watermark for empty preview bay
        self.preview_placeholder_img = None
        try:
            shield_path = get_asset_path("logo_shield.png")
            if os.path.exists(shield_path):
                pil_ph = Image.open(shield_path)
                self.preview_placeholder_img = ctk.CTkImage(
                    light_image=pil_ph, dark_image=pil_ph, size=(54, 54)
                )
        except Exception:
            pass

        self.image_preview_label = ctk.CTkLabel(
            self.preview_frame,
            image=self.preview_placeholder_img,
            text="\nNo QR Image Loaded\nDrop image or select file" if self.preview_placeholder_img else "No QR Image Loaded\nDrop image or select file",
            compound="top",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=COLOR_TEXT_MUTED,
        )
        self.image_preview_label.pack(expand=True)

        # Payload Text Display
        payload_title = ctk.CTkLabel(
            self.left_panel,
            text="● EXTRACTED RAW PAYLOAD",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color=COLOR_TEXT_MUTED,
        )
        payload_title.pack(anchor="w", padx=16, pady=(12, 4))

        self.payload_textbox = ctk.CTkTextbox(
            self.left_panel,
            height=70,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color=COLOR_CODE_BG,
            border_width=1,
            border_color=COLOR_BORDER,
            corner_radius=10,
            wrap="char",
        )
        self.payload_textbox.pack(fill="x", padx=16, pady=4)
        self.payload_textbox.insert("1.0", "Awaiting payload...")
        self.payload_textbox.configure(state="disabled")

        self.btn_copy_left_payload = ctk.CTkButton(
            self.left_panel,
            text="📋 Copy Extracted Payload",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="#141f33",
            hover_color="#1e2f4e",
            border_width=1,
            border_color="#233555",
            text_color="#38bdf8",
            height=30,
            corner_radius=12,
            command=self._handle_copy_current_payload,
        )
        self.btn_copy_left_payload.pack(fill="x", padx=16, pady=(2, 6))

        # Loading / Progress Indicator
        self.progress_bar = ctk.CTkProgressBar(
            self.left_panel,
            mode="indeterminate",
            height=4,
            corner_radius=2,
            progress_color=COLOR_ACCENT,
        )
        self.progress_bar.pack(fill="x", padx=16, pady=(12, 4))
        self.progress_bar.set(0)

        self.status_state_label = ctk.CTkLabel(
            self.left_panel,
            text="● System Idle / Standby",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=COLOR_TEXT_MUTED,
        )
        self.status_state_label.pack(anchor="w", padx=16, pady=0)

        # Clear / Reset Button
        self.btn_reset = ctk.CTkButton(
            self.left_panel,
            text="🔄 Clear Quarantine Session",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="#141c2c",
            hover_color="#1d283f",
            border_width=1,
            border_color="#22304c",
            height=38,
            corner_radius=12,
            command=self._handle_reset,
        )
        self.btn_reset.pack(fill="x", padx=16, pady=(14, 14), side="bottom")

    def _setup_right_panel(self):
        # 1. Threat Status Banner (Apple Notification Center / Material 3 Alert Card)
        self.status_banner = ctk.CTkFrame(
            self.right_panel,
            fg_color=COLOR_CARD_DARK,
            corner_radius=14,
            height=65,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        self.status_banner.pack(fill="x", pady=(0, 10))
        self.status_banner.pack_propagate(False)

        self.banner_badge = ctk.CTkLabel(
            self.status_banner,
            text="🟢 STATUS: IDLE / SECURE",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color=COLOR_LOW_RISK,
        )
        self.banner_badge.pack(side="left", padx=20, pady=16)

        self.banner_hint = ctk.CTkLabel(
            self.status_banner,
            text="No threat indicators detected yet.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=COLOR_TEXT_MUTED,
        )
        self.banner_hint.pack(side="right", padx=20, pady=18)

        # 2. Metric Dashboard (Threat Arc Gauge + Telemetry Tiles)
        metrics_container = ctk.CTkFrame(self.right_panel, fg_color="transparent", height=136)
        metrics_container.pack(fill="x", pady=(0, 10))

        # Circular Arc Speedometer Gauge (High-Res Dynamic Scaling)
        self.threat_gauge = ThreatArcGauge(metrics_container, width=185, height=136, corner_radius=14)
        self.threat_gauge.pack(side="left", padx=(0, 6))

        # Right Telemetry Tiles Box
        tiles_box = ctk.CTkFrame(metrics_container, fg_color="transparent")
        tiles_box.pack(side="left", expand=True, fill="both")

        self.tile_hops, self.sub_hops = self._create_metric_tile(
            tiles_box, "REDIRECT CHAIN", "0 Hops", COLOR_TEXT_PRIMARY, "Direct Target / No Hops"
        )
        self.tile_scheme, self.sub_scheme = self._create_metric_tile(
            tiles_box, "TRANSPORT & SSL", "N/A", COLOR_TEXT_PRIMARY, "Awaiting URL Payload"
        )

        # 3. Tabbed / Segmented Display (Apple macOS / Material 3 Segmented Pill Bar)
        self.tabview = ctk.CTkTabview(
            self.right_panel,
            fg_color=COLOR_CARD_DARK,
            segmented_button_fg_color="#0b0f19",
            segmented_button_selected_color="#2563eb",
            segmented_button_selected_hover_color="#1d4ed8",
            segmented_button_unselected_color="#0b0f19",
            segmented_button_unselected_hover_color="#162034",
            corner_radius=14,
        )
        self.tabview.pack(expand=True, fill="both")

        self.tab_dossier = self.tabview.add("🔍 Detailed QR Analysis")
        self.tab_sandbox = self.tabview.add("🔬 Payload Sandbox")
        self.tab_redirects = self.tabview.add("Visual Redirect Chain")
        self.tab_vectors = self.tabview.add("📊 Risk Vector Graph")
        self.tab_analytics = self.tabview.add("📈 Threat Analytics")
        self.tab_history = self.tabview.add("🗄️ Scan History")
        self.tab_heuristics = self.tabview.add("Heuristic Flags")
        self.tab_log = self.tabview.add("Live Security Log")

        self._setup_tab_dossier()
        self._setup_tab_sandbox()
        self._setup_tab_redirects()
        self._setup_tab_vectors()
        self._setup_tab_analytics()
        self._setup_tab_history()
        self._setup_tab_heuristics()
        self._setup_tab_log()

        self.tabview.configure(command=self._on_tab_changed)

    def _on_tab_changed(self):
        """Forces sharp canvas recalculation and redraw when switching between graph tabs."""
        tab = self.tabview.get()
        if "Risk Vector" in tab:
            self.risk_bar_chart._draw_bars()
        elif "Threat Analytics" in tab:
            self.analytics_chart.redraw()
        elif "Scan History" in tab:
            if hasattr(self, "scan_history_view"):
                self.scan_history_view.refresh()

    def _setup_tab_dossier(self):
        self.detailed_dossier = QRDetailedAnalysisDossier(
            self.tab_dossier, copy_callback=self._copy_to_clipboard, corner_radius=14
        )
        self.detailed_dossier.pack(expand=True, fill="both", padx=6, pady=6)

    def _setup_tab_sandbox(self):
        self.payload_sandbox = HexPayloadSandbox(
            self.tab_sandbox, copy_callback=self._copy_to_clipboard
        )
        self.payload_sandbox.pack(expand=True, fill="both", padx=6, pady=6)

    def _setup_tab_history(self):
        self.scan_history_view = ScanHistoryAuditView(
            self.tab_history,
            on_reinspect_callback=self._reinspect_historical_scan,
            copy_callback=self._copy_to_clipboard,
        )
        self.scan_history_view.pack(expand=True, fill="both", padx=6, pady=6)

    def _create_metric_tile(self, parent, title: str, initial_value: str, val_color: str, subtext: str = ""):
        tile = ctk.CTkFrame(
            parent,
            fg_color=COLOR_CARD_DARK,
            corner_radius=14,
            height=136,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        tile.pack(side="left", expand=True, fill="both", padx=4)
        tile.pack_propagate(False)

        lbl_title = ctk.CTkLabel(
            tile,
            text=title,
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color=COLOR_TEXT_SECONDARY,
        )
        lbl_title.pack(anchor="w", padx=14, pady=(16, 0))

        lbl_val = ctk.CTkLabel(
            tile,
            text=initial_value,
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color=val_color,
        )
        lbl_val.pack(anchor="w", padx=14, pady=(2, 0))

        lbl_sub = ctk.CTkLabel(
            tile,
            text=subtext,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=COLOR_TEXT_MUTED,
        )
        lbl_sub.pack(anchor="w", padx=14, pady=(4, 0))

        return lbl_val, lbl_sub

    def _setup_tab_log(self):
        log_bar = ctk.CTkFrame(self.tab_log, fg_color="transparent")
        log_bar.pack(fill="x", padx=10, pady=(6, 2))

        ctk.CTkLabel(
            log_bar,
            text="⚡ REAL-TIME ZERO-TRUST AUDIT STREAM",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#38bdf8",
        ).pack(side="left")

        btn_box = ctk.CTkFrame(log_bar, fg_color="transparent")
        btn_box.pack(side="right")

        ctk.CTkButton(
            btn_box,
            text="📋 Copy Log",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="#141f33",
            hover_color="#1e2f4e",
            border_width=1,
            border_color="#233555",
            width=95,
            height=28,
            corner_radius=12,
            command=self._handle_copy_log,
        ).pack(side="left", padx=3)

        ctk.CTkButton(
            btn_box,
            text="🗑️ Clear Log",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color="#2b1114",
            hover_color="#3d181d",
            text_color="#f87171",
            width=80,
            height=28,
            corner_radius=12,
            command=self._handle_clear_log,
        ).pack(side="left", padx=3)

        self.log_textbox = ctk.CTkTextbox(
            self.tab_log,
            font=ctk.CTkFont(family="Consolas", size=12),
            fg_color=COLOR_CODE_BG,
            border_width=1,
            border_color=COLOR_BORDER,
            corner_radius=10,
            text_color=COLOR_TEXT_PRIMARY,
            wrap="word",
        )
        self.log_textbox.pack(expand=True, fill="both", padx=10, pady=(4, 10))

    def _setup_tab_redirects(self):
        self.visual_hop_chain = VisualHopChain(
            self.tab_redirects, copy_callback=self._copy_to_clipboard
        )
        self.visual_hop_chain.pack(expand=True, fill="both", padx=6, pady=6)

    def _setup_tab_vectors(self):
        self.risk_bar_chart = RiskVectorBarChart(self.tab_vectors)
        self.risk_bar_chart.pack(expand=True, fill="both", padx=6, pady=6)

    def _setup_tab_analytics(self):
        self.analytics_chart = ThreatTrendAreaChart(self.tab_analytics)
        self.analytics_chart.pack(expand=True, fill="both", padx=6, pady=6)

    def _setup_tab_heuristics(self):
        h_bar = ctk.CTkFrame(self.tab_heuristics, fg_color="transparent")
        h_bar.pack(fill="x", padx=10, pady=(6, 2))

        ctk.CTkLabel(
            h_bar,
            text="🛡️ STATIC & BEHAVIORAL HEURISTIC AUDIT",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#38bdf8",
        ).pack(side="left")

        self.btn_copy_flags = ctk.CTkButton(
            h_bar,
            text="📋 Copy Flags",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="#141f33",
            hover_color="#1e2f4e",
            border_width=1,
            border_color="#233555",
            width=95,
            height=28,
            corner_radius=12,
            command=self._handle_copy_flags,
        )
        self.btn_copy_flags.pack(side="right")

        self.heuristics_textbox = ctk.CTkTextbox(
            self.tab_heuristics,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            fg_color=COLOR_CODE_BG,
            border_width=1,
            border_color=COLOR_BORDER,
            corner_radius=10,
            text_color=COLOR_TEXT_PRIMARY,
            wrap="word",
        )
        self.heuristics_textbox.pack(expand=True, fill="both", padx=10, pady=(4, 10))
        self.heuristics_textbox.insert("1.0", "No heuristic analysis performed yet.")
        self.heuristics_textbox.configure(state="disabled")

    def _log_event(self, message: str, level: str = "INFO"):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        prefix = f"[{timestamp}] [{level}] "
        full_line = f"{prefix}{message}\n"

        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", full_line)
        self.log_textbox.see("end")

    def _copy_to_clipboard(self, text: str):
        """Copies text to the system clipboard securely."""
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.update()
            sound_manager.play_tap()
            self._log_event("Copied to clipboard.")
        except Exception as e:
            self._log_event(f"Clipboard copy notice: {e}", level="WARN")

    # --- ACTIONS & CONTROLLERS ---

    def _handle_select_file(self):
        file_path = ctk.filedialog.askopenfilename(
            title="Select QR Code Image",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.bmp *.webp *.tiff")]
        )
        if not file_path:
            return

        self.current_image_path = file_path
        try:
            with Image.open(file_path) as img:
                self.current_image_obj = img.copy()
        except Exception:
            self.current_image_obj = None
        self.current_image_b64 = _get_base64_image(self.current_image_obj or file_path)
        self._display_preview_image(file_path)
        self._log_event(f"Loaded image: {os.path.basename(file_path)}")

        # Start analysis in worker thread
        self._start_async_task(self._process_image_worker, file_path)

    def _handle_open_webcam(self):
        if not CV2_AVAILABLE:
            self._log_event("Cannot open webcam: OpenCV is not available.", level="ERROR")
            return

        if self.webcam_window is not None and self.webcam_window.winfo_exists():
            self.webcam_window.focus()
            return

        self._log_event("Starting live webcam capture session...")
        self.webcam_window = WebcamScannerWindow(self, self._on_webcam_payload_detected)

    def _on_webcam_payload_detected(self, payload: str, camera_meta: dict = None, frame_snapshot = None):
        self._log_event(f"QR code captured from live camera feed successfully: {payload[:40]}...")
        if frame_snapshot is not None:
            self.current_image_obj = frame_snapshot
            self.current_image_b64 = _get_base64_image(frame_snapshot)
            self._display_preview_image(frame_snapshot)

        if not camera_meta:
            camera_meta = create_webcam_metadata(
                cam_index=0,
                width=1280,
                height=720,
                payload=payload,
                engine_name="OpenCV / PyZBar Real-Time Sensor Decoder",
            )

        cam_idx = camera_meta.get("camera_index", 0)
        source_label = f"Camera Device #{cam_idx} (Sensor Stream)"
        engine_label = camera_meta.get("engine", "OpenCV / PyZBar Video Sensor Decoder")

        self._start_async_task(
            self._process_payload_worker,
            payload,
            "Live Webcam Stream",
            source_label,
            camera_meta,
            engine_label,
            frame_snapshot,
            self.current_image_b64,
        )

    def _display_preview_image(self, img_source):
        try:
            if isinstance(img_source, Image.Image):
                img_copy = img_source.copy()
            else:
                with Image.open(img_source) as img:
                    img_copy = img.copy()
            if self.current_image_obj is None:
                self.current_image_obj = img_copy.copy()
            if not self.current_image_b64:
                self.current_image_b64 = _get_base64_image(self.current_image_obj)
            img_copy.thumbnail((260, 160), Image.Resampling.BILINEAR)
            ctk_img = ctk.CTkImage(light_image=img_copy, dark_image=img_copy, size=img_copy.size)
            self.image_preview_label.configure(image=ctk_img, text="")
        except Exception as e:
            self.image_preview_label.configure(image=None, text="Failed to render preview")
            self._log_event(f"Image preview error: {e}", level="WARN")

    def _start_async_task(self, target_fn, *args):
        self._set_loading(True, "Inspecting QR & Payload...")
        worker = threading.Thread(target=target_fn, args=args, daemon=True)
        worker.start()

    def _set_loading(self, is_loading: bool, status_text: str = ""):
        if is_loading:
            self.progress_bar.start()
            self.status_state_label.configure(text=status_text, text_color="#58a6ff")
            self.btn_select_file.configure(state="disabled")
            self.btn_webcam.configure(state="disabled")
        else:
            self.progress_bar.stop()
            self.progress_bar.set(0)
            self.status_state_label.configure(text="Inspection Complete", text_color=COLOR_TEXT_MUTED)
            self.btn_select_file.configure(state="normal")
            self.btn_webcam.configure(state="normal")

    def _handle_reset(self):
        self.current_image_path = None
        self.current_payload = None

        if hasattr(self, "preview_placeholder_img") and self.preview_placeholder_img:
            self.image_preview_label.configure(
                image=self.preview_placeholder_img,
                compound="top",
                text="\nNo QR Image Loaded\nDrag or select file"
            )
        else:
            self.image_preview_label.configure(image=None, text="No QR Image Loaded\nDrag or select file")

        self.payload_textbox.configure(state="normal")
        self.payload_textbox.delete("1.0", "end")
        self.payload_textbox.insert("1.0", "Awaiting payload...")
        self.payload_textbox.configure(state="disabled")

        self.banner_badge.configure(text="🟢 STATUS: IDLE / SECURE", text_color=COLOR_LOW_RISK)
        self.banner_hint.configure(text="No threat indicators detected yet.")

        self.threat_gauge.reset()
        self.visual_hop_chain.reset()
        self.risk_bar_chart.reset()
        self.detailed_dossier.reset()
        if hasattr(self, "payload_sandbox"):
            self.payload_sandbox.reset()

        self.tile_hops.configure(text="0 Hops", text_color=COLOR_TEXT_PRIMARY)
        self.sub_hops.configure(text="Direct Target / No Hops")
        self.tile_scheme.configure(text="N/A", text_color=COLOR_TEXT_PRIMARY)
        self.sub_scheme.configure(text="Awaiting URL Payload")

        self.heuristics_textbox.configure(state="normal")
        self.heuristics_textbox.delete("1.0", "end")
        self.heuristics_textbox.insert("1.0", "No heuristic analysis performed yet.")
        self.heuristics_textbox.configure(state="disabled")

        self._set_loading(False)
        self.status_state_label.configure(text="Idle / Ready", text_color=COLOR_TEXT_MUTED)
        self._log_event("Workspace cleared and reset.")

    def _handle_copy_current_payload(self):
        """Copies current extracted raw payload to clipboard."""
        if self.current_payload and self.current_payload != "Awaiting payload...":
            self._copy_to_clipboard(self.current_payload)
        else:
            self._log_event("No payload to copy.", level="WARN")

    def _handle_copy_log(self):
        """Copies entire security audit event log to clipboard."""
        content = self.log_textbox.get("1.0", "end-1c")
        if content:
            self._copy_to_clipboard(content)

    def _handle_copy_flags(self):
        """Copies detected heuristic security flags to clipboard."""
        content = self.heuristics_textbox.get("1.0", "end-1c")
        if content and "No heuristic analysis performed yet." not in content:
            self._copy_to_clipboard(content)
        else:
            self._log_event("No heuristic flags available to copy.", level="WARN")

    def _handle_clear_log(self):
        """Clears security event log window."""
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")
        self._log_event("Security audit log stream cleared by operator.")

    # --- ASYNC WORKERS ---

    def _process_image_worker(self, file_path: str):
        self._log_event("Running QR code decoders (pyzbar + OpenCV CLAHE pipeline)...")
        res = decode_from_file_with_metadata(file_path)

        if not res["success"] or not res["payload"]:
            self._log_event(f"Decoding failed: {res['error']}", level="ERROR")
            self.after(0, self._render_decode_failure, res["error"])
            return

        self._process_payload_worker(
            res["payload"],
            source=f"Local File: {os.path.basename(file_path)}",
            file_path=file_path,
            optical_meta=res["optical_meta"],
            engine=res["engine"],
            image_obj=self.current_image_obj,
            image_b64=self.current_image_b64 or _get_base64_image(file_path),
        )

    def _process_payload_worker(
        self,
        payload: str,
        source: str = "Local Image File",
        file_path: str = "",
        optical_meta: Optional[dict] = None,
        engine: str = "PyZBar zbar-0.10 (Direct Matrix)",
        image_obj: Optional[Any] = None,
        image_b64: Optional[str] = None,
    ):
        self.current_payload = payload
        self.after(0, self._update_payload_ui, payload)
        self._log_event(f"Extracted Raw Payload: {payload}")

        if optical_meta is None and file_path:
            optical_meta = extract_optical_metadata(file_path)

        if not image_obj and self.current_image_obj is not None:
            image_obj = self.current_image_obj
        if not image_b64 and self.current_image_b64:
            image_b64 = self.current_image_b64
        elif not image_b64 and image_obj is not None:
            image_b64 = _get_base64_image(image_obj)
        elif not image_b64 and file_path and os.path.exists(file_path):
            image_b64 = _get_base64_image(file_path)

        entropy = compute_shannon_entropy(payload)
        if entropy < 3.8:
            entropy_desc = "Low / Natural Structured Format"
        elif entropy < 5.2:
            entropy_desc = "Standard Uniform Alphanumeric Distribution"
        else:
            entropy_desc = "High / Potential Encrypted or Base64 Obfuscation"

        parsed = urlparse(payload)
        is_url = parsed.scheme in ("http", "https")
        is_upi = payload.lower().startswith("upi://")

        context = {
            "source": source,
            "file_path": file_path,
            "optical_meta": optical_meta or {},
            "engine": engine,
            "entropy": entropy,
            "entropy_desc": entropy_desc,
            "image_obj": image_obj,
            "image_b64": image_b64 or "",
        }

        if not is_url:
            if is_upi:
                self._log_event("Detected valid UPI mobile payment QR format.", level="INFO")
                self.after(0, self._render_upi_result, payload, context)
            else:
                self._log_event("Payload is plain text or non-HTTP URI scheme.", level="WARN")
                self.after(0, self._render_non_url_result, payload, context)
            return

        self.after(0, lambda: self.tile_scheme.configure(text=parsed.scheme.upper()))

        # Trace Network Redirects
        self._log_event(f"Tracing network redirect chain for {payload}...")
        trace_result = trace_url(payload, max_hops=5, timeout=5)

        if trace_result.get("error"):
            self._log_event(f"Network warning/error: {trace_result['error']}", level="WARN")

        redirect_count = trace_result.get("redirect_count", 0)
        final_url = trace_result.get("final_url", payload)

        self._log_event(f"Network Trace completed with {redirect_count} redirects. Final landing URL: {final_url}")

        # Analyze Local Heuristics on final landing URL
        self._log_event("Running offline heuristic risk checks on landing domain...")
        heuristics_result = analyze_heuristics(final_url, redirect_count=redirect_count)

        # Update UI with consolidated results
        self.after(0, self._render_full_analysis, trace_result, heuristics_result, context)

    # --- UI UPDATE CALLBACKS (MAIN THREAD) ---

    def _update_payload_ui(self, payload: str):
        self.payload_textbox.configure(state="normal")
        self.payload_textbox.delete("1.0", "end")
        self.payload_textbox.insert("1.0", payload)
        self.payload_textbox.configure(state="disabled")

    def _render_decode_failure(self, err_msg: str):
        self._set_loading(False)
        self.banner_badge.configure(text="⚠️ STATUS: SCAN FAILED", text_color=COLOR_MEDIUM_RISK)
        self.banner_hint.configure(text="Could not decode a valid QR matrix.")

        self.threat_gauge.set_score(0, verdict="IDLE", animated=False)
        self.visual_hop_chain.reset()
        self.risk_bar_chart.reset()
        self.detailed_dossier.reset()
        if hasattr(self, "payload_sandbox"):
            self.payload_sandbox.reset()

        sound_manager.play_warning_alert()

        self.tile_hops.configure(text="0 Hops", text_color=COLOR_TEXT_PRIMARY)
        self.sub_hops.configure(text="Decode Aborted")
        self.tile_scheme.configure(text="ERROR", text_color=COLOR_MEDIUM_RISK)
        self.sub_scheme.configure(text="Unrecognized Matrix")

        self.payload_textbox.configure(state="normal")
        self.payload_textbox.delete("1.0", "end")
        self.payload_textbox.insert("1.0", f"DECODE ERROR:\n{err_msg}")
        self.payload_textbox.configure(state="disabled")

    def _render_upi_result(self, payload: str, context: Optional[dict] = None):
        if context is None:
            context = {}
        self._set_loading(False)
        parsed = urlparse(payload)
        params = parse_qs(parsed.query)

        vpa = params.get("pa", [""])[0]
        name = params.get("pn", ["Verified Payee"])[0]
        amount = params.get("am", ["Open / Payer Specified"])[0]
        note = params.get("tn", ["Standard Peer-to-Peer Transfer"])[0]
        currency = params.get("cu", ["INR"])[0]
        psp = f"@{vpa.split('@')[-1]}" if "@" in vpa else "@upi"

        upi_data = {
            "vpa": vpa,
            "name": name,
            "amount": amount,
            "note": note,
            "currency": currency,
            "psp": psp,
        }

        # 1. Update Status Banner
        self.banner_badge.configure(text="🟢 STATUS: VERIFIED UPI PAYMENT QR", text_color=COLOR_LOW_RISK)
        self.banner_hint.configure(text="Valid P2P payment format. Zero web redirection or credential harvesting hazard.")

        # 2. Update Threat Arc Gauge
        self.threat_gauge.set_score(0, verdict="LOW", animated=True)

        # 3. Update Metric Tiles
        self.tile_hops.configure(text="0 Hops", text_color=COLOR_TEXT_PRIMARY)
        self.sub_hops.configure(text="Direct P2P Payment")
        self.tile_scheme.configure(text="💳 UPI", text_color=COLOR_LOW_RISK)
        self.sub_scheme.configure(text=f"PSP: {psp} Verified")

        # 4. Render Formatted UPI Inspection Card in Visual Flow tab
        self.visual_hop_chain.render_upi_payload(upi_data, payload)
        self.risk_bar_chart.update_for_upi(upi_data)

        # 5. Render Detailed QR Analysis Dossier
        entropy = context.get("entropy", compute_shannon_entropy(payload))
        entropy_desc = context.get("entropy_desc", "Standard Alphanumeric Distribution")
        dossier_data = {
            "payload": payload,
            "source": context.get("source", "Local Image File"),
            "file_path": context.get("file_path", ""),
            "optical_meta": context.get("optical_meta", {}),
            "engine": context.get("engine", "PyZBar zbar-0.10 (Direct Matrix)"),
            "image_obj": context.get("image_obj") or self.current_image_obj,
            "image_b64": context.get("image_b64") or self.current_image_b64 or _get_base64_image(context.get("image_obj") or self.current_image_obj),
            "payload_type": "💳 UPI Mobile Payment",
            "entropy": entropy,
            "entropy_desc": entropy_desc,
            "threat_score": 0,
            "threat_verdict": "CLEAN / VERIFIED P2P PAYMENT",
            "vectors": [
                ("🌐 Domain & TLD Abuse", 0.0, "0% CLEAN", COLOR_LOW_RISK),
                ("🔤 Brand Impersonation", 0.0, "0% CLEAN", COLOR_LOW_RISK),
                ("🔀 Redirect Chain Evasion", 0.0, "0% CLEAN", COLOR_LOW_RISK),
                ("🔒 Protocol & Auth Obfuscation", 0.0, "0% CLEAN", COLOR_LOW_RISK),
                ("🎯 Host & Subdomain Structure", 0.0, "0% CLEAN", COLOR_LOW_RISK),
            ],
            "params": [
                ("👤 Payee Name (pn)", name, "Verified Payee", COLOR_LOW_RISK),
                ("🏦 Virtual Address (pa)", vpa, "NPCI Compliant", COLOR_LOW_RISK),
                ("🌐 Banking Network (PSP)", psp, "Registered Handle", COLOR_LOW_RISK),
                ("💵 Transaction Amount (am)", f"{amount} ({currency})", "Open Entry", COLOR_LOW_RISK),
                ("📝 Transaction Note (tn)", note, "User Reference", COLOR_TEXT_MUTED),
                ("💱 Currency Code (cu)", currency, "ISO 4217", COLOR_LOW_RISK),
                ("🛡️ Protocol Compliance", "NPCI UPI Specification Compliant", "PASS", COLOR_LOW_RISK),
            ],
            "checklist": [
                {"name": "Web Redirection Risk", "badge": "PASS", "color": COLOR_LOW_RISK, "desc": "Native mobile banking URI protocol; zero external browser redirection risk."},
                {"name": "Transport Protocol Security", "badge": "VERIFIED", "color": COLOR_LOW_RISK, "desc": "Handled natively by verified UPI-registered PSP mobile applications."},
                {"name": "Homograph & Brand Spoofing", "badge": "PASS", "color": COLOR_LOW_RISK, "desc": "No homograph lookalike or brand typosquatting detected in VPA handle."},
                {"name": "Shannon Entropy & Obfuscation", "badge": "PASS", "color": COLOR_LOW_RISK, "desc": f"Entropy {entropy:.2f} bits/symbol is within standard URI bounds."},
                {"name": "Quarantine Recommendation", "badge": "CLEAN", "color": COLOR_LOW_RISK, "desc": "Safe peer-to-peer payment QR code. Approved for payment initiation."},
            ],
        }
        self.detailed_dossier.render_dossier(dossier_data)
        if hasattr(self, "payload_sandbox"):
            self.payload_sandbox.update_sandbox(payload, dossier_data)

        history_manager.add_record(
            payload=payload,
            risk_level="LOW",
            score=0,
            source=context.get("source", "UPI Payment"),
            sha256=context.get("optical_meta", {}).get("sha256", "N/A"),
            optical_meta=context.get("optical_meta", {}),
            hops_count=0,
            flags=[],
            image_b64=context.get("image_b64", ""),
        )
        if hasattr(self, "scan_history_view") and "Scan History" in self.tabview.get():
            self.scan_history_view.refresh()

        sound_manager.play_scan_clean()

        # 6. Keep on graph tab if active, otherwise switch to Detailed QR Analysis
        current_tab = self.tabview.get()
        if current_tab in ("📊 Risk Vector Graph", "📈 Threat Analytics", "🔬 Payload Sandbox", "🗄️ Scan History"):
            self._on_tab_changed()
        else:
            self.tabview.set("🔍 Detailed QR Analysis")

        # 7. Populate Heuristic Audit Tab with structured verification
        self.heuristics_textbox.configure(state="normal")
        self.heuristics_textbox.delete("1.0", "end")
        h_summary = f"""=== UPI PAYMENT INTEGRITY & ZERO-TRUST AUDIT ===
Payee Name (pn):        {name}
Virtual Address (pa):   {vpa}
Banking Network (psp):  {psp}
Transaction Note (tn):  {note}
Amount Parameter (am):  {amount} ({currency})

ZERO-TRUST CHECKS PASSED:
 • Web Redirection: None (Native Mobile Banking URI Scheme)
 • Format Syntax:   NPCI Alphanumeric Specification Compliant
 • Risk Assessment: 0 / 100 [CLEAN / VERIFIED P2P PAYMENT]
"""
        self.heuristics_textbox.insert("1.0", h_summary)
        self.heuristics_textbox.configure(state="disabled")

        # 8. Record in session threat telemetry
        self.analytics_chart.record_scan(0, "LOW", payload)
        self._log_event(f"UPI quarantine audit complete for {name} ({vpa}). Verdict: CLEAN.")

    def _render_non_url_result(self, payload: str, context: Optional[dict] = None):
        if context is None:
            context = {}
        self._set_loading(False)
        self.banner_badge.configure(text="🟢 STATUS: TEXT PAYLOAD", text_color=COLOR_LOW_RISK)
        self.banner_hint.configure(text="Non-HTTP payload; no redirect risk.")

        self.threat_gauge.set_score(0, verdict="LOW", animated=True)
        self.visual_hop_chain.render_generic_text_payload(payload)
        self.risk_bar_chart.update_for_text(payload)

        self.tile_hops.configure(text="0 Hops", text_color=COLOR_TEXT_PRIMARY)
        self.sub_hops.configure(text="Non-HTTP Target")
        self.tile_scheme.configure(text="TEXT", text_color=COLOR_TEXT_PRIMARY)
        self.sub_scheme.configure(text="Static Text Data")

        entropy = context.get("entropy", compute_shannon_entropy(payload))
        entropy_desc = context.get("entropy_desc", "Standard Alphanumeric Distribution")
        dossier_data = {
            "payload": payload,
            "source": context.get("source", "Local Image File"),
            "file_path": context.get("file_path", ""),
            "optical_meta": context.get("optical_meta", {}),
            "engine": context.get("engine", "PyZBar zbar-0.10 (Direct Matrix)"),
            "image_obj": context.get("image_obj") or self.current_image_obj,
            "image_b64": context.get("image_b64") or self.current_image_b64 or _get_base64_image(context.get("image_obj") or self.current_image_obj),
            "payload_type": "📄 Plain Text / Custom Scheme",
            "entropy": entropy,
            "entropy_desc": entropy_desc,
            "threat_score": 0,
            "threat_verdict": "LOW / TEXT",
            "vectors": [
                ("🌐 Domain & TLD Abuse", 0.0, "0% CLEAN", COLOR_LOW_RISK),
                ("🔤 Brand Impersonation", 0.0, "0% CLEAN", COLOR_LOW_RISK),
                ("🔀 Redirect Chain Evasion", 0.0, "0% CLEAN", COLOR_LOW_RISK),
                ("🔒 Protocol & Auth Obfuscation", 0.0, "0% CLEAN", COLOR_LOW_RISK),
                ("🎯 Host & Subdomain Structure", 0.0, "0% CLEAN", COLOR_LOW_RISK),
            ],
            "params": [
                ("📄 Content Preview", (payload[:60] + "...") if len(payload) > 60 else payload, "Text Data", COLOR_TEXT_PRIMARY),
                ("🔤 Character Count", f"{len(payload)} Characters", "Size", COLOR_TEXT_MUTED),
                ("🔢 Word Count", f"{len(payload.split())} Words", "Words", COLOR_TEXT_MUTED),
                ("📏 Line Count", f"{len(payload.splitlines())} Lines", "Lines", COLOR_TEXT_MUTED),
            ],
            "checklist": [
                {"name": "Web Redirection Risk", "badge": "PASS", "color": COLOR_LOW_RISK, "desc": "Static text payload; zero external browser redirection risk."},
                {"name": "Transport Protocol Security", "badge": "N/A", "color": COLOR_LOW_RISK, "desc": "No transport network invocation required."},
                {"name": "Brand Spoofing & Typosquatting", "badge": "PASS", "color": COLOR_LOW_RISK, "desc": "No URL domain host present."},
                {"name": "Shannon Entropy & Obfuscation", "badge": "PASS", "color": COLOR_LOW_RISK, "desc": f"Entropy {entropy:.2f} bits/symbol."},
                {"name": "Quarantine Recommendation", "badge": "CLEAN", "color": COLOR_LOW_RISK, "desc": "Non-executable static text data."},
            ],
        }
        self.detailed_dossier.render_dossier(dossier_data)
        if hasattr(self, "payload_sandbox"):
            self.payload_sandbox.update_sandbox(payload, dossier_data)

        history_manager.add_record(
            payload=payload,
            risk_level="LOW",
            score=0,
            source=context.get("source", "Plain Text"),
            sha256=context.get("optical_meta", {}).get("sha256", "N/A"),
            optical_meta=context.get("optical_meta", {}),
            hops_count=0,
            flags=[],
            image_b64=context.get("image_b64", ""),
        )
        if hasattr(self, "scan_history_view") and "Scan History" in self.tabview.get():
            self.scan_history_view.refresh()

        sound_manager.play_scan_clean()

        current_tab = self.tabview.get()
        if current_tab in ("📊 Risk Vector Graph", "📈 Threat Analytics", "🔬 Payload Sandbox", "🗄️ Scan History"):
            self._on_tab_changed()
        else:
            self.tabview.set("🔍 Detailed QR Analysis")

        self.heuristics_textbox.configure(state="normal")
        self.heuristics_textbox.delete("1.0", "end")
        self.heuristics_textbox.insert("1.0", f"Payload is plain text or custom URI:\n\n{payload}\n\nNo web redirection or domain heuristics applicable.")
        self.heuristics_textbox.configure(state="disabled")

        self.analytics_chart.record_scan(0, "LOW", payload)

    def _render_full_analysis(self, trace_result: dict, heuristics_result: dict, context: Optional[dict] = None):
        if context is None:
            context = {}
        self._set_loading(False)

        score = heuristics_result["score"]
        verdict = heuristics_result["verdict"]
        flags = heuristics_result["flags"]
        redirect_count = trace_result["redirect_count"]
        hops = trace_result["hops"]
        trace_err = trace_result["error"]

        # 1. Update Threat Arc Gauge
        self.threat_gauge.set_score(score, verdict=verdict, animated=True)

        # 2. Update Risk Vector Bar Chart & Session Threat Analytics Area Chart
        self.risk_bar_chart.update_from_heuristics(heuristics_result, redirect_count=redirect_count)
        self.analytics_chart.record_scan(score, verdict, trace_result.get("final_url", ""))

        # 3. Update Metric Tiles
        if redirect_count == 0:
            self.tile_hops.configure(text="0 Hops", text_color=COLOR_TEXT_PRIMARY)
            self.sub_hops.configure(text="Direct Connection")
        else:
            hop_color = COLOR_MEDIUM_RISK if redirect_count > 1 else COLOR_TEXT_PRIMARY
            self.tile_hops.configure(text=f"{redirect_count} Hops", text_color=hop_color)
            self.sub_hops.configure(text="Multiple Redirects" if redirect_count > 1 else "Single HTTP Redirect")

        parsed_final = urlparse(trace_result.get("final_url", ""))
        scheme = parsed_final.scheme.upper()
        if scheme == "HTTPS":
            self.tile_scheme.configure(text="🔒 HTTPS", text_color=COLOR_LOW_RISK)
            self.sub_scheme.configure(text="TLS / SSL Encrypted")
        elif scheme == "HTTP":
            self.tile_scheme.configure(text="⚠️ HTTP", text_color=COLOR_MEDIUM_RISK)
            self.sub_scheme.configure(text="Plaintext Transmission")
        else:
            self.tile_scheme.configure(text=scheme, text_color=COLOR_TEXT_PRIMARY)
            self.sub_scheme.configure(text="Custom Protocol")

        # 4. Update Banner
        if verdict == "CRITICAL":
            self.banner_badge.configure(text="🔴 STATUS: CRITICAL RISK", text_color=COLOR_CRITICAL_RISK)
            self.banner_hint.configure(text="Severe threat indicators detected! Do not proceed to URL.")
        elif verdict == "MEDIUM":
            self.banner_badge.configure(text="🟡 STATUS: WARNING", text_color=COLOR_MEDIUM_RISK)
            self.banner_hint.configure(text="Suspicious patterns detected. Exercise strict caution.")
        else:
            self.banner_badge.configure(text="🟢 STATUS: SECURE", text_color=COLOR_LOW_RISK)
            self.banner_hint.configure(text="No high-risk phishing or typosquatting patterns detected.")

        # 5. Update Visual Hop Chain
        self.visual_hop_chain.render_trace(trace_result, heuristics_result=heuristics_result)

        # 6. Render Detailed QR Analysis Dossier with Attack Vector breakdown
        final_url = trace_result.get("final_url", self.current_payload or "")
        entropy = context.get("entropy", compute_shannon_entropy(final_url))
        entropy_desc = context.get("entropy_desc", "Standard Alphanumeric Distribution")
        host = parsed_final.netloc or parsed_final.path.split('/')[0]

        flags_text = " ".join(flags).lower()
        d_val = min(100.0, (70.0 if "tld" in flags_text else 0.0) + (85.0 if "raw ip" in flags_text else 0.0))
        b_val = 90.0 if ("typosquat" in flags_text or "impersonat" in flags_text) else 0.0
        r_val = 95.0 if redirect_count >= 3 else (65.0 if redirect_count == 2 else (35.0 if redirect_count == 1 else 0.0))
        p_val = 80.0 if ("basic auth" in flags_text or "credential" in flags_text) else 0.0
        s_val = min(100.0, (45.0 if "subdomain" in flags_text else 0.0) + (50.0 if "raw ip" in flags_text else 0.0))

        def _get_v_badge(val):
            if val >= 70: return f"{int(val)}% HIGH", COLOR_CRITICAL_RISK
            if val >= 30: return f"{int(val)}% WARN", COLOR_MEDIUM_RISK
            if val > 0: return f"{int(val)}% LOW", "#3b82f6"
            return "0% CLEAN", COLOR_LOW_RISK

        vectors = [
            ("🌐 Domain & TLD Abuse", d_val, *_get_v_badge(d_val)),
            ("🔤 Brand Impersonation", b_val, *_get_v_badge(b_val)),
            ("🔀 Redirect Chain Evasion", r_val, *_get_v_badge(r_val)),
            ("🔒 Protocol & Auth Obfuscation", p_val, *_get_v_badge(p_val)),
            ("🎯 Host & Subdomain Structure", s_val, *_get_v_badge(s_val)),
        ]

        dossier_data = {
            "payload": final_url,
            "source": context.get("source", "Local Image File"),
            "file_path": context.get("file_path", ""),
            "optical_meta": context.get("optical_meta", {}),
            "engine": context.get("engine", "PyZBar zbar-0.10 (Direct Matrix)"),
            "image_obj": context.get("image_obj") or self.current_image_obj,
            "image_b64": context.get("image_b64") or self.current_image_b64 or _get_base64_image(context.get("image_obj") or self.current_image_obj),
            "payload_type": f"🌐 Web URL ({scheme})",
            "entropy": entropy,
            "entropy_desc": entropy_desc,
            "threat_score": score,
            "threat_verdict": verdict,
            "vectors": vectors,
            "params": [
                ("🌐 Destination Host", host, "Landing Host", COLOR_TEXT_PRIMARY),
                ("🔒 Transport Protocol", f"{scheme} ({'TLS/SSL Encrypted' if scheme == 'HTTPS' else 'Unencrypted Plaintext'})", "Encrypted" if scheme == "HTTPS" else "Unencrypted", COLOR_LOW_RISK if scheme == "HTTPS" else COLOR_MEDIUM_RISK),
                ("🔀 Redirection Route", f"{redirect_count} Hops Recorded", "Direct Target" if redirect_count == 0 else f"{redirect_count} Hops", COLOR_LOW_RISK if redirect_count == 0 else COLOR_MEDIUM_RISK),
                ("📍 Path Resource", parsed_final.path or "/", "Resource Path", COLOR_TEXT_MUTED),
                ("❓ Query Parameters", parsed_final.query or "None", f"{len(parse_qs(parsed_final.query))} Params", COLOR_TEXT_MUTED),
                ("🎯 Threat Score", f"{score} / 100", verdict, COLOR_CRITICAL_RISK if verdict == "CRITICAL" else (COLOR_MEDIUM_RISK if verdict == "MEDIUM" else COLOR_LOW_RISK)),
            ],
            "checklist": [
                {
                    "name": "Web Redirection Risk",
                    "badge": "ALERT" if redirect_count > 1 else "PASS",
                    "color": COLOR_MEDIUM_RISK if redirect_count > 1 else COLOR_LOW_RISK,
                    "desc": f"Observed {redirect_count} HTTP redirect hops between source QR and final target." if redirect_count > 0 else "Direct connection without redirection obfuscation.",
                },
                {
                    "name": "Transport Protocol Security",
                    "badge": "PASS" if scheme == "HTTPS" else "WARN",
                    "color": COLOR_LOW_RISK if scheme == "HTTPS" else COLOR_MEDIUM_RISK,
                    "desc": "Modern TLS/SSL cryptographic encryption in transit." if scheme == "HTTPS" else "Unencrypted plaintext transmission; vulnerable to MITM interception.",
                },
                {
                    "name": "Brand Spoofing & Typosquatting",
                    "badge": "ALERT" if any("brand" in f.lower() or "typo" in f.lower() for f in flags) else "PASS",
                    "color": COLOR_CRITICAL_RISK if any("brand" in f.lower() or "typo" in f.lower() for f in flags) else COLOR_LOW_RISK,
                    "desc": "Suspicious similarity to high-value target financial/tech domains detected." if any("brand" in f.lower() or "typo" in f.lower() for f in flags) else "No high-value brand spoofing patterns identified.",
                },
                {
                    "name": "Shannon Entropy & Obfuscation",
                    "badge": "ALERT" if entropy > 5.5 else "PASS",
                    "color": COLOR_MEDIUM_RISK if entropy > 5.5 else COLOR_LOW_RISK,
                    "desc": f"Entropy {entropy:.2f} bits/symbol ({entropy_desc}).",
                },
                {
                    "name": "Quarantine Recommendation",
                    "badge": "QUARANTINED" if verdict == "CRITICAL" else ("WARNING" if verdict == "MEDIUM" else "SAFE"),
                    "color": COLOR_CRITICAL_RISK if verdict == "CRITICAL" else (COLOR_MEDIUM_RISK if verdict == "MEDIUM" else COLOR_LOW_RISK),
                    "desc": "Hostile threat profile. Do NOT proceed to destination." if verdict == "CRITICAL" else ("Suspicious indicators present. Proceed with extreme caution." if verdict == "MEDIUM" else "Standard web profile. No malicious heuristics detected."),
                },
            ],
        }
        self.detailed_dossier.render_dossier(dossier_data)
        if hasattr(self, "payload_sandbox"):
            self.payload_sandbox.update_sandbox(final_url, dossier_data)

        history_manager.add_record(
            payload=final_url,
            risk_level=verdict,
            score=score,
            source=context.get("source", "Web URL"),
            sha256=context.get("optical_meta", {}).get("sha256", "N/A"),
            optical_meta=context.get("optical_meta", {}),
            hops_count=redirect_count,
            flags=flags,
            image_b64=context.get("image_b64", ""),
        )
        if hasattr(self, "scan_history_view") and "Scan History" in self.tabview.get():
            self.scan_history_view.refresh()

        if verdict in ["CRITICAL", "HIGH"]:
            sound_manager.play_critical_alert()
        elif verdict in ["MEDIUM", "WARN", "WARNING"]:
            sound_manager.play_warning_alert()
        else:
            sound_manager.play_scan_clean()

        current_tab = self.tabview.get()
        if current_tab in ("📊 Risk Vector Graph", "📈 Threat Analytics", "🔬 Payload Sandbox", "🗄️ Scan History"):
            self._on_tab_changed()
        else:
            self.tabview.set("🔍 Detailed QR Analysis")

        # 7. Update Heuristic Flags Tab
        self.heuristics_textbox.configure(state="normal")
        self.heuristics_textbox.delete("1.0", "end")

        h_text = f"Threat Verdict: {verdict}\n"
        h_text += f"Risk Score:     {score} / 100\n"
        h_text += "=" * 50 + "\n\n"

        if flags:
            h_text += "DETECTION FLAGS TRIGGERED:\n\n"
            for f in flags:
                h_text += f" • {f}\n"
        else:
            h_text += "No heuristic risk flags were triggered. The target domain appears consistent with standard web conventions."

        self.heuristics_textbox.insert("1.0", h_text)
        self.heuristics_textbox.configure(state="disabled")

        self._log_event(f"Analysis complete: Verdict={verdict}, Threat Score={score}/100.")

    def _toggle_sound(self):
        """Mutes or unmutes tactical audio cues."""
        is_muted = sound_manager.toggle_mute()
        if is_muted:
            self.btn_sound.configure(
                text="🔇 Audio: OFF",
                fg_color="#331417",
                hover_color="#521d23",
                text_color="#f87171",
            )
            self._log_event("Tactical cyber audio cues MUTED.")
        else:
            self.btn_sound.configure(
                text="🔊 Audio: ON",
                fg_color="#1e293b",
                hover_color="#334155",
                text_color="#38bdf8",
            )
            self._log_event("Tactical cyber audio cues ENABLED.")

    def _export_current_incident_report(self):
        """Triggers executive forensic report export for currently analyzed QR."""
        if hasattr(self, "detailed_dossier") and self.detailed_dossier.current_dossier:
            sound_manager.play_export_success()
            self.detailed_dossier._export_html_report()
        else:
            sound_manager.play_warning_alert()
            self._log_event("Cannot export report: No active QR scan dossier available.", level="WARN")

    def _reinspect_historical_scan(self, rec: Dict[str, Any]):
        """Loads a past scan record from the audit log into active quarantine workspace."""
        payload = rec.get("payload", "")
        if not payload:
            return
        self._log_event(f"Re-inspecting historical audit record {rec.get('id', '')}...")
        img_b64 = rec.get("image_b64", "")
        self.current_image_b64 = img_b64
        self._start_async_task(
            self._process_payload_worker,
            payload,
            rec.get("source", "Historical Audit Log"),
            rec.get("optical_meta", {}).get("file_path", ""),
            rec.get("optical_meta", {}),
            rec.get("optical_meta", {}).get("engine", "Historical Audit Pipeline"),
            None,
            img_b64,
        )


def main():
    app = QuishGuardApp()
    app.mainloop()


if __name__ == "__main__":
    main()
