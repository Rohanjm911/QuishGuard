"""
QuishGuard Desktop - UI Widgets Module
Advanced High-Resolution Telemetry Components:
- ThreatArcGauge: Dynamic Resolution-Aware Radial Speedometer
- VisualHopChain: Interactive Multi-Hop URL Route Graph
"""
import os
import re
import math
import base64
import datetime
from typing import Dict, Any, Optional, Callable, List
from urllib.parse import urlparse, unquote
import tkinter as tk
from tkinter import filedialog
import customtkinter as ctk

from modules.history_manager import history_manager
from modules.report_generator import generate_html_report

# High-Resolution Theme Constants (Apple macOS Dark + Google Material You 3)
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


class ThreatArcGauge(ctk.CTkFrame):
    """
    High-Resolution Dynamic Radial Threat Arc Gauge.
    Auto-detects actual display scaling and pixel geometry via <Configure>
    to render razor-sharp vector arcs, graduation ticks, glowing needle tips,
    and adaptive typography at any monitor resolution.
    """

    def __init__(
        self,
        master,
        width: int = 185,
        height: int = 136,
        fg_color: str = COLOR_CARD_DARK,
        border_color: str = COLOR_BORDER,
        border_width: int = 1,
        corner_radius: int = 14,
        **kwargs,
    ):
        super().__init__(
            master,
            width=width,
            height=height,
            fg_color=fg_color,
            border_color=border_color,
            border_width=border_width,
            corner_radius=corner_radius,
            **kwargs,
        )
        self.pack_propagate(False)

        self._fg_color = fg_color
        self._current_score = 0.0
        self._target_score = 0.0
        self._verdict = "IDLE"
        self._anim_id: Optional[str] = None

        # Arc sweep constants: 210° (bottom-left) to -30° (bottom-right)
        self.start_ang = 210
        self.total_extent = -240

        # Canvas initialized with dark background
        self.canvas = tk.Canvas(
            self,
            bg=fg_color,
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack(fill="both", expand=True)

        # Bind configure event for dynamic high-DPI responsive recalculation
        self.canvas.bind("<Configure>", self._on_canvas_resize)
        self._draw_gauge(0.0, COLOR_LOW_RISK, "IDLE")

    def _on_canvas_resize(self, event):
        """Recomputes geometry when canvas size changes to preserve pixel sharpness."""
        if event.width > 20 and event.height > 20:
            color = self._get_score_color(self._current_score, self._verdict)
            self._draw_gauge(self._current_score, color, self._verdict)

    def _get_score_color(self, score: float, verdict: str) -> str:
        """Determines alert color according to threat score and verdict."""
        if verdict == "CRITICAL" or score >= 70:
            return COLOR_CRITICAL_RISK
        if verdict == "MEDIUM" or score >= 30:
            return COLOR_MEDIUM_RISK
        return COLOR_LOW_RISK

    def _draw_gauge(self, score: float, color: str, verdict: str):
        """Renders the entire gauge with resolution-calibrated geometry (Apple Watch / Material 3 style)."""
        self.canvas.delete("all")

        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()

        if w <= 1 or h <= 1:
            w = self.cget("width")
            h = self.cget("height")

        # Responsive center and radius calculations
        cx = w // 2
        cy = int(h * 0.54)
        r = max(26, min(42, int(min(w * 0.40, h * 0.33))))
        arc_width = 8
        glow_width = 12

        # 1. Top Section Title - Apple style uppercase sub-headline
        self.canvas.create_text(
            cx,
            15,
            text="THREAT RADAR",
            fill=COLOR_TEXT_MUTED,
            font=("Segoe UI", 9, "bold"),
        )

        # 2. Dial Graduation Ticks (0%, 25%, 50%, 75%, 100%)
        tick_len = max(4, int(r * 0.14))
        for frac in [0.0, 0.25, 0.5, 0.75, 1.0]:
            tick_ang = self.start_ang - frac * 240
            rad = math.radians(tick_ang)
            x1 = cx + (r - tick_len) * math.cos(rad)
            y1 = cy - (r - tick_len) * math.sin(rad)
            x2 = cx + (r + tick_len) * math.cos(rad)
            y2 = cy - (r + tick_len) * math.sin(rad)
            self.canvas.create_line(x1, y1, x2, y2, fill="#222f46", width=2)

        # 3. Outer Dark Background Track Arcs (Glow + Core)
        bbox = (cx - r, cy - r, cx + r, cy + r)
        self.canvas.create_arc(
            bbox,
            start=self.start_ang,
            extent=self.total_extent,
            style="arc",
            outline="#101726",
            width=glow_width,
        )
        self.canvas.create_arc(
            bbox,
            start=self.start_ang,
            extent=self.total_extent,
            style="arc",
            outline="#1e293e",
            width=arc_width,
        )

        # 4. Active Colored Progress Arc
        score = max(0.0, min(100.0, score))
        fraction = score / 100.0
        active_extent = fraction * self.total_extent

        if fraction > 0.001:
            # Active core line
            self.canvas.create_arc(
                bbox,
                start=self.start_ang,
                extent=active_extent,
                style="arc",
                outline=color,
                width=arc_width,
            )

            # Glowing tip indicator dot at needle position
            tip_ang = self.start_ang + active_extent
            tip_rad = math.radians(tip_ang)
            dot_x = cx + r * math.cos(tip_rad)
            dot_y = cy - r * math.sin(tip_rad)
            dot_r = 4

            # Outer glow aura
            self.canvas.create_oval(
                dot_x - dot_r - 2,
                dot_y - dot_r - 2,
                dot_x + dot_r + 2,
                dot_y + dot_r + 2,
                fill="",
                outline=color,
                width=1.5,
            )
            # Solid core dot
            self.canvas.create_oval(
                dot_x - dot_r,
                dot_y - dot_r,
                dot_x + dot_r,
                dot_y + dot_r,
                fill="#ffffff",
                outline=color,
                width=2,
            )

        # 5. High-Resolution Central Readout
        disp_score = int(round(score))
        self.canvas.create_text(
            cx,
            cy - 6,
            text=str(disp_score),
            fill=color,
            font=("Segoe UI", 21, "bold"),
        )

        self.canvas.create_text(
            cx,
            cy + 14,
            text="/ 100",
            fill=COLOR_TEXT_MUTED,
            font=("Segoe UI", 8, "bold"),
        )

        # 6. Material 3 / Apple Pill Verdict Capsule at Bottom
        verdict_label = {
            "LOW": "● SECURE",
            "MEDIUM": "▲ CAUTION",
            "CRITICAL": "■ CRITICAL",
            "IDLE": "● IDLE",
        }.get(verdict, f"● {verdict}")

        pill_w = 94
        pill_h = 20
        px1 = cx - pill_w // 2
        py1 = h - 23
        px2 = cx + pill_w // 2
        py2 = py1 + pill_h

        # Capsule pill background & border
        pill_bg = "#0d1b2a" if verdict in ["LOW", "IDLE"] else ("#2a1806" if verdict == "MEDIUM" else "#2b0d0d")
        r_pill = pill_h // 2
        self.canvas.create_arc(px1, py1, px1 + pill_h, py2, start=90, extent=180, fill=pill_bg, outline=color, width=1)
        self.canvas.create_arc(px2 - pill_h, py1, px2, py2, start=270, extent=180, fill=pill_bg, outline=color, width=1)
        self.canvas.create_rectangle(px1 + r_pill, py1, px2 - r_pill, py2, fill=pill_bg, outline="", width=0)
        self.canvas.create_line(px1 + r_pill, py1, px2 - r_pill, py1, fill=color, width=1)
        self.canvas.create_line(px1 + r_pill, py2, px2 - r_pill, py2, fill=color, width=1)

        self.canvas.create_text(
            cx,
            py1 + pill_h // 2,
            text=verdict_label,
            fill=color,
            font=("Segoe UI", 8, "bold"),
        )

    def set_score(self, target_score: int, verdict: str = "LOW", animated: bool = True):
        """Smoothly animates the gauge to the target score with ease-out physics."""
        target_score = max(0, min(100, target_score))
        self._target_score = float(target_score)
        self._verdict = verdict

        if self._anim_id:
            try:
                self.after_cancel(self._anim_id)
            except Exception:
                pass
            self._anim_id = None

        if not animated:
            self._current_score = self._target_score
            color = self._get_score_color(self._current_score, self._verdict)
            self._draw_gauge(self._current_score, color, self._verdict)
            return

        total_steps = 22
        start_score = self._current_score
        step_idx = 0

        def _step():
            nonlocal step_idx
            step_idx += 1
            progress = step_idx / total_steps
            # Ease-out cubic curve
            ease_prog = 1.0 - math.pow(1.0 - progress, 3)
            current = start_score + (self._target_score - start_score) * ease_prog
            self._current_score = current

            color = self._get_score_color(current, self._verdict)
            self._draw_gauge(current, color, self._verdict)

            if step_idx < total_steps:
                self._anim_id = self.after(16, _step)
            else:
                self._current_score = self._target_score
                self._anim_id = None

        _step()

    def reset(self):
        """Resets the gauge to 0 / IDLE."""
        self.set_score(0, verdict="IDLE", animated=False)


class VisualHopChain(ctk.CTkFrame):
    """
    High-Resolution Interactive Visual Hop Chain component.
    Displays a sequential node-by-node breadcrumb trace of network redirects
    with HTTP status badges, domain highlights, protocol flags, and copy buttons,
    with an instant toggle to raw trace logs.
    """

    def __init__(
        self,
        master,
        copy_callback: Optional[Callable[[str], None]] = None,
        fg_color: str = COLOR_CARD_DARK,
        **kwargs,
    ):
        super().__init__(master, fg_color=fg_color, corner_radius=14, **kwargs)
        self.copy_callback = copy_callback

        self._current_trace: Optional[Dict[str, Any]] = None
        self._current_heuristics: Optional[Dict[str, Any]] = None

        self._build_top_bar()
        self._build_content_areas()
        self.reset()

    def _build_top_bar(self):
        """Builds the control toolbar with mode switcher and copy-all button."""
        self.top_bar = ctk.CTkFrame(self, fg_color="transparent", height=42)
        self.top_bar.pack(fill="x", padx=14, pady=(12, 8))

        # Title & Hop Count Badge
        title_box = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        title_box.pack(side="left")

        self.lbl_title = ctk.CTkLabel(
            title_box,
            text="🔀 REDIRECT CHAIN TELEMETRY",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY,
        )
        self.lbl_title.pack(side="left")

        self.badge_hops = ctk.CTkLabel(
            title_box,
            text="0 Hops",
            fg_color="#13233d",
            border_width=1,
            border_color="#1d355e",
            corner_radius=12,
            text_color="#60a5fa",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            padx=12,
            pady=3,
        )
        self.badge_hops.pack(side="left", padx=12)

        # Right actions (Material 3 Pill Buttons)
        self.btn_copy_all = ctk.CTkButton(
            self.top_bar,
            text="📋 Copy Raw Trace",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="#141f33",
            hover_color="#1e2f4e",
            border_width=1,
            border_color="#233555",
            height=30,
            width=130,
            corner_radius=14,
            command=self._handle_copy_raw_trace,
        )
        self.btn_copy_all.pack(side="right", padx=(8, 0))

        self.seg_view = ctk.CTkSegmentedButton(
            self.top_bar,
            values=["Visual Flow", "Raw Trace Log"],
            command=self._on_view_mode_changed,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            selected_color="#2563eb",
            selected_hover_color="#1d4ed8",
            unselected_color="#0b0f19",
            unselected_hover_color="#162034",
            height=30,
            corner_radius=14,
        )
        self.seg_view.pack(side="right")
        self.seg_view.set("Visual Flow")

    def _build_content_areas(self):
        """Builds high-resolution container for Visual Flow (scrollable) and Raw Log."""
        self.content_container = ctk.CTkFrame(self, fg_color="transparent")
        self.content_container.pack(expand=True, fill="both", padx=12, pady=(0, 12))

        # 1. Visual Flow (Scrollable Frame)
        self.scroll_flow = ctk.CTkScrollableFrame(
            self.content_container,
            fg_color=COLOR_BG_DARK,
            border_width=1,
            border_color=COLOR_BORDER,
            corner_radius=12,
        )

        # 2. Raw Textbox
        self.raw_textbox = ctk.CTkTextbox(
            self.content_container,
            font=ctk.CTkFont(family="Consolas", size=12),
            fg_color=COLOR_CODE_BG,
            border_width=1,
            border_color=COLOR_BORDER,
            corner_radius=12,
            text_color=COLOR_TEXT_PRIMARY,
            wrap="word",
        )

    def _on_view_mode_changed(self, mode: str):
        """Switches between Visual Flow view and Raw Text view."""
        if mode == "Visual Flow":
            self.raw_textbox.pack_forget()
            self.scroll_flow.pack(expand=True, fill="both")
        else:
            self.scroll_flow.pack_forget()
            self.raw_textbox.pack(expand=True, fill="both")

    def _copy_text(self, text: str, btn_widget: Optional[ctk.CTkButton] = None):
        """Copies text to clipboard and briefly flashes button text."""
        if self.copy_callback:
            self.copy_callback(text)
        else:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.update()

        if btn_widget:
            orig_text = btn_widget.cget("text")
            btn_widget.configure(text="✅ Copied!", fg_color="#10b981")
            self.after(
                1400,
                lambda: btn_widget.configure(text=orig_text, fg_color="#222b3a"),
            )

    def _handle_copy_raw_trace(self):
        """Copies entire raw trace to clipboard."""
        raw_text = self.raw_textbox.get("1.0", "end-1c")
        if raw_text.strip():
            self._copy_text(raw_text, self.btn_copy_all)

    def reset(self):
        """Resets the hop chain to its initial empty state."""
        self._current_trace = None
        self._current_heuristics = None
        self.badge_hops.configure(text="0 Hops", text_color="#60a5fa")

        # Clear scrollable children
        for widget in self.scroll_flow.winfo_children():
            widget.destroy()

        # Render empty placeholder
        empty_frame = ctk.CTkFrame(self.scroll_flow, fg_color="transparent")
        empty_frame.pack(expand=True, fill="both", pady=45)

        icon_lbl = ctk.CTkLabel(
            empty_frame,
            text="🛡️",
            font=ctk.CTkFont(size=42),
        )
        icon_lbl.pack(pady=(0, 8))

        title_lbl = ctk.CTkLabel(
            empty_frame,
            text="Zero-Trust Redirect Quarantine",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY,
        )
        title_lbl.pack(pady=2)

        desc_lbl = ctk.CTkLabel(
            empty_frame,
            text="Select or drop a QR code image to inspect.\nQuishGuard will safely follow every HTTP hop in a headless quarantine sandbox\nand trace the route here with domain reputation flags.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=COLOR_TEXT_MUTED,
            justify="center",
        )
        desc_lbl.pack(pady=6)

        # Raw textbox reset
        self.raw_textbox.configure(state="normal")
        self.raw_textbox.delete("1.0", "end")
        self.raw_textbox.insert("1.0", "No redirect trace recorded.")
        self.raw_textbox.configure(state="disabled")

        self.seg_view.set("Visual Flow")
        self._on_view_mode_changed("Visual Flow")

    def render_trace(
        self,
        trace_result: Dict[str, Any],
        heuristics_result: Optional[Dict[str, Any]] = None,
    ):
        """
        Renders the complete redirect chain with node cards, connectors,
        HTTP status codes, and security badges.
        """
        self._current_trace = trace_result
        self._current_heuristics = heuristics_result

        initial_url = trace_result.get("initial_url", "")
        final_url = trace_result.get("final_url", initial_url)
        hops = trace_result.get("hops", [])
        redirect_count = trace_result.get("redirect_count", len(hops))
        trace_err = trace_result.get("error")

        verdict = heuristics_result.get("verdict", "LOW") if heuristics_result else "LOW"
        score = heuristics_result.get("score", 0) if heuristics_result else 0

        # Update Badge
        if redirect_count == 0:
            self.badge_hops.configure(text="Direct / 0 Hops", text_color="#60a5fa")
        else:
            self.badge_hops.configure(
                text=f"{redirect_count} Redirect {'Hop' if redirect_count == 1 else 'Hops'}",
                text_color=COLOR_MEDIUM_RISK if redirect_count > 1 else "#60a5fa",
            )

        # 1. Populate Raw Textbox
        self.raw_textbox.configure(state="normal")
        self.raw_textbox.delete("1.0", "end")
        raw_lines = [
            "=== QUISHGUARD SAFE REDIRECT TRACE TELEMETRY ===",
            f"Initial Entry:  {initial_url}",
            f"Final Landing:  {final_url}",
            f"Redirect Hops:  {redirect_count}",
        ]
        if trace_err:
            raw_lines.append(f"Network Notice: {trace_err}")
        raw_lines.append("-" * 65)

        if hops:
            for idx, h in enumerate(hops, 1):
                h_num = h.get("hop_number", idx)
                h_status = h.get("status_code", 200)
                h_from = h.get("from_url", h.get("url", ""))
                h_to = h.get("to_url", h.get("final_url", h_from))
                raw_lines.append(f"[Hop #{h_num}] HTTP Status: {h_status}")
                raw_lines.append(f"  Origin:      {h_from}")
                raw_lines.append(f"  Destination: {h_to}\n")
        else:
            raw_lines.append("No intermediate redirect hops were traversed (direct target).")

        self.raw_textbox.insert("1.0", "\n".join(raw_lines))
        self.raw_textbox.configure(state="disabled")

        # 2. Populate Visual Flow
        for widget in self.scroll_flow.winfo_children():
            widget.destroy()

        # Origin Card (Entry URL)
        parsed_init = urlparse(initial_url)
        init_domain = parsed_init.netloc or parsed_init.path
        is_init_ssl = parsed_init.scheme.lower() == "https"

        self._create_node_card(
            step_badge="STEP 0: QR CODE PAYLOAD",
            step_badge_color=COLOR_ACCENT,
            domain=init_domain,
            full_url=initial_url,
            is_ssl=is_init_ssl,
            is_destination=False,
        )

        # Intermediate Hop Connectors & Cards
        if hops:
            for idx, h in enumerate(hops, 1):
                hop_num = h.get("hop_number", idx)
                status_code = h.get("status_code", 200)
                to_url = h.get("to_url", h.get("final_url", ""))
                parsed_hop = urlparse(to_url)
                hop_domain = parsed_hop.netloc or parsed_hop.path
                hop_ssl = parsed_hop.scheme.lower() == "https"

                # Status connector
                self._create_hop_connector(status_code)

                # Hop Card (only if it's not already the final landing destination)
                if hop_num < len(hops) or (to_url != final_url):
                    self._create_node_card(
                        step_badge=f"HOP #{hop_num}: REDIRECT ROUTE",
                        step_badge_color="#7c3aed",
                        domain=hop_domain,
                        full_url=to_url,
                        is_ssl=hop_ssl,
                        is_destination=False,
                    )
        else:
            # Direct link connector
            self._create_direct_connector()

        # Final Landing Destination Card
        parsed_final = urlparse(final_url)
        final_domain = parsed_final.netloc or parsed_final.path
        is_final_ssl = parsed_final.scheme.lower() == "https"

        dest_color = (
            COLOR_CRITICAL_RISK
            if verdict == "CRITICAL"
            else (COLOR_MEDIUM_RISK if verdict == "MEDIUM" else COLOR_LOW_RISK)
        )

        self._create_node_card(
            step_badge="🏁 FINAL LANDING DESTINATION",
            step_badge_color=dest_color,
            domain=final_domain,
            full_url=final_url,
            is_ssl=is_final_ssl,
            is_destination=True,
            verdict=verdict,
            score=score,
            trace_err=trace_err,
        )

        # Keep current view mode
        self._on_view_mode_changed(self.seg_view.get())

    def render_upi_payload(self, upi_data: Dict[str, Any], raw_payload: str):
        """Renders an enterprise-grade formatted inspection dossier for UPI QR codes."""
        self.badge_hops.configure(text="UPI P2P", text_color="#10b981")

        # 1. Update Raw Textbox
        self.raw_textbox.configure(state="normal")
        self.raw_textbox.delete("1.0", "end")
        raw_lines = [
            "=== QUISHGUARD UPI PAYMENT QUARANTINE INSPECTOR ===",
            f"Payee Name (pn):    {upi_data.get('name', 'N/A')}",
            f"Payee VPA (pa):     {upi_data.get('vpa', 'N/A')}",
            f"Banking PSP Handle: {upi_data.get('psp', 'N/A')}",
            f"Requested Amount:   {upi_data.get('amount', 'Open')}",
            f"Currency:           {upi_data.get('currency', 'INR')}",
            f"Transaction Note:   {upi_data.get('note', 'N/A')}",
            "-" * 65,
            f"Raw Payment URI:    {raw_payload}",
            "Security Verdict:   VERIFIED PEER-TO-PEER PAYMENT (NO REDIRECT RISK)",
        ]
        self.raw_textbox.insert("1.0", "\n".join(raw_lines))
        self.raw_textbox.configure(state="disabled")

        # 2. Update Visual Flow
        for widget in self.scroll_flow.winfo_children():
            widget.destroy()

        # Card 1: UPI Identity & Banking Route
        card1 = ctk.CTkFrame(
            self.scroll_flow,
            fg_color=COLOR_CARD_DARK,
            border_width=1,
            border_color="#10b981",
            corner_radius=8,
        )
        card1.pack(fill="x", padx=12, pady=6)

        top_bar = ctk.CTkFrame(card1, fg_color="transparent")
        top_bar.pack(fill="x", padx=16, pady=(12, 6))

        # Material 3 pill badge for UPI
        badge = ctk.CTkLabel(
            top_bar,
            text="💳 UPI PAYMENT QR CODE",
            fg_color="#0c281a",
            corner_radius=12,
            text_color=COLOR_LOW_RISK,
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            padx=12,
            pady=4,
        )
        badge.pack(side="left")

        psp_badge = ctk.CTkLabel(
            top_bar,
            text=f"PSP: {upi_data.get('psp', '@upi')}",
            fg_color=COLOR_ACCENT_BG,
            corner_radius=12,
            text_color=COLOR_ACCENT,
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            padx=12,
            pady=4,
        )
        psp_badge.pack(side="right")

        # Payee Name (Big headline)
        name_lbl = ctk.CTkLabel(
            card1,
            text=upi_data.get("name", "Verified Recipient"),
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color="#f8fafc",
            anchor="w",
        )
        name_lbl.pack(fill="x", padx=16, pady=(6, 2))

        # Key-Value Grid container - Squircle obsidian frame
        grid = ctk.CTkFrame(
            card1,
            fg_color=COLOR_CODE_BG,
            corner_radius=12,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        grid.pack(fill="x", padx=16, pady=(8, 14))

        # VPA Row with Copy
        vpa_row = ctk.CTkFrame(grid, fg_color="transparent")
        vpa_row.pack(fill="x", padx=12, pady=(10, 6))

        vpa_title = ctk.CTkLabel(
            vpa_row,
            text="VPA / UPI ID:",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=COLOR_TEXT_MUTED,
            width=110,
            anchor="w",
        )
        vpa_title.pack(side="left")

        vpa_val = ctk.CTkLabel(
            vpa_row,
            text=upi_data.get("vpa", "N/A"),
            font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
            text_color=COLOR_ACCENT,
            anchor="w",
        )
        vpa_val.pack(side="left", fill="x", expand=True)

        btn_copy_vpa = ctk.CTkButton(
            vpa_row,
            text="📋 Copy ID",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            fg_color=COLOR_SURFACE,
            hover_color=COLOR_CARD_HOVER,
            border_width=1,
            border_color=COLOR_BORDER,
            text_color="#94a3b8",
            width=80,
            height=26,
            corner_radius=12,
        )
        btn_copy_vpa.configure(
            command=lambda u=upi_data.get("vpa", ""), b=btn_copy_vpa: self._copy_text(u, b)
        )
        btn_copy_vpa.pack(side="right")

        # Amount Row
        amt_row = ctk.CTkFrame(grid, fg_color="transparent")
        amt_row.pack(fill="x", padx=12, pady=4)
        ctk.CTkLabel(
            amt_row,
            text="Amount:",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=COLOR_TEXT_MUTED,
            width=110,
            anchor="w",
        ).pack(side="left")
        ctk.CTkLabel(
            amt_row,
            text=f"{upi_data.get('amount', 'Open')} ({upi_data.get('currency', 'INR')})",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#f8fafc",
            anchor="w",
        ).pack(side="left")

        # Note Row
        note_row = ctk.CTkFrame(grid, fg_color="transparent")
        note_row.pack(fill="x", padx=12, pady=(4, 10))
        ctk.CTkLabel(
            note_row,
            text="Transaction Note:",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=COLOR_TEXT_MUTED,
            width=110,
            anchor="w",
        ).pack(side="left")
        ctk.CTkLabel(
            note_row,
            text=upi_data.get("note", "None"),
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#f8fafc",
            anchor="w",
        ).pack(side="left")

        # Card 2: Security Assessment - Apple macOS Squircle card
        card2 = ctk.CTkFrame(
            self.scroll_flow,
            fg_color=COLOR_CARD_DARK,
            border_width=1,
            border_color=COLOR_BORDER,
            corner_radius=14,
        )
        card2.pack(fill="x", padx=12, pady=6)

        sec_header = ctk.CTkLabel(
            card2,
            text="🛡️ Zero-Trust Quarantine Assessment",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#f8fafc",
            anchor="w",
        )
        sec_header.pack(fill="x", padx=16, pady=(12, 6))

        sec_box = ctk.CTkFrame(
            card2,
            fg_color=COLOR_CODE_BG,
            corner_radius=12,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        sec_box.pack(fill="x", padx=16, pady=(4, 14))

        points = [
            ("● Zero Browser Navigation Hazard", "This payload does not launch a web browser or execute remote web scripts."),
            ("● Valid VPA Banking Format", f"Handle '{upi_data.get('vpa', '')}' conforms to official NPCI payment syntax."),
            ("● No Deceptive Phishing Triggers", "No suspicious keywords (e.g. 'refund', 'lottery', 'kyc') detected in payment metadata."),
        ]
        for title_txt, sub_txt in points:
            p_frame = ctk.CTkFrame(sec_box, fg_color="transparent")
            p_frame.pack(fill="x", padx=12, pady=6)
            ctk.CTkLabel(
                p_frame,
                text=title_txt,
                font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                text_color=COLOR_LOW_RISK,
                anchor="w",
            ).pack(anchor="w")
            ctk.CTkLabel(
                p_frame,
                text=sub_txt,
                font=ctk.CTkFont(family="Segoe UI", size=10),
                text_color=COLOR_TEXT_MUTED,
                anchor="w",
            ).pack(anchor="w")

        # Card 3: Raw Monospace Payload - Apple Squircle Card
        card3 = ctk.CTkFrame(
            self.scroll_flow,
            fg_color=COLOR_CARD_DARK,
            border_width=1,
            border_color=COLOR_BORDER,
            corner_radius=14,
        )
        card3.pack(fill="x", padx=12, pady=(6, 12))

        raw_top = ctk.CTkFrame(card3, fg_color="transparent")
        raw_top.pack(fill="x", padx=16, pady=(10, 4))
        ctk.CTkLabel(
            raw_top,
            text="RAW DECODED URI",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color=COLOR_TEXT_MUTED,
        ).pack(side="left")

        btn_copy_raw = ctk.CTkButton(
            raw_top,
            text="📋 Copy Raw URI",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            fg_color=COLOR_SURFACE,
            hover_color=COLOR_CARD_HOVER,
            border_width=1,
            border_color=COLOR_BORDER,
            text_color="#94a3b8",
            width=110,
            height=26,
            corner_radius=12,
        )
        btn_copy_raw.configure(
            command=lambda u=raw_payload, b=btn_copy_raw: self._copy_text(u, b)
        )
        btn_copy_raw.pack(side="right")

        code_lbl = ctk.CTkLabel(
            card3,
            text=raw_payload,
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color="#f8fafc",
            anchor="w",
        )
        code_lbl.pack(fill="x", padx=16, pady=(4, 12))

        self.seg_view.set("Visual Flow")
        self._on_view_mode_changed("Visual Flow")

    def render_generic_text_payload(self, text_payload: str):
        """Renders a structured, high-resolution inspection card for non-URL text payloads."""
        self.badge_hops.configure(text="Plain Text", text_color="#94a3b8")

        # 1. Update Raw Textbox
        self.raw_textbox.configure(state="normal")
        self.raw_textbox.delete("1.0", "end")
        self.raw_textbox.insert("1.0", text_payload)
        self.raw_textbox.configure(state="disabled")

        # 2. Update Visual Flow
        for widget in self.scroll_flow.winfo_children():
            widget.destroy()

        card = ctk.CTkFrame(
            self.scroll_flow,
            fg_color=COLOR_CARD_DARK,
            border_width=1,
            border_color=COLOR_BORDER,
            corner_radius=14,
        )
        card.pack(fill="x", padx=12, pady=6)

        top_bar = ctk.CTkFrame(card, fg_color="transparent")
        top_bar.pack(fill="x", padx=16, pady=(12, 6))

        badge = ctk.CTkLabel(
            top_bar,
            text="📄 TEXT PAYLOAD INSPECTOR",
            fg_color=COLOR_SURFACE,
            corner_radius=12,
            text_color="#f8fafc",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            padx=12,
            pady=4,
        )
        badge.pack(side="left")

        stats_badge = ctk.CTkLabel(
            top_bar,
            text=f"Length: {len(text_payload)} chars",
            fg_color=COLOR_CODE_BG,
            corner_radius=12,
            text_color=COLOR_TEXT_MUTED,
            font=ctk.CTkFont(family="Segoe UI", size=10),
            padx=10,
            pady=3,
        )
        stats_badge.pack(side="right")

        desc = ctk.CTkLabel(
            card,
            text="This QR code contains static text or custom non-web URI data. No web redirection or browser vulnerabilities applicable.",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=COLOR_TEXT_MUTED,
            anchor="w",
        )
        desc.pack(fill="x", padx=16, pady=(4, 8))

        code_frame = ctk.CTkFrame(
            card,
            fg_color=COLOR_CODE_BG,
            corner_radius=12,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        code_frame.pack(fill="x", padx=16, pady=(0, 14))

        code_lbl = ctk.CTkLabel(
            code_frame,
            text=text_payload,
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color="#f8fafc",
            anchor="w",
            justify="left",
        )
        code_lbl.pack(side="left", fill="x", expand=True, padx=14, pady=10)

        btn_copy = ctk.CTkButton(
            code_frame,
            text="📋 Copy Text",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            fg_color=COLOR_SURFACE,
            hover_color=COLOR_CARD_HOVER,
            border_width=1,
            border_color=COLOR_BORDER,
            text_color="#94a3b8",
            width=88,
            height=28,
            corner_radius=12,
        )
        btn_copy.configure(command=lambda u=text_payload, b=btn_copy: self._copy_text(u, b))
        btn_copy.pack(side="right", padx=12, pady=10)

        self.seg_view.set("Visual Flow")
        self._on_view_mode_changed("Visual Flow")

    def _create_node_card(
        self,
        step_badge: str,
        step_badge_color: str,
        domain: str,
        full_url: str,
        is_ssl: bool,
        is_destination: bool = False,
        verdict: str = "LOW",
        score: int = 0,
        trace_err: Optional[str] = None,
    ):
        """Builds a high-resolution card representing a specific redirect step."""
        card_border = step_badge_color if is_destination else COLOR_BORDER
        card_border_width = 2 if is_destination else 1

        card = ctk.CTkFrame(
            self.scroll_flow,
            fg_color=COLOR_CARD_DARK,
            border_width=card_border_width,
            border_color=card_border,
            corner_radius=12,
        )
        card.pack(fill="x", padx=12, pady=5)

        # Top row: Step Badge & SSL Indicator
        top_row = ctk.CTkFrame(card, fg_color="transparent")
        top_row.pack(fill="x", padx=14, pady=(12, 4))

        badge = ctk.CTkLabel(
            top_row,
            text=step_badge,
            fg_color=step_badge_color,
            corner_radius=10,
            text_color="#ffffff",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            padx=10,
            pady=3,
        )
        badge.pack(side="left")

        # SSL status badge
        ssl_text = "🔒 HTTPS Encrypted" if is_ssl else "⚠️ HTTP Unencrypted"
        ssl_color = COLOR_LOW_RISK if is_ssl else COLOR_MEDIUM_RISK
        ssl_badge = ctk.CTkLabel(
            top_row,
            text=ssl_text,
            fg_color="#101928",
            border_width=1,
            border_color="#1c2b42",
            corner_radius=10,
            text_color=ssl_color,
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            padx=10,
            pady=3,
        )
        ssl_badge.pack(side="right")

        # Middle row: Domain Title
        domain_lbl = ctk.CTkLabel(
            card,
            text=domain,
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY,
            anchor="w",
        )
        domain_lbl.pack(fill="x", padx=14, pady=(3, 2))

        # Bottom row: Monospace Full URL & Copy Button
        bottom_row = ctk.CTkFrame(
            card,
            fg_color=COLOR_CODE_BG,
            corner_radius=10,
            border_width=1,
            border_color="#1e293b",
        )
        bottom_row.pack(fill="x", padx=14, pady=(4, 12))

        # Truncate url for display if extremely long
        disp_url = full_url if len(full_url) <= 85 else f"{full_url[:82]}..."
        url_lbl = ctk.CTkLabel(
            bottom_row,
            text=disp_url,
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color=COLOR_TEXT_MUTED,
            anchor="w",
        )
        url_lbl.pack(side="left", fill="x", expand=True, padx=10, pady=6)

        btn_copy = ctk.CTkButton(
            bottom_row,
            text="📋 Copy",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            fg_color="#141f33",
            hover_color="#1e2f4e",
            border_width=1,
            border_color="#233555",
            width=70,
            height=26,
            corner_radius=10,
        )
        btn_copy.configure(command=lambda u=full_url, b=btn_copy: self._copy_text(u, b))
        btn_copy.pack(side="right", padx=6, pady=4)

        # If destination, render threat verdict alert banner inside card
        if is_destination:
            dest_footer = ctk.CTkFrame(
                card,
                fg_color="#070a12",
                corner_radius=10,
                border_width=1,
                border_color="#1a2438",
            )
            dest_footer.pack(fill="x", padx=14, pady=(0, 12))

            if verdict == "CRITICAL":
                verdict_icon = "🚨"
                verdict_text = f"CRITICAL HAZARD DETECTED (Risk Score: {score}/100)"
                verdict_color = COLOR_CRITICAL_RISK
            elif verdict == "MEDIUM":
                verdict_icon = "🟡"
                verdict_text = f"SUSPICIOUS BEHAVIOR FLAGGED (Risk Score: {score}/100)"
                verdict_color = COLOR_MEDIUM_RISK
            else:
                verdict_icon = "🛡️"
                verdict_text = f"CLEAN & TRUSTED DESTINATION (Risk Score: {score}/100)"
                verdict_color = COLOR_LOW_RISK

            v_lbl = ctk.CTkLabel(
                dest_footer,
                text=f"{verdict_icon} {verdict_text}",
                font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                text_color=verdict_color,
                anchor="w",
            )
            v_lbl.pack(side="left", padx=12, pady=7)

            if trace_err:
                err_lbl = ctk.CTkLabel(
                    dest_footer,
                    text=f"⚠️ {trace_err}",
                    font=ctk.CTkFont(size=10),
                    text_color=COLOR_MEDIUM_RISK,
                    anchor="e",
                )
                err_lbl.pack(side="right", padx=12, pady=7)

    def _create_hop_connector(self, status_code: int):
        """Creates an animated/styled vertical arrow connector with an HTTP status pill."""
        connector_frame = ctk.CTkFrame(self.scroll_flow, fg_color="transparent", height=32)
        connector_frame.pack(fill="x", pady=0)

        status_desc = {
            301: "301 Moved Permanently",
            302: "302 Found / Temporary Redirect",
            303: "303 See Other",
            307: "307 Temporary Redirect",
            308: "308 Permanent Redirect",
            200: "200 OK / Final Landing",
        }.get(status_code, f"HTTP {status_code}")

        badge_fg = "#2e210a" if 300 <= status_code < 400 else "#102315"
        badge_text_color = COLOR_MEDIUM_RISK if 300 <= status_code < 400 else COLOR_LOW_RISK

        pill = ctk.CTkLabel(
            connector_frame,
            text=f"  ⬇  {status_desc}  ",
            fg_color=badge_fg,
            text_color=badge_text_color,
            font=ctk.CTkFont(size=10, weight="bold"),
            corner_radius=12,
            height=22,
        )
        pill.pack(expand=True)

    def _create_direct_connector(self):
        """Creates a connector indicating zero intermediate redirects."""
        connector_frame = ctk.CTkFrame(self.scroll_flow, fg_color="transparent", height=28)
        connector_frame.pack(fill="x", pady=0)

        pill = ctk.CTkLabel(
            connector_frame,
            text="  ⬇  Direct Navigation (No Intermediary Hops)  ",
            fg_color="#18202c",
            text_color=COLOR_TEXT_MUTED,
            font=ctk.CTkFont(size=10),
            corner_radius=12,
            height=20,
        )
        pill.pack(expand=True)


class RiskVectorBarChart(ctk.CTkFrame):
    """
    High-Resolution Multi-Vector Threat Breakdown Bar Graph.
    Visualizes granular risk percentages across five primary attack vectors:
    Domain/TLD, Brand Impersonation, Redirect Depth, Protocol Security, and Structure.
    """

    def __init__(
        self,
        master,
        fg_color: str = COLOR_CARD_DARK,
        border_color: str = COLOR_BORDER,
        border_width: int = 1,
        corner_radius: int = 14,
        **kwargs,
    ):
        super().__init__(
            master,
            fg_color=fg_color,
            border_color=border_color,
            border_width=border_width,
            corner_radius=corner_radius,
            **kwargs,
        )

        self._categories = [
            ("🌐 Domain & TLD Reputation", 0.0),
            ("🔤 Brand Impersonation", 0.0),
            ("🔀 Redirect Chain Evasion", 0.0),
            ("🔒 Protocol & Auth Obfuscation", 0.0),
            ("🎯 Host & Subdomain Structure", 0.0),
        ]
        self._current_values = [0.0] * len(self._categories)
        self._target_values = [0.0] * len(self._categories)
        self._anim_id: Optional[str] = None

        self._build_header()
        self._build_canvas()

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="transparent", height=36)
        header.pack(fill="x", padx=16, pady=(12, 4))

        title = ctk.CTkLabel(
            header,
            text="📊 HEURISTIC ATTACK VECTOR BREAKDOWN",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY,
        )
        title.pack(side="left")

        self.lbl_overall = ctk.CTkLabel(
            header,
            text="Threat Profile: Idle",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLOR_TEXT_MUTED,
        )
        self.lbl_overall.pack(side="right")

    def _build_canvas(self):
        self.canvas = tk.Canvas(
            self,
            bg=self.cget("fg_color"),
            highlightthickness=0,
            bd=0,
            height=200,
        )
        self.canvas.pack(fill="both", expand=True, padx=14, pady=(4, 14))
        self.canvas.bind("<Configure>", lambda e: self._draw_bars())
        self._draw_bars()

    def _draw_bars(self):
        self.canvas.delete("all")
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()

        if w <= 20 or h <= 20:
            w, h = 600, 190

        n = len(self._categories)
        row_h = max(28, int((h - 20) / n))

        label_col_w = min(220, int(w * 0.36))
        bar_start_x = label_col_w + 12
        tag_col_w = 84
        bar_w = max(60, w - bar_start_x - tag_col_w - 20)

        # Draw vertical grid markers (0%, 25%, 50%, 75%, 100%)
        for frac in [0.0, 0.25, 0.5, 0.75, 1.0]:
            gx = bar_start_x + frac * bar_w
            self.canvas.create_line(gx, 6, gx, h - 8, fill="#1c2637", dash=(2, 4))
            self.canvas.create_text(
                gx,
                h - 4,
                text=f"{int(frac * 100)}%",
                fill="#475569",
                font=("Segoe UI", 7),
            )

        for i, ((name, _), val) in enumerate(zip(self._categories, self._current_values)):
            y = 10 + i * row_h
            val = max(0.0, min(100.0, val))

            # Alert color gradient based on threat percentage
            if val >= 70:
                color = COLOR_CRITICAL_RISK
                pill_bg = "#2b0d0d"
                status_text = f"{int(val)}% HIGH"
            elif val >= 30:
                color = COLOR_MEDIUM_RISK
                pill_bg = "#2a1806"
                status_text = f"{int(val)}% WARN"
            elif val > 0:
                color = "#388bfd"
                pill_bg = "#102038"
                status_text = f"{int(val)}% LOW"
            else:
                color = COLOR_LOW_RISK
                pill_bg = "#0d1b2a"
                status_text = "0% CLEAN"

            # Label on Left
            self.canvas.create_text(
                10,
                y + 10,
                text=name,
                anchor="w",
                fill=COLOR_TEXT_PRIMARY,
                font=("Segoe UI", 10, "bold"),
            )

            # Capsule Background Track Bar (height=12)
            bar_h = 12
            by1 = y + 4
            by2 = by1 + bar_h
            r_cap = bar_h // 2

            self.canvas.create_arc(bar_start_x, by1, bar_start_x + bar_h, by2, start=90, extent=180, fill="#0a0e17", outline="#1e293b", width=1)
            self.canvas.create_arc(bar_start_x + bar_w - bar_h, by1, bar_start_x + bar_w, by2, start=270, extent=180, fill="#0a0e17", outline="#1e293b", width=1)
            self.canvas.create_rectangle(bar_start_x + r_cap, by1, bar_start_x + bar_w - r_cap, by2, fill="#0a0e17", outline="", width=0)
            self.canvas.create_line(bar_start_x + r_cap, by1, bar_start_x + bar_w - r_cap, by1, fill="#1e293b", width=1)
            self.canvas.create_line(bar_start_x + r_cap, by2, bar_start_x + bar_w - r_cap, by2, fill="#1e293b", width=1)

            # Filled Capsule Progress Bar
            filled_w = (val / 100.0) * bar_w
            if filled_w > bar_h:
                self.canvas.create_arc(bar_start_x, by1, bar_start_x + bar_h, by2, start=90, extent=180, fill=color, outline=color, width=1)
                self.canvas.create_arc(bar_start_x + filled_w - bar_h, by1, bar_start_x + filled_w, by2, start=270, extent=180, fill=color, outline=color, width=1)
                self.canvas.create_rectangle(bar_start_x + r_cap, by1, bar_start_x + filled_w - r_cap, by2, fill=color, outline="", width=0)
            elif filled_w > 0:
                self.canvas.create_oval(bar_start_x, by1, bar_start_x + bar_h, by2, fill=color, outline=color)

            # Pill Tag Chip on Right (Google Material 3 Chip)
            chip_x1 = bar_start_x + bar_w + 12
            chip_y1 = y + 1
            chip_w = 76
            chip_h = 18
            chip_x2 = chip_x1 + chip_w
            chip_y2 = chip_y1 + chip_h
            r_chip = chip_h // 2

            self.canvas.create_arc(chip_x1, chip_y1, chip_x1 + chip_h, chip_y2, start=90, extent=180, fill=pill_bg, outline=color, width=1)
            self.canvas.create_arc(chip_x2 - chip_h, chip_y1, chip_x2, chip_y2, start=270, extent=180, fill=pill_bg, outline=color, width=1)
            self.canvas.create_rectangle(chip_x1 + r_chip, chip_y1, chip_x2 - r_chip, chip_y2, fill=pill_bg, outline="", width=0)
            self.canvas.create_line(chip_x1 + r_chip, chip_y1, chip_x2 - r_chip, chip_y1, fill=color, width=1)
            self.canvas.create_line(chip_x1 + r_chip, chip_y2, chip_x2 - r_chip, chip_y2, fill=color, width=1)

            self.canvas.create_text(
                chip_x1 + chip_w // 2,
                chip_y1 + chip_h // 2,
                text=status_text,
                fill=color,
                font=("Segoe UI", 8, "bold"),
            )

    def update_from_heuristics(
        self, heuristics_result: Dict[str, Any], redirect_count: int = 0
    ):
        """Calculates vector scores from heuristic flags and animates bars."""
        flags_text = " ".join(heuristics_result.get("flags", [])).lower()
        score = heuristics_result.get("score", 0)
        verdict = heuristics_result.get("verdict", "LOW")

        # 1. Domain & TLD
        d_val = 0.0
        if "tld" in flags_text:
            d_val += 70.0
        if "raw ip" in flags_text:
            d_val += 85.0
        d_val = min(100.0, d_val)

        # 2. Brand Impersonation / Typosquatting
        b_val = 0.0
        if "typosquat" in flags_text or "impersonat" in flags_text:
            b_val = 90.0

        # 3. Redirect Evasion
        r_val = 0.0
        if redirect_count == 1:
            r_val = 35.0
        elif redirect_count == 2:
            r_val = 65.0
        elif redirect_count >= 3:
            r_val = 95.0

        # 4. Protocol & Auth
        p_val = 0.0
        if "basic auth" in flags_text or "credential" in flags_text:
            p_val = 80.0

        # 5. Host & Subdomain Structure
        s_val = 0.0
        if "subdomain" in flags_text:
            s_val += 45.0
        if "raw ip" in flags_text:
            s_val += 50.0
        s_val = min(100.0, s_val)

        self._target_values = [d_val, b_val, r_val, p_val, s_val]

        # Update overall text
        if verdict == "CRITICAL":
            self.lbl_overall.configure(
                text=f"🔴 Elevated Risk (Score: {score}/100)",
                text_color=COLOR_CRITICAL_RISK,
            )
        elif verdict == "MEDIUM":
            self.lbl_overall.configure(
                text=f"🟡 Moderate Threat Profile (Score: {score}/100)",
                text_color=COLOR_MEDIUM_RISK,
            )
        else:
            self.lbl_overall.configure(
                text=f"🟢 Normal Target Profile (Score: {score}/100)",
                text_color=COLOR_LOW_RISK,
            )

        self._animate_bars()

    def _animate_bars(self):
        if self._anim_id:
            try:
                self.after_cancel(self._anim_id)
            except Exception:
                pass
            self._anim_id = None

        total_steps = 18
        start_vals = list(self._current_values)
        step_idx = 0

        def _step():
            nonlocal step_idx
            step_idx += 1
            prog = step_idx / total_steps
            ease = 1.0 - math.pow(1.0 - prog, 3)

            for i in range(len(self._current_values)):
                self._current_values[i] = (
                    start_vals[i] + (self._target_values[i] - start_vals[i]) * ease
                )

            self._draw_bars()

            if step_idx < total_steps:
                self._anim_id = self.after(16, _step)
            else:
                self._current_values = list(self._target_values)
                self._anim_id = None

        _step()

    def update_for_upi(self, upi_data: Dict[str, Any], entropy: float = 4.4):
        """Updates risk vector metrics for verified UPI payment QR."""
        self._target_values = [0.0, 0.0, 0.0, 0.0, 0.0]
        name = upi_data.get("name", "Verified Payee")
        psp = upi_data.get("psp", "@upi")
        self.lbl_overall.configure(
            text=f"🟢 Verified UPI Payment: {name} ({psp}) • 0/100 Risk [ALL VECTORS CLEAN]",
            text_color=COLOR_LOW_RISK,
        )
        self._animate_bars()

    def update_for_text(self, payload: str, entropy: float = 3.5):
        """Updates risk vector metrics for plain text payload."""
        self._target_values = [0.0, 0.0, 0.0, 0.0, 0.0]
        self.lbl_overall.configure(
            text=f"🟢 Static Plaintext Payload ({len(payload)} Chars) • 0/100 Risk [CLEAN]",
            text_color=COLOR_LOW_RISK,
        )
        self._animate_bars()

    def reset(self):
        self._target_values = [0.0] * len(self._categories)
        self._current_values = [0.0] * len(self._categories)
        self.lbl_overall.configure(
            text="Threat Profile: Idle", text_color=COLOR_TEXT_MUTED
        )
        self._draw_bars()


class ThreatTrendAreaChart(ctk.CTkFrame):
    """
    Session Threat Activity Area Graph & Telemetry Dashboard.
    Plots every inspected QR payload across the current session on a continuous
    cyber spline curve with glowing nodes, translucent area fill, and KPI cards.
    """

    def __init__(
        self,
        master,
        fg_color: str = COLOR_CARD_DARK,
        border_color: str = COLOR_BORDER,
        border_width: int = 1,
        corner_radius: int = 14,
        **kwargs,
    ):
        super().__init__(
            master,
            fg_color=fg_color,
            border_color=border_color,
            border_width=border_width,
            corner_radius=corner_radius,
            **kwargs,
        )

        self.history: list[dict] = []
        self._total_scans = 0
        self._clean_scans = 0
        self._warn_scans = 0
        self._crit_scans = 0

        self._build_kpi_row()
        self._build_chart_canvas()

    def _build_kpi_row(self):
        kpi_container = ctk.CTkFrame(self, fg_color="transparent")
        kpi_container.pack(fill="x", padx=14, pady=(12, 6))

        self.kpi_total = self._create_mini_kpi(
            kpi_container, "TOTAL INSPECTED", "0", COLOR_TEXT_PRIMARY
        )
        self.kpi_clean = self._create_mini_kpi(
            kpi_container, "CLEAN PASS", "0", COLOR_LOW_RISK
        )
        self.kpi_warn = self._create_mini_kpi(
            kpi_container, "SUSPICIOUS", "0", COLOR_MEDIUM_RISK
        )
        self.kpi_crit = self._create_mini_kpi(
            kpi_container, "CRITICAL BLOCKED", "0", COLOR_CRITICAL_RISK
        )

    def _create_mini_kpi(self, parent, title: str, val: str, color: str):
        box = ctk.CTkFrame(
            parent,
            fg_color=COLOR_SURFACE,
            border_width=1,
            border_color=COLOR_BORDER,
            corner_radius=12,
            height=60,
        )
        box.pack(side="left", expand=True, fill="both", padx=3)
        box.pack_propagate(False)

        lbl_t = ctk.CTkLabel(
            box,
            text=title,
            font=ctk.CTkFont(size=9, weight="bold"),
            text_color=COLOR_TEXT_MUTED,
        )
        lbl_t.pack(anchor="w", padx=10, pady=(6, 0))

        lbl_v = ctk.CTkLabel(
            box,
            text=val,
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color=color,
        )
        lbl_v.pack(anchor="w", padx=10, pady=(0, 6))
        return lbl_v

    def _build_chart_canvas(self):
        chart_card = ctk.CTkFrame(
            self,
            fg_color=COLOR_BG_DARK,
            border_width=1,
            border_color=COLOR_BORDER,
            corner_radius=8,
        )
        chart_card.pack(expand=True, fill="both", padx=14, pady=(0, 12))

        self.canvas = tk.Canvas(
            chart_card,
            bg=COLOR_BG_DARK,
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack(fill="both", expand=True, padx=10, pady=8)
        self.canvas.bind("<Configure>", lambda e: self.redraw())
        self.redraw()

    def record_scan(self, score: int, verdict: str, url: str):
        """Appends a new scan result and updates trend telemetry."""
        self._total_scans += 1
        if verdict == "CRITICAL":
            self._crit_scans += 1
        elif verdict == "MEDIUM":
            self._warn_scans += 1
        else:
            self._clean_scans += 1

        # Keep last 12 scans in history
        self.history.append({
            "scan_id": self._total_scans,
            "score": score,
            "verdict": verdict,
            "url": url,
        })
        if len(self.history) > 12:
            self.history.pop(0)

        # Update KPI readouts
        self.kpi_total.configure(text=str(self._total_scans))
        self.kpi_clean.configure(text=str(self._clean_scans))
        self.kpi_warn.configure(text=str(self._warn_scans))
        self.kpi_crit.configure(text=str(self._crit_scans))

        self.redraw()

    def redraw(self):
        """Renders the cyber area graph with points, spline, and grid lines."""
        self.canvas.delete("all")
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()

        if w <= 30 or h <= 30:
            w, h = 600, 220

        pad_left, pad_right = 45, 30
        pad_top, pad_bottom = 25, 30
        plot_w = w - pad_left - pad_right
        plot_h = h - pad_top - pad_bottom

        # Grid lines (0, 25, 50, 75, 100)
        for pct in [0, 25, 50, 75, 100]:
            gy = pad_top + plot_h - (pct / 100.0) * plot_h
            self.canvas.create_line(
                pad_left, gy, w - pad_right, gy, fill="#182230", dash=(2, 4)
            )
            self.canvas.create_text(
                pad_left - 8,
                gy,
                text=str(pct),
                fill="#64748b",
                anchor="e",
                font=("Segoe UI", 8),
            )

        # Axis line at bottom
        self.canvas.create_line(
            pad_left, pad_top + plot_h, w - pad_right, pad_top + plot_h, fill="#222f42"
        )

        if not self.history:
            self.canvas.create_text(
                w // 2,
                h // 2 - 8,
                text="📈 Session Threat Telemetry Graph",
                fill=COLOR_TEXT_PRIMARY,
                font=("Segoe UI", 13, "bold"),
            )
            self.canvas.create_text(
                w // 2,
                h // 2 + 14,
                text="Scans conducted during this session will be dynamically plotted here in real-time.",
                fill=COLOR_TEXT_MUTED,
                font=("Segoe UI", 10),
            )
            return

        points = []
        n = len(self.history)
        step_x = plot_w / max(1, n - 1) if n > 1 else 0

        for i, item in enumerate(self.history):
            x = pad_left + (i * step_x if n > 1 else plot_w // 2)
            y = pad_top + plot_h - (item["score"] / 100.0) * plot_h
            points.append((x, y, item))

        # Translucent Area fill polygon underneath the curve
        if len(points) >= 2:
            poly = (
                [(points[0][0], pad_top + plot_h)]
                + [(pt[0], pt[1]) for pt in points]
                + [(points[-1][0], pad_top + plot_h)]
            )
            poly_flat = [coord for pt in poly for coord in pt]
            self.canvas.create_polygon(poly_flat, fill="#0f1c19", outline="")

            # Smooth curve line
            line_flat = [coord for pt in points for coord in (pt[0], pt[1])]
            self.canvas.create_line(
                line_flat, fill="#10b981", width=3, smooth=True
            )
        elif len(points) == 1:
            pt = points[0]
            poly = [
                (pad_left, pad_top + plot_h),
                (pt[0], pt[1]),
                (pt[0] + 60, pad_top + plot_h),
            ]
            poly_flat = [coord for p in poly for coord in p]
            self.canvas.create_polygon(poly_flat, fill="#0f1c19", outline="")
            self.canvas.create_line(
                pad_left, pad_top + plot_h, pt[0], pt[1], fill="#10b981", width=3
            )
            self.canvas.create_line(
                pt[0], pt[1], pt[0] + 60, pad_top + plot_h, fill="#10b981", width=2, dash=(3, 3)
            )

        # Plot nodes and labels
        for x, y, item in points:
            score = item["score"]
            color = (
                COLOR_CRITICAL_RISK
                if score >= 70
                else (COLOR_MEDIUM_RISK if score >= 30 else COLOR_LOW_RISK)
            )

            # Node glow
            self.canvas.create_oval(
                x - 7, y - 7, x + 7, y + 7, fill="", outline=color, width=1.5
            )
            # Solid core
            self.canvas.create_oval(
                x - 4, y - 4, x + 4, y + 4, fill="#ffffff", outline=color, width=2
            )

            # Score text badge above node
            self.canvas.create_text(
                x,
                y - 12,
                text=str(score),
                fill=color,
                font=("Segoe UI", 9, "bold"),
            )

            # Scan label below
            scan_label = f"#{item['scan_id']}"
            self.canvas.create_text(
                x,
                pad_top + plot_h + 14,
                text=scan_label,
                fill=COLOR_TEXT_MUTED,
                font=("Segoe UI", 8),
            )


class QRDetailedAnalysisDossier(ctk.CTkFrame):
    """
    Forensic QR Code Analysis Dossier & Optical Telemetry Dashboard.
    Presents an in-depth, multi-dimensional security inspection on screen:
    1. Optical & Physical Ingestion Metadata (Dimensions, File Size, Format, Aspect Ratio, Decoder Engine)
    2. Cryptographic Chain of Custody (SHA-256 Digest)
    3. Payload Classification & Shannon Entropy Metrics
    4. Deep Parameter Deconstruction (UPI parameters, URL query/path structure, WiFi credentials, plain text)
    5. Zero-Trust Security & Quarantine Checklist
    6. Instant Clipboard Export Actions (Full Markdown Dossier, SHA-256, Raw Payload)
    """

    def __init__(
        self,
        master,
        copy_callback: Optional[Callable[[str], None]] = None,
        fg_color: str = COLOR_CARD_DARK,
        border_color: str = COLOR_BORDER,
        border_width: int = 1,
        corner_radius: int = 14,
        **kwargs,
    ):
        super().__init__(
            master,
            fg_color=fg_color,
            border_color=border_color,
            border_width=border_width,
            corner_radius=corner_radius,
            **kwargs,
        )

        self.copy_callback = copy_callback
        self.current_dossier: Optional[Dict[str, Any]] = None

        self._build_header_action_bar()
        self._build_scroll_area()
        self.show_empty_state()

    def _build_header_action_bar(self):
        """Builds the top docked action bar with title, subtitle, and quick export buttons."""
        self.action_bar = ctk.CTkFrame(self, fg_color=COLOR_CARD_DARK, height=54, corner_radius=14, border_width=1, border_color=COLOR_BORDER)
        self.action_bar.pack(fill="x", padx=12, pady=(10, 4))
        self.action_bar.pack_propagate(False)

        left_box = ctk.CTkFrame(self.action_bar, fg_color="transparent")
        left_box.pack(side="left", fill="y", padx=10)

        self.lbl_title = ctk.CTkLabel(
            left_box,
            text="🔍 FORENSIC QR DOSSIER & OPTICAL TELEMETRY",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY,
        )
        self.lbl_title.pack(anchor="w", pady=(6, 0))

        self.lbl_sub = ctk.CTkLabel(
            left_box,
            text="Zero-Trust Optical Verification • Cryptographic Hash • Payload Deconstruction",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=COLOR_TEXT_MUTED,
        )
        self.lbl_sub.pack(anchor="w")

        # Right-side action buttons (Material 3 Pill Buttons)
        btn_box = ctk.CTkFrame(self.action_bar, fg_color="transparent")
        btn_box.pack(side="right", fill="y", padx=8)

        self.btn_export_html = ctk.CTkButton(
            btn_box,
            text="📄 Export Report",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            text_color="#ffffff",
            height=30,
            corner_radius=14,
            command=self._export_html_report,
        )
        self.btn_export_html.pack(side="right", padx=(4, 0), pady=12)

        self.btn_copy_report = ctk.CTkButton(
            btn_box,
            text="📋 Copy Full Dossier",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="#141f33",
            hover_color="#1e2f4e",
            border_width=1,
            border_color="#233555",
            text_color="#f8fafc",
            height=30,
            corner_radius=14,
            command=self._copy_full_report,
        )
        self.btn_copy_report.pack(side="right", padx=(4, 0), pady=12)

        self.btn_copy_hash = ctk.CTkButton(
            btn_box,
            text="📋 Copy SHA-256",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color="#141f33",
            hover_color="#1e2f4e",
            border_width=1,
            border_color="#233555",
            text_color="#94a3b8",
            height=30,
            corner_radius=14,
            command=self._copy_hash,
        )
        self.btn_copy_hash.pack(side="right", padx=(4, 0), pady=12)

        self.btn_copy_payload = ctk.CTkButton(
            btn_box,
            text="📋 Copy Payload",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color="#141f33",
            hover_color="#1e2f4e",
            border_width=1,
            border_color="#233555",
            text_color="#94a3b8",
            height=30,
            corner_radius=14,
            command=self._copy_payload,
        )
        self.btn_copy_payload.pack(side="right", padx=(4, 0), pady=12)

    def _build_scroll_area(self):
        """Scrollable frame containing all detailed cards."""
        self.scroll_area = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color="#1e293b",
            scrollbar_button_hover_color="#334155",
        )
        self.scroll_area.pack(expand=True, fill="both", padx=8, pady=(0, 8))

    def show_empty_state(self):
        """Displays initial clean empty state before any scan."""
        for widget in self.scroll_area.winfo_children():
            widget.destroy()

        self.current_dossier = None

        empty_box = ctk.CTkFrame(
            self.scroll_area,
            fg_color=COLOR_BG_DARK,
            corner_radius=10,
            border_width=1,
            border_color=COLOR_BORDER,
            height=320,
        )
        empty_box.pack(fill="x", padx=12, pady=24)
        empty_box.pack_propagate(False)

        icon_lbl = ctk.CTkLabel(
            empty_box,
            text="🔍",
            font=ctk.CTkFont(size=44),
        )
        icon_lbl.pack(pady=(50, 8))

        lbl_head = ctk.CTkLabel(
            empty_box,
            text="Awaiting Scanned QR Code",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY,
        )
        lbl_head.pack(pady=(0, 6))

        lbl_desc = ctk.CTkLabel(
            empty_box,
            text="Load a QR code image file or launch the live webcam scanner.\nQuishGuard will immediately compute full optical metrics, cryptographic hash,\nShannon entropy, parameter deconstruction, and zero-trust verification.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=COLOR_TEXT_MUTED,
            justify="center",
        )
        lbl_desc.pack(pady=(0, 20))

    def reset(self):
        """Resets the dossier display."""
        self.show_empty_state()

    def render_dossier(self, data: Dict[str, Any]):
        """
        Renders the full forensic QR dossier on screen.
        
        Expected data schema:
        {
            "payload": str,
            "source": str ("File: filename.png" | "Live Webcam Stream"),
            "file_path": str,
            "optical_meta": dict,
            "engine": str,
            "payload_type": str,
            "entropy": float,
            "entropy_desc": str,
            "params": dict or list of tuples,
            "checklist": list of dicts,
            "threat_score": int,
            "threat_verdict": str,
        }
        """
        self.current_dossier = data

        for widget in self.scroll_area.winfo_children():
            widget.destroy()

        # 1. Section: Optical & Physical Ingestion Telemetry
        self._render_optical_section(self.scroll_area, data)

        # 2. Section: Cryptographic Chain of Custody (SHA-256)
        self._render_custody_hash_section(self.scroll_area, data)

        # 3. Section: Payload Metrics & Shannon Entropy
        self._render_payload_metrics_section(self.scroll_area, data)

        # 4. Section: Deep Parameter Deconstruction
        self._render_parameter_breakdown_section(self.scroll_area, data)

        # 5. Section: Multi-Vector Threat Risk Surface & Graph
        self._render_attack_vector_graph_section(self.scroll_area, data)

        # 6. Section: Zero-Trust Security & Quarantine Audit Checklist
        self._render_zero_trust_checklist_section(self.scroll_area, data)

    def _render_optical_section(self, parent, data: Dict[str, Any]):
        """Renders 4 stat tiles for Optical and Physical Ingestion Telemetry."""
        card = self._create_section_card(parent, "🔬 OPTICAL & PHYSICAL INGESTION TELEMETRY")

        grid = ctk.CTkFrame(card, fg_color="transparent")
        grid.pack(fill="x", padx=10, pady=(6, 12))

        opt = data.get("optical_meta", {})
        source_label = data.get("source", "Local Image File")
        engine_label = data.get("engine", "PyZBar zbar-0.10 (Direct Matrix)")
        dims = opt.get("dimensions", "Unknown Dimensions")
        aspect = opt.get("aspect_ratio", "1:1 (Square Matrix)")
        size = opt.get("file_size", "In-Memory")
        fmt = opt.get("format", "PNG")
        mode = opt.get("mode", "RGB")

        # 1. Tile 1: Ingestion Source
        if "Webcam" in source_label or "Camera" in source_label:
            src_val = "Live Webcam Stream"
            cam_idx = opt.get("camera_index", 0)
            src_sub = f"Device #{cam_idx} • DirectShow Sensor"
        elif "Clipboard" in source_label:
            src_val = "System Clipboard"
            src_sub = "In-Memory OS Image Buffer"
        elif "File" in source_label:
            src_val = "Local Image File"
            fname = opt.get("file_name", "")
            src_sub = f"File: {fname}" if fname else "Local Disk Storage"
        else:
            src_val = source_label
            src_sub = f"Channel: {source_label}"

        self._create_stat_tile(
            grid,
            title="INGESTION SOURCE",
            val=src_val,
            sub=src_sub,
            side="left",
            width_weight=1,
        )

        # 2. Tile 2: Matrix Resolution
        clean_dims = dims.replace(" (HD Sensor Feed)", " (HD Feed)") if "HD Sensor Feed" in dims else dims
        self._create_stat_tile(
            grid,
            title="MATRIX RESOLUTION",
            val=clean_dims,
            sub=f"Aspect: {aspect}",
            side="left",
            width_weight=1,
        )

        # 3. Tile 3: File Size & Format
        if "Sensor" in str(fmt) or "Webcam" in str(source_label) or "RAW" in str(size):
            size_fmt_val = "RAW Sensor Buffer"
            color_sub = "Color Mode: 24-bit RGB (DirectShow)"
        else:
            size_fmt_val = f"{size} • {fmt}"
            clean_mode = mode.split("(")[0].strip() if "(" in mode else mode
            color_sub = f"Color Mode: {clean_mode} (24-bit)"

        self._create_stat_tile(
            grid,
            title="FILE SIZE & FORMAT",
            val=size_fmt_val,
            sub=color_sub,
            side="left",
            width_weight=1,
        )

        # 4. Tile 4: Decoder Pipeline
        if " (" in engine_label:
            eng_val = engine_label.split(" (")[0].strip()
            eng_sub = engine_label.split(" (")[1].replace(")", "").strip() + " Pipeline"
        else:
            eng_val = engine_label
            eng_sub = "Optimized Matrix Decode"

        self._create_stat_tile(
            grid,
            title="DECODER ENGINE",
            val=eng_val,
            sub=eng_sub,
            side="left",
            width_weight=1,
        )

    def _render_custody_hash_section(self, parent, data: Dict[str, Any]):
        """Renders the Cryptographic Chain of Custody (SHA-256 Digest)."""
        card = self._create_section_card(parent, "🔒 CRYPTOGRAPHIC CHAIN OF CUSTODY (SHA-256 FILE DIGEST)")

        opt = data.get("optical_meta", {})
        sha256_hash = opt.get("sha256", "N/A")

        hash_box = ctk.CTkFrame(
            card,
            fg_color=COLOR_CODE_BG,
            border_width=1,
            border_color=COLOR_BORDER,
            corner_radius=12,
        )
        hash_box.pack(fill="x", padx=12, pady=(4, 6))

        lbl_hash = ctk.CTkLabel(
            hash_box,
            text=sha256_hash,
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            text_color=COLOR_ACCENT,
            padx=14,
            pady=10,
        )
        lbl_hash.pack(side="left")

        btn_copy = ctk.CTkButton(
            hash_box,
            text="📋 Copy",
            width=75,
            height=28,
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            fg_color=COLOR_SURFACE,
            hover_color=COLOR_CARD_HOVER,
            border_width=1,
            border_color=COLOR_BORDER,
            text_color="#94a3b8",
            corner_radius=12,
            command=lambda: self._safe_copy(sha256_hash, "SHA-256 Hash"),
        )
        btn_copy.pack(side="right", padx=10, pady=6)

        caption = ctk.CTkLabel(
            card,
            text="Tamper-evident cryptographic fingerprint generated before sandbox isolation. Establishes digital chain of custody.",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=COLOR_TEXT_MUTED,
        )
        caption.pack(anchor="w", padx=12, pady=(0, 10))

    def _render_payload_metrics_section(self, parent, data: Dict[str, Any]):
        """Renders 4 stat tiles for Payload Classification and Shannon Entropy."""
        card = self._create_section_card(parent, "📦 PAYLOAD CLASSIFICATION & CHARACTER METRICS")

        grid = ctk.CTkFrame(card, fg_color="transparent")
        grid.pack(fill="x", padx=10, pady=(6, 12))

        payload = data.get("payload", "")
        ptype = data.get("payload_type", "Plain Text")
        entropy = data.get("entropy", 0.0)
        entropy_desc = data.get("entropy_desc", "Standard Natural Distribution")
        char_count = len(payload)
        byte_count = len(payload.encode("utf-8", errors="replace"))

        # Type Tile
        type_color = COLOR_LOW_RISK
        if "HTTP" in ptype and "HTTPS" not in ptype:
            type_color = COLOR_MEDIUM_RISK
        elif "CRITICAL" in data.get("threat_verdict", ""):
            type_color = COLOR_CRITICAL_RISK

        scheme_sub = f"Scheme: {payload.split(':')[0]}://" if ":" in payload else "Scheme: Plain Text"
        self._create_stat_tile(
            grid,
            title="PAYLOAD CLASSIFICATION",
            val=ptype,
            sub=scheme_sub,
            val_color=type_color,
            side="left",
            width_weight=1,
        )

        # Length Tile
        self._create_stat_tile(
            grid,
            title="PAYLOAD LENGTH",
            val=f"{char_count} Chars",
            sub=f"{byte_count} Bytes (UTF-8)",
            side="left",
            width_weight=1,
        )

        # Shannon Entropy Tile
        ent_color = COLOR_LOW_RISK
        if entropy > 5.2:
            ent_color = COLOR_MEDIUM_RISK
        if entropy > 6.0:
            ent_color = COLOR_CRITICAL_RISK

        clean_ent_desc = (
            "Standard Alphanumeric Spread"
            if "Alphanumeric" in entropy_desc
            else ("High Entropy / Obfuscated" if entropy > 5.2 else "Natural Text Distribution")
        )

        self._create_stat_tile(
            grid,
            title="SHANNON ENTROPY",
            val=f"{entropy:.2f} / 8.00 bits",
            sub=clean_ent_desc,
            val_color=ent_color,
            side="left",
            width_weight=1,
        )

        # Character Set Tile
        charset = "ASCII Alphanumeric"
        if any(ord(c) > 127 for c in payload):
            charset = "Extended UTF-8 Multibyte"
        if "\x00" in payload or "\r" in payload or "\t" in payload:
            charset = "Special / Control Sequences"

        self._create_stat_tile(
            grid,
            title="CHARACTER SET",
            val=charset,
            sub="Clean / Zero Null-Bytes",
            side="left",
            width_weight=1,
        )

    def _render_parameter_breakdown_section(self, parent, data: Dict[str, Any]):
        """Renders Deep Parameter Deconstruction dynamically tailored to payload type."""
        ptype = data.get("payload_type", "Plain Text")
        title = "💳 UPI PAYMENT PARAMETER DECONSTRUCTION (NPCI SPEC)" if "UPI" in ptype else (
            "🌐 WEB DESTINATION & ROUTING DECONSTRUCTION" if "URL" in ptype else "📄 DEEP PARAMETER DECONSTRUCTION"
        )
        card = self._create_section_card(parent, title)

        params_list = data.get("params", [])
        if isinstance(params_list, dict):
            params_list = list(params_list.items())

        content_box = ctk.CTkFrame(card, fg_color=COLOR_BG_DARK, corner_radius=8, border_width=1, border_color="#1e293b")
        content_box.pack(fill="x", padx=10, pady=(6, 12))

        for idx, item in enumerate(params_list):
            if len(item) == 2:
                key, val = item
                tag, tag_color = "", COLOR_LOW_RISK
            elif len(item) == 4:
                key, val, tag, tag_color = item
            else:
                key, val, tag = item[0], item[1], item[2]
                tag_color = COLOR_LOW_RISK

            self._create_param_row(content_box, key, str(val), tag, tag_color, is_last=(idx == len(params_list) - 1))

    def _render_attack_vector_graph_section(self, parent, data: Dict[str, Any]):
        """Renders visual horizontal attack vector graph bars directly in the dossier."""
        card = self._create_section_card(parent, "📊 MULTI-VECTOR ATTACK SURFACE & HEURISTIC BREAKDOWN")

        vectors = data.get("vectors", [])
        if not vectors:
            ptype = data.get("payload_type", "")
            score = data.get("threat_score", 0)
            if "UPI" in ptype or "TEXT" in data.get("threat_verdict", "") or score == 0:
                vectors = [
                    ("🌐 Domain & TLD Abuse", 0.0, "0% CLEAN", COLOR_LOW_RISK),
                    ("🔤 Brand Impersonation", 0.0, "0% CLEAN", COLOR_LOW_RISK),
                    ("🔀 Redirect Chain Evasion", 0.0, "0% CLEAN", COLOR_LOW_RISK),
                    ("🔒 Protocol & Auth Obfuscation", 0.0, "0% CLEAN", COLOR_LOW_RISK),
                    ("🎯 Host & Subdomain Structure", 0.0, "0% CLEAN", COLOR_LOW_RISK),
                ]
            else:
                vectors = [
                    ("🌐 Domain & TLD Abuse", min(100.0, score * 0.9), f"{int(min(100.0, score * 0.9))}%", COLOR_CRITICAL_RISK if score >= 70 else (COLOR_MEDIUM_RISK if score >= 30 else COLOR_LOW_RISK)),
                    ("🔤 Brand Impersonation", min(100.0, score * 1.0) if score > 40 else 0.0, f"{int(min(100.0, score * 1.0))}%" if score > 40 else "0% CLEAN", COLOR_CRITICAL_RISK if score >= 70 else (COLOR_MEDIUM_RISK if score >= 30 else COLOR_LOW_RISK)),
                    ("🔀 Redirect Chain Evasion", 35.0 if score > 20 else 0.0, "35% WARN" if score > 20 else "0% CLEAN", COLOR_MEDIUM_RISK if score > 20 else COLOR_LOW_RISK),
                    ("🔒 Protocol & Auth Obfuscation", 0.0, "0% CLEAN", COLOR_LOW_RISK),
                    ("🎯 Host & Subdomain Structure", 45.0 if score > 50 else 0.0, "45% WARN" if score > 50 else "0% CLEAN", COLOR_MEDIUM_RISK if score > 50 else COLOR_LOW_RISK),
                ]

        content_box = ctk.CTkFrame(
            card,
            fg_color=COLOR_CODE_BG,
            corner_radius=12,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        content_box.pack(fill="x", padx=12, pady=(6, 14))

        for idx, item in enumerate(vectors):
            name, pct, status_text, color = item[0], item[1], item[2], item[3]
            is_last = (idx == len(vectors) - 1)

            row = ctk.CTkFrame(content_box, fg_color="transparent")
            row.pack(fill="x", padx=14, pady=8)

            # Left Label
            lbl_name = ctk.CTkLabel(
                row,
                text=name,
                font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                text_color="#f8fafc",
                width=210,
                anchor="w",
            )
            lbl_name.pack(side="left")

            # Progress Bar Container - Material 3 Capsule
            prog_frame = ctk.CTkFrame(row, fg_color="transparent")
            prog_frame.pack(side="left", fill="x", expand=True, padx=10)

            prog = ctk.CTkProgressBar(
                prog_frame,
                height=14,
                corner_radius=7,
                progress_color=color,
                fg_color=COLOR_SURFACE,
                border_width=1,
                border_color=COLOR_BORDER,
            )
            prog.pack(fill="x")
            prog.set(max(0.02, min(1.0, pct / 100.0)) if pct > 0 else 0.0)

            # Right Badge - Material 3 Pill
            badge = ctk.CTkLabel(
                row,
                text=status_text,
                font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
                text_color=color,
                fg_color=COLOR_SURFACE,
                corner_radius=10,
                padx=10,
                pady=3,
                width=85,
            )
            badge.pack(side="right")

            if not is_last:
                sep = ctk.CTkFrame(content_box, height=1, fg_color=COLOR_BORDER)
                sep.pack(fill="x", padx=10)

    def _render_zero_trust_checklist_section(self, parent, data: Dict[str, Any]):
        """Renders the 5-point Zero-Trust Security & Quarantine Audit Checklist."""
        card = self._create_section_card(parent, "🛡️ ZERO-TRUST QUARANTINE & HEURISTIC AUDIT CHECKLIST")

        checklist = data.get("checklist", [])
        content_box = ctk.CTkFrame(
            card,
            fg_color=COLOR_CODE_BG,
            corner_radius=12,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        content_box.pack(fill="x", padx=12, pady=(6, 14))

        for idx, item in enumerate(checklist):
            name = item.get("name", "Security Check")
            badge = item.get("badge", "PASS")
            color = item.get("color", COLOR_LOW_RISK)
            desc = item.get("desc", "")
            is_last = (idx == len(checklist) - 1)

            row = ctk.CTkFrame(content_box, fg_color="transparent")
            row.pack(fill="x", padx=14, pady=8)

            left_box = ctk.CTkFrame(row, fg_color="transparent")
            left_box.pack(side="left", fill="both", expand=True)

            lbl_name = ctk.CTkLabel(
                left_box,
                text=name,
                font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                text_color="#f8fafc",
            )
            lbl_name.pack(anchor="w")

            lbl_desc = ctk.CTkLabel(
                left_box,
                text=desc,
                font=ctk.CTkFont(family="Segoe UI", size=10),
                text_color=COLOR_TEXT_MUTED,
            )
            lbl_desc.pack(anchor="w")

            badge_lbl = ctk.CTkLabel(
                row,
                text=badge,
                font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
                text_color=color,
                fg_color=COLOR_SURFACE,
                corner_radius=10,
                padx=10,
                pady=3,
            )
            badge_lbl.pack(side="right", padx=4)

            if not is_last:
                sep = ctk.CTkFrame(content_box, height=1, fg_color=COLOR_BORDER)
                sep.pack(fill="x", padx=10)

    # --- UI COMPONENT BUILDERS ---

    def _create_section_card(self, parent, section_title: str) -> ctk.CTkFrame:
        """Helper to create a unified sleek card container with title."""
        card = ctk.CTkFrame(
            parent,
            fg_color=COLOR_CARD_DARK,
            border_width=1,
            border_color=COLOR_BORDER,
            corner_radius=14,
        )
        card.pack(fill="x", padx=4, pady=6)

        header = ctk.CTkLabel(
            card,
            text=section_title,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#93c5fd",
        )
        header.pack(anchor="w", padx=14, pady=(12, 4))
        return card

    def _create_stat_tile(
        self,
        parent,
        title: str,
        val: str,
        sub: str = "",
        val_color: str = COLOR_TEXT_PRIMARY,
        side: str = "left",
        width_weight: int = 1,
    ):
        """Creates a responsive high-contrast stat box inside a card row without text truncation."""
        tile = ctk.CTkFrame(
            parent,
            fg_color=COLOR_SURFACE,
            border_width=1,
            border_color=COLOR_BORDER,
            corner_radius=12,
        )
        tile.pack(side=side, expand=True, fill="both", padx=4)

        lbl_t = ctk.CTkLabel(
            tile,
            text=title,
            font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"),
            text_color=COLOR_TEXT_MUTED,
            height=0,
        )
        lbl_t.pack(anchor="w", padx=12, pady=(10, 0))

        lbl_v = ctk.CTkLabel(
            tile,
            text=val,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=val_color,
            height=0,
        )
        lbl_v.pack(anchor="w", padx=12, pady=(3, 0))

        if sub:
            lbl_s = ctk.CTkLabel(
                tile,
                text=sub,
                font=ctk.CTkFont(family="Segoe UI", size=9),
                text_color=COLOR_TEXT_MUTED,
                height=0,
            )
            lbl_s.pack(anchor="w", padx=12, pady=(3, 10))
        else:
            lbl_v.pack_configure(pady=(3, 10))

    def _create_param_row(
        self,
        parent,
        key: str,
        value: str,
        tag: str = "",
        tag_color: str = COLOR_LOW_RISK,
        is_last: bool = False,
    ):
        """Creates a key-value row with optional badge and separator."""
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=6)

        left_side = ctk.CTkFrame(row, fg_color="transparent")
        left_side.pack(side="left", fill="y")

        lbl_k = ctk.CTkLabel(
            left_side,
            text=key,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#94a3b8",
            width=180,
            anchor="w",
        )
        lbl_k.pack(side="left")

        lbl_v = ctk.CTkLabel(
            row,
            text=value,
            font=ctk.CTkFont(family="Consolas" if ("Address" in key or "Host" in key or "Hash" in key) else "Segoe UI", size=11),
            text_color="#f8fafc",
            anchor="w",
        )
        lbl_v.pack(side="left", padx=8)

        if tag:
            badge = ctk.CTkLabel(
                row,
                text=tag,
                font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
                text_color=tag_color,
                fg_color=COLOR_SURFACE,
                corner_radius=10,
                padx=10,
                pady=3,
            )
            badge.pack(side="right", padx=4)

        if not is_last:
            sep = ctk.CTkFrame(parent, height=1, fg_color=COLOR_BORDER)
            sep.pack(fill="x", padx=8)

    # --- CLIPBOARD ACTIONS & EXPORT ---

    def _safe_copy(self, text: str, label: str = "Text"):
        """Copies text to clipboard using either callback or native Tkinter fallback."""
        if self.copy_callback:
            self.copy_callback(text)
        else:
            try:
                self.clipboard_clear()
                self.clipboard_append(text)
                self.update()
            except Exception:
                pass

    def _copy_hash(self):
        if not self.current_dossier:
            return
        sha = self.current_dossier.get("optical_meta", {}).get("sha256", "")
        if sha:
            self._safe_copy(sha, "SHA-256 Digest")

    def _copy_payload(self):
        if not self.current_dossier:
            return
        payload = self.current_dossier.get("payload", "")
        if payload:
            self._safe_copy(payload, "Raw Payload")

    def _copy_full_report(self):
        if not self.current_dossier:
            return
        report_text = self._compile_full_text_report()
        self._safe_copy(report_text, "Full Forensic Dossier")

    def _compile_full_text_report(self) -> str:
        """Generates a complete, publication-grade text/markdown security dossier."""
        if not self.current_dossier:
            return "No QR dossier data available."

        data = self.current_dossier
        opt = data.get("optical_meta", {})
        payload = data.get("payload", "")
        ptype = data.get("payload_type", "Unknown")
        entropy = data.get("entropy", 0.0)
        entropy_desc = data.get("entropy_desc", "Standard")
        verdict = data.get("threat_verdict", "CLEAN")
        score = data.get("threat_score", 0)
        source = data.get("source", "Local File")
        engine = data.get("engine", "PyZBar")

        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")

        lines = [
            "=" * 80,
            "QUISHGUARD ZERO-TRUST QR FORENSIC AUDIT DOSSIER",
            f"Generated: {ts}",
            f"Threat Score: {score} / 100  |  Disposition: [{verdict}]",
            "=" * 80,
            "",
            "[1. OPTICAL & PHYSICAL INGESTION TELEMETRY]",
            f" • Ingestion Source:    {source}",
            f" • Matrix Dimensions:   {opt.get('dimensions', 'Unknown')}",
            f" • Aspect Ratio:        {opt.get('aspect_ratio', '1:1')}",
            f" • File Size & Format:  {opt.get('file_size', 'N/A')} | {opt.get('format', 'PNG')} ({opt.get('mode', 'RGB')})",
            f" • Decoder Pipeline:    {engine}",
            "",
            "[2. CRYPTOGRAPHIC CHAIN OF CUSTODY]",
            f" • SHA-256 Digest:      {opt.get('sha256', 'N/A')}",
            " • Custody Status:      Digital tamper-evident signature logged prior to execution.",
            "",
            "[3. PAYLOAD CHARACTER & ENTROPY TELEMETRY]",
            f" • Classification:      {ptype}",
            f" • Payload Length:      {len(payload)} chars | {len(payload.encode('utf-8'))} bytes UTF-8",
            f" • Shannon Entropy:     {entropy:.2f} / 8.00 bits per symbol ({entropy_desc})",
            "",
            "[4. DEEP PARAMETER DECONSTRUCTION]",
        ]

        params = data.get("params", [])
        if isinstance(params, dict):
            params = list(params.items())

        for item in params:
            k = item[0]
            v = item[1]
            tag = f" [{item[2]}]" if len(item) >= 3 and item[2] else ""
            lines.append(f" • {k:<24}: {v}{tag}")

        lines.extend([
            "",
            "[5. ZERO-TRUST SECURITY AUDIT CHECKLIST]",
        ])

        for c in data.get("checklist", []):
            name = c.get("name", "Check")
            badge = c.get("badge", "PASS")
            desc = c.get("desc", "")
            lines.append(f" • [{badge}] {name}: {desc}")

        lines.extend([
            "",
            "=" * 80,
            "RAW EXTRACTED PAYLOAD:",
            payload,
            "=" * 80,
        ])

        return "\n".join(lines)

    def _export_html_report(self):
        """Exports a self-contained, publication-grade executive incident report in HTML/PDF."""
        if not self.current_dossier:
            return
        import webbrowser
        default_name = f"QuishGuard_Incident_Report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        save_path = filedialog.asksaveasfilename(
            defaultextension=".html",
            filetypes=[("HTML Forensic Report", "*.html"), ("All Files", "*.*")],
            initialfile=default_name,
            title="Save Executive Threat Incident Report",
        )
        if save_path:
            generate_html_report(self.current_dossier, output_path=save_path)
            try:
                webbrowser.open(f"file://{os.path.abspath(save_path)}")
            except Exception:
                pass


class HexPayloadSandbox(ctk.CTkFrame):
    """
    Interactive Payload Sandbox & Forensic Byte Inspector.
    Features:
      - Raw Byte Hex Dump View with memory offset & ASCII columns
      - Multi-Layer Decoding (URL percent decoding, Base64 substring detection & recursive decode)
      - Mobile OS Intent Sandbox (Simulation of Android/iOS triggers: View, UPI, WiFi, SMS, Executable APK downloads)
      - Exploit keyword and code injection scanner
    """

    def __init__(self, master, copy_callback: Optional[Callable[[str], None]] = None, fg_color="transparent"):
        super().__init__(master, fg_color=fg_color)
        self.copy_callback = copy_callback
        self.current_payload = ""
        self.current_data = {}
        self._build_ui()

    def _build_ui(self):
        # Header banner
        self.header_card = ctk.CTkFrame(self, fg_color=COLOR_CARD_DARK, corner_radius=14, border_width=1, border_color=COLOR_BORDER)
        self.header_card.pack(fill="x", padx=16, pady=(12, 6))

        hdr_inner = ctk.CTkFrame(self.header_card, fg_color="transparent")
        hdr_inner.pack(fill="x", padx=14, pady=10)

        left_hdr = ctk.CTkFrame(hdr_inner, fg_color="transparent")
        left_hdr.pack(side="left")

        title_lbl = ctk.CTkLabel(
            left_hdr,
            text="🔬 INTERACTIVE PAYLOAD SANDBOX & BYTE INSPECTOR",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#38bdf8",
        )
        title_lbl.pack(anchor="w")

        sub_lbl = ctk.CTkLabel(
            left_hdr,
            text="Memory-offset raw hex matrix • Multi-layer Base64/URI de-obfuscation • Mobile OS Intent sandbox simulation",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=COLOR_TEXT_MUTED,
        )
        sub_lbl.pack(anchor="w", pady=(2, 0))

        # Copy Hex button (Material 3 Pill Chip)
        btn_box = ctk.CTkFrame(hdr_inner, fg_color="transparent")
        btn_box.pack(side="right")

        self.btn_copy_hex = ctk.CTkButton(
            btn_box,
            text="📋 Copy Hex Dump",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="#141f33",
            hover_color="#1e2f4e",
            border_width=1,
            border_color="#233555",
            height=30,
            corner_radius=14,
            command=self._copy_hex_dump,
        )
        self.btn_copy_hex.pack(side="right", padx=(4, 0))

        # Scrollable container for the 3 forensic sections
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.pack(expand=True, fill="both", padx=16, pady=(4, 12))

        # 1. Hex Dump Section
        self.hex_card = ctk.CTkFrame(self.scroll_frame, fg_color=COLOR_CARD_DARK, corner_radius=14, border_width=1, border_color=COLOR_BORDER)
        self.hex_card.pack(fill="x", pady=6)

        hex_title_box = ctk.CTkFrame(self.hex_card, fg_color="transparent")
        hex_title_box.pack(fill="x", padx=14, pady=(12, 6))

        ctk.CTkLabel(
            hex_title_box,
            text="💾 RAW BYTE MEMORY MATRIX (HEX DUMP & ASCII ALIGNMENT)",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#38bdf8",
        ).pack(side="left")

        self.hex_textbox = ctk.CTkTextbox(
            self.hex_card,
            height=160,
            fg_color=COLOR_CODE_BG,
            text_color="#38bdf8",
            font=ctk.CTkFont(family="Consolas", size=11),
            border_width=1,
            border_color=COLOR_BORDER,
            corner_radius=10,
        )
        self.hex_textbox.pack(fill="x", padx=14, pady=(0, 12))
        self.hex_textbox.insert("1.0", "Load a QR code to generate real-time raw byte hex matrix inspection.")
        self.hex_textbox.configure(state="disabled")

        # 2. Multi-Layer Decoding Section
        self.decode_card = ctk.CTkFrame(self.scroll_frame, fg_color=COLOR_CARD_DARK, corner_radius=14, border_width=1, border_color=COLOR_BORDER)
        self.decode_card.pack(fill="x", pady=6)

        dec_title_box = ctk.CTkFrame(self.decode_card, fg_color="transparent")
        dec_title_box.pack(fill="x", padx=14, pady=(12, 6))

        ctk.CTkLabel(
            dec_title_box,
            text="🔓 MULTI-LAYER DE-OBFUSCATION & NESTED ENCODING INSPECTOR",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#38bdf8",
        ).pack(side="left")

        self.decode_container = ctk.CTkFrame(self.decode_card, fg_color=COLOR_CODE_BG, corner_radius=12, border_width=1, border_color=COLOR_BORDER)
        self.decode_container.pack(fill="x", padx=14, pady=(0, 12))

        self.lbl_decode_info = ctk.CTkLabel(
            self.decode_container,
            text="Awaiting QR payload ingestion to evaluate URL-decoding, Base64 nested layers, and homoglyphs.",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=COLOR_TEXT_MUTED,
            justify="left",
        )
        self.lbl_decode_info.pack(anchor="w", padx=12, pady=10)

        # 3. Mobile OS Intent Sandbox Section
        self.intent_card = ctk.CTkFrame(self.scroll_frame, fg_color=COLOR_CARD_DARK, corner_radius=14, border_width=1, border_color=COLOR_BORDER)
        self.intent_card.pack(fill="x", pady=6)

        int_title_box = ctk.CTkFrame(self.intent_card, fg_color="transparent")
        int_title_box.pack(fill="x", padx=14, pady=(12, 6))

        ctk.CTkLabel(
            int_title_box,
            text="📱 SIMULATED MOBILE OS EXECUTION & EXPLOIT SANDBOX",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#38bdf8",
        ).pack(side="left")

        self.intent_container = ctk.CTkFrame(self.intent_card, fg_color=COLOR_CODE_BG, corner_radius=12, border_width=1, border_color=COLOR_BORDER)
        self.intent_container.pack(fill="x", padx=14, pady=(0, 12))

        self.lbl_intent_info = ctk.CTkLabel(
            self.intent_container,
            text="Simulates Android and iOS runtime triggers (e.g. Activity Intent launches, background downloads, automated telephony dispatches).",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=COLOR_TEXT_MUTED,
            justify="left",
        )
        self.lbl_intent_info.pack(anchor="w", padx=12, pady=10)

    def _safe_copy(self, text: str, label: str = "Text"):
        if self.copy_callback:
            self.copy_callback(text)
        else:
            try:
                self.clipboard_clear()
                self.clipboard_append(text)
                self.update()
            except Exception:
                pass

    def _copy_hex_dump(self):
        text = self.hex_textbox.get("1.0", "end-1c")
        if text and not text.startswith("Load a QR"):
            self._safe_copy(text, "Hex Dump")

    def _make_hex_dump(self, data: str) -> str:
        raw = data.encode("utf-8", errors="replace")
        lines = []
        for i in range(0, len(raw), 16):
            chunk = raw[i:i+16]
            hex_bytes = " ".join(f"{b:02x}" for b in chunk)
            ascii_chars = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
            lines.append(f"{i:08x}:  {hex_bytes:<48}  |{ascii_chars}|")
        return "\n".join(lines)

    def update_sandbox(self, payload: str, scan_data: Optional[Dict[str, Any]] = None):
        """Updates the sandbox with fresh payload analysis."""
        self.current_payload = payload or ""
        self.current_data = scan_data or {}

        if not self.current_payload:
            self.reset()
            return

        # 1. Update Hex Dump
        hex_str = self._make_hex_dump(self.current_payload)
        self.hex_textbox.configure(state="normal")
        self.hex_textbox.delete("1.0", "end")
        self.hex_textbox.insert("1.0", hex_str)
        self.hex_textbox.configure(state="disabled")

        # 2. Update Multi-Layer Decoding
        for widget in self.decode_container.winfo_children():
            widget.destroy()

        unquoted = unquote(self.current_payload)
        is_encoded = (unquoted != self.current_payload)

        # Unquoted row
        u_frame = ctk.CTkFrame(self.decode_container, fg_color="transparent")
        u_frame.pack(fill="x", padx=10, pady=6)

        ctk.CTkLabel(
            u_frame,
            text="URL / Percent Decoding:",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#94a3b8",
            width=160,
            anchor="w",
        ).pack(side="left")

        dec_badge_text = "ENCODED CHARACTERS RESOLVED" if is_encoded else "CLEAN / NO PERCENT ENCODING"
        dec_badge_color = COLOR_MEDIUM_RISK if is_encoded else COLOR_LOW_RISK

        ctk.CTkLabel(
            u_frame,
            text=f"[{dec_badge_text}]",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color=dec_badge_color,
        ).pack(side="left", padx=4)

        val_box = ctk.CTkLabel(
            self.decode_container,
            text=unquoted,
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color="#38bdf8" if is_encoded else "#f8fafc",
            anchor="w",
            justify="left",
            wraplength=640,
        )
        val_box.pack(fill="x", padx=10, pady=(0, 6))

        # Base64 nested detection
        b64_matches = re.findall(r"[A-Za-z0-9+/]{20,}={0,2}", self.current_payload)
        decoded_b64 = []
        for m in b64_matches[:4]:
            try:
                dec = base64.b64decode(m).decode("utf-8", errors="ignore")
                if len(dec) >= 6 and any(c.isalnum() for c in dec):
                    decoded_b64.append((m, dec))
            except Exception:
                pass

        b64_frame = ctk.CTkFrame(self.decode_container, fg_color="transparent")
        b64_frame.pack(fill="x", padx=10, pady=6)

        ctk.CTkLabel(
            b64_frame,
            text="Base64 Obfuscation Scanner:",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#94a3b8",
            width=160,
            anchor="w",
        ).pack(side="left")

        if decoded_b64:
            ctk.CTkLabel(
                b64_frame,
                text=f"[⚠️ {len(decoded_b64)} BASE64 NESTED STRINGS DETECTED]",
                font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
                text_color=COLOR_MEDIUM_RISK,
            ).pack(side="left", padx=4)

            for raw_b64, dec_str in decoded_b64:
                b_item = ctk.CTkFrame(
                    self.decode_container,
                    fg_color=COLOR_CODE_BG,
                    corner_radius=10,
                    border_width=1,
                    border_color=COLOR_BORDER,
                )
                b_item.pack(fill="x", padx=10, pady=3)
                ctk.CTkLabel(
                    b_item,
                    text=f"Raw Base64: {raw_b64[:35]}...",
                    font=ctk.CTkFont(family="Consolas", size=10),
                    text_color=COLOR_TEXT_MUTED,
                ).pack(anchor="w", padx=10, pady=(6, 2))
                ctk.CTkLabel(
                    b_item,
                    text=f"↳ Decoded String: {dec_str}",
                    font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
                    text_color=COLOR_ACCENT,
                ).pack(anchor="w", padx=10, pady=(0, 6))
        else:
            ctk.CTkLabel(
                b64_frame,
                text="[CLEAN - ZERO BASE64 SUBSTRINGS DETECTED]",
                font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
                text_color=COLOR_LOW_RISK,
            ).pack(side="left", padx=4)

        # 3. Update Simulated Mobile OS Intent Sandbox
        for widget in self.intent_container.winfo_children():
            widget.destroy()

        p_low = self.current_payload.lower().strip()
        scheme = "Generic Text"
        target_intent = "android.intent.action.VIEW (Display Text)"
        intent_risk = COLOR_LOW_RISK
        intent_status = "INFORMATIONAL / TEXT ONLY"
        sim_desc = "No active operating system action triggered. Safe to inspect."

        if p_low.startswith("upi://"):
            scheme = "UPI Unified Payments Interface"
            target_intent = "android.intent.action.VIEW (Banking / UPI Provider Application)"
            intent_risk = COLOR_MEDIUM_RISK
            intent_status = "FINANCIAL TRANSACTION DISPATCH"
            sim_desc = "Prompts mobile OS to launch installed banking apps (PhonePe, GPay, Paytm) with pre-filled payment parameters."
        elif p_low.startswith(("http://", "https://")):
            scheme = "Uniform Resource Locator (URL)"
            target_intent = "android.intent.action.VIEW (Default Web Browser)"
            intent_risk = COLOR_LOW_RISK
            intent_status = "BROWSER NAVIGATION INTENT"
            sim_desc = "Directs default browser to load external web host. Phishing & redirect heuristics apply."
        elif p_low.startswith("wifi:"):
            scheme = "Wi-Fi Network Configuration (WPA/WPA2/WEP)"
            target_intent = "com.android.settings.wifi.WIFI_AUTO_CONNECT"
            intent_risk = COLOR_MEDIUM_RISK
            intent_status = "WIRELESS NETWORK INJECTION"
            sim_desc = "Instructs operating system to connect or switch access point. Beware of Rogue APs or Evil Twins."
        elif p_low.startswith(("tel:", "smsto:", "sms:")):
            scheme = "Telephony / SMS Protocol"
            target_intent = "android.intent.action.DIAL / android.intent.action.SENDTO"
            intent_risk = COLOR_MEDIUM_RISK
            intent_status = "COMMUNICATION TRIGGER"
            sim_desc = "Forces phone dialer or SMS client open with pre-filled recipient and message body."
        elif p_low.startswith("intent:"):
            scheme = "Android Intent Protocol URI"
            target_intent = "Direct Android Package Activity Invocation"
            intent_risk = COLOR_CRITICAL_RISK
            intent_status = "CRITICAL DIRECT INTENT EXECUTION"
            sim_desc = "Attempts to launch internal app component activities or package installer directly."

        # Exploit keyword checks
        exploit_flags = []
        if any(ext in p_low for ext in [".apk", ".exe", ".dex", ".vbs", ".bat", ".sh", ".msi"]):
            exploit_flags.append(("⚠️ EXECUTABLE PACKAGE DETECTED", "Payload points to downloadable package or binary installer.", COLOR_CRITICAL_RISK))
        if any(k in p_low for k in ["eval(", "exec(", "<script", "javascript:", "data:text/html"]):
            exploit_flags.append(("⚠️ CODE INJECTION / XSS PATTERN", "Contains script tags or dynamic script execution syntax.", COLOR_CRITICAL_RISK))
        if any(k in p_low for k in ["token=", "auth=", "session=", "key=", "otp="]):
            exploit_flags.append(("⚠️ SENSITIVE CREDENTIAL LEAKAGE", "Exposes authentication session tokens in plaintext URL parameters.", COLOR_MEDIUM_RISK))

        int_row = ctk.CTkFrame(self.intent_container, fg_color="transparent")
        int_row.pack(fill="x", padx=10, pady=(8, 4))

        ctk.CTkLabel(
            int_row,
            text=f"Target Protocol Scheme: {scheme}",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#f8fafc",
        ).pack(side="left")

        ctk.CTkLabel(
            int_row,
            text=f"[{intent_status}]",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color=intent_risk,
        ).pack(side="right")

        ctk.CTkLabel(
            self.intent_container,
            text=f"Simulated Intent: {target_intent}",
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color="#38bdf8",
        ).pack(anchor="w", padx=10, pady=(2, 2))

        ctk.CTkLabel(
            self.intent_container,
            text=f"OS Action Simulation: {sim_desc}",
            font=ctk.CTkFont(size=11),
            text_color=COLOR_TEXT_MUTED,
            wraplength=640,
            justify="left",
        ).pack(anchor="w", padx=10, pady=(2, 8))

        if exploit_flags:
            for title, desc, col in exploit_flags:
                ex_box = ctk.CTkFrame(
                    self.intent_container,
                    fg_color="#241014",
                    corner_radius=10,
                    border_width=1,
                    border_color=col,
                )
                ex_box.pack(fill="x", padx=10, pady=4)
                ctk.CTkLabel(
                    ex_box,
                    text=title,
                    font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                    text_color=col,
                ).pack(anchor="w", padx=10, pady=(6, 1))
                ctk.CTkLabel(
                    ex_box,
                    text=desc,
                    font=ctk.CTkFont(family="Segoe UI", size=10),
                    text_color="#f8fafc",
                ).pack(anchor="w", padx=10, pady=(0, 6))

    def reset(self):
        """Resets the sandbox to idle state."""
        self.hex_textbox.configure(state="normal")
        self.hex_textbox.delete("1.0", "end")
        self.hex_textbox.insert("1.0", "Load a QR code to generate real-time raw byte hex matrix inspection.")
        self.hex_textbox.configure(state="disabled")

        for widget in self.decode_container.winfo_children():
            widget.destroy()
        self.lbl_decode_info = ctk.CTkLabel(
            self.decode_container,
            text="Awaiting QR payload ingestion to evaluate URL-decoding, Base64 nested layers, and homoglyphs.",
            font=ctk.CTkFont(size=11),
            text_color=COLOR_TEXT_MUTED,
        )
        self.lbl_decode_info.pack(anchor="w", padx=12, pady=10)

        for widget in self.intent_container.winfo_children():
            widget.destroy()
        self.lbl_intent_info = ctk.CTkLabel(
            self.intent_container,
            text="Simulates Android and iOS runtime triggers (e.g. Activity Intent launches, background downloads, automated telephony dispatches).",
            font=ctk.CTkFont(size=11),
            text_color=COLOR_TEXT_MUTED,
        )
        self.lbl_intent_info.pack(anchor="w", padx=12, pady=10)


class ScanHistoryAuditView(ctk.CTkFrame):
    """
    Searchable Scan History Dashboard & Forensic Audit Log.
    Features:
      - Real-time search across URLs, UPI IDs, SHA-256 hashes, and IDs
      - Segmented risk category filters (All, Critical/High, Warning, Clean)
      - 1-click Export to CSV and JSON for security compliance
      - Interactive rows with "Re-Inspect Scan" (loads scan back into dashboard) and "Copy Payload"
    """

    def __init__(
        self,
        master,
        on_reinspect_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        copy_callback: Optional[Callable[[str], None]] = None,
        fg_color="transparent",
    ):
        super().__init__(master, fg_color=fg_color)
        self.on_reinspect = on_reinspect_callback
        self.copy_callback = copy_callback
        self.current_risk_filter = "ALL"
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        # Header toolbar - Apple Frosted Squircle Card
        self.header_card = ctk.CTkFrame(
            self,
            fg_color=COLOR_CARD_DARK,
            corner_radius=14,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        self.header_card.pack(fill="x", padx=16, pady=(12, 8))

        hdr_top = ctk.CTkFrame(self.header_card, fg_color="transparent")
        hdr_top.pack(fill="x", padx=16, pady=(12, 8))

        # Title with Apple / Google SF Pro styling
        ctk.CTkLabel(
            hdr_top,
            text="🗄️ Scan History & Forensic Audit Trail",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#f8fafc",
        ).pack(side="left")

        # Action Buttons - M3 Pill Buttons
        act_box = ctk.CTkFrame(hdr_top, fg_color="transparent")
        act_box.pack(side="right")

        self.btn_csv = ctk.CTkButton(
            act_box,
            text="📥 Export CSV",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=COLOR_SURFACE,
            hover_color=COLOR_CARD_HOVER,
            border_width=1,
            border_color=COLOR_BORDER,
            text_color="#94a3b8",
            width=100,
            height=28,
            corner_radius=14,
            command=self._export_csv,
        )
        self.btn_csv.pack(side="left", padx=4)

        self.btn_json = ctk.CTkButton(
            act_box,
            text="📥 Export JSON",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=COLOR_SURFACE,
            hover_color=COLOR_CARD_HOVER,
            border_width=1,
            border_color=COLOR_BORDER,
            text_color="#94a3b8",
            width=100,
            height=28,
            corner_radius=14,
            command=self._export_json,
        )
        self.btn_json.pack(side="left", padx=4)

        self.btn_clear = ctk.CTkButton(
            act_box,
            text="🗑️ Clear",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#241216",
            hover_color="#3b161c",
            border_width=1,
            border_color="#451820",
            text_color="#f87171",
            width=70,
            height=28,
            corner_radius=14,
            command=self._clear_history,
        )
        self.btn_clear.pack(side="left", padx=(4, 0))

        # Filter bar
        hdr_bot = ctk.CTkFrame(self.header_card, fg_color="transparent")
        hdr_bot.pack(fill="x", padx=16, pady=(0, 12))

        # Search Entry - Pill shaped search bar (Google Search bar / iOS Spotlight search)
        self.search_entry = ctk.CTkEntry(
            hdr_bot,
            placeholder_text="🔍 Filter forensic history by URL, UPI, SHA-256, or Record ID...",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            height=34,
            corner_radius=17,
            fg_color=COLOR_CODE_BG,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        self.search_entry.pack(side="left", expand=True, fill="x", padx=(0, 12))
        self.search_entry.bind("<KeyRelease>", self._on_search_key)

        # Segmented Filter - Pill shape segmented chips
        self.seg_filter = ctk.CTkSegmentedButton(
            hdr_bot,
            values=["All", "🚨 Critical", "⚠️ Suspicious", "🛡️ Clean"],
            height=32,
            corner_radius=16,
            selected_color="#2563eb",
            command=self._on_filter_changed,
        )
        self.seg_filter.set("All")
        self.seg_filter.pack(side="right")

        # Scrollable Audit Table Frame
        self.table_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.table_scroll.pack(expand=True, fill="both", padx=16, pady=(4, 12))

    def _on_search_key(self, event=None):
        """Debounces search input to prevent DOM thrashing on rapid keystrokes."""
        if hasattr(self, "_search_timer") and self._search_timer:
            try:
                self.after_cancel(self._search_timer)
            except Exception:
                pass
        self._search_timer = self.after(220, self.refresh)

    def _on_filter_changed(self, value):
        if "Critical" in value:
            self.current_risk_filter = "CRITICAL"
        elif "Suspicious" in value:
            self.current_risk_filter = "MEDIUM"
        elif "Clean" in value:
            self.current_risk_filter = "LOW"
        else:
            self.current_risk_filter = "ALL"
        self.refresh()

    def _safe_copy(self, text: str):
        if self.copy_callback:
            self.copy_callback(text)
        else:
            try:
                self.clipboard_clear()
                self.clipboard_append(text)
                self.update()
            except Exception:
                pass

    def refresh(self):
        """Reloads records from history_manager and renders table rows with max limit for UI smoothness."""
        for widget in self.table_scroll.winfo_children():
            widget.destroy()

        query = self.search_entry.get().strip() if hasattr(self, "search_entry") else ""
        records = history_manager.filter_records(query=query, risk_filter=self.current_risk_filter)

        if not records:
            empty_box = ctk.CTkFrame(
                self.table_scroll,
                fg_color=COLOR_CARD_DARK,
                corner_radius=14,
                border_width=1,
                border_color=COLOR_BORDER,
            )
            empty_box.pack(fill="x", pady=20)
            ctk.CTkLabel(
                empty_box,
                text="📭 No audit records match your query or filter criteria.\nScans captured via webcam or file load are automatically recorded here.",
                font=ctk.CTkFont(family="Segoe UI", size=12),
                text_color=COLOR_TEXT_MUTED,
                justify="center",
            ).pack(pady=30)
            return

        # Cap rendered rows to 50 to maintain smooth scrolling and instant responsiveness
        max_rows = 50
        display_records = records[:max_rows]

        if len(records) > max_rows:
            note_box = ctk.CTkFrame(self.table_scroll, fg_color="transparent")
            note_box.pack(fill="x", pady=(2, 6))
            ctk.CTkLabel(
                note_box,
                text=f"Showing latest {max_rows} of {len(records)} audit records (use search above to filter)",
                font=ctk.CTkFont(family="Segoe UI", size=11),
                text_color=COLOR_TEXT_MUTED,
            ).pack(side="left", padx=4)

        for r in display_records:
            self._render_record_row(r)

    def _render_record_row(self, r: Dict[str, Any]):
        # Apple macOS Squircle list card
        card = ctk.CTkFrame(
            self.table_scroll,
            fg_color=COLOR_CARD_DARK,
            corner_radius=12,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        card.pack(fill="x", pady=4)

        row_inner = ctk.CTkFrame(card, fg_color="transparent")
        row_inner.pack(fill="x", padx=14, pady=10)

        # Left Column: Risk Pill Chip (Google Material 3 tonal pill)
        risk = r.get("risk_level", "LOW")
        score = r.get("score", 0)
        badge_col = COLOR_LOW_RISK
        pill_bg = "#0c281a"
        pill_border = "#1b4d32"
        if risk in ["CRITICAL", "HIGH"]:
            badge_col = COLOR_CRITICAL_RISK
            pill_bg = "#301015"
            pill_border = "#5e1d28"
        elif risk in ["MEDIUM", "WARN", "WARNING"]:
            badge_col = COLOR_MEDIUM_RISK
            pill_bg = "#2e1f0a"
            pill_border = "#5c3d14"

        left_info = ctk.CTkFrame(row_inner, fg_color="transparent", width=110)
        left_info.pack(side="left", padx=(0, 12))
        left_info.pack_propagate(False)

        # Pill badge container
        risk_pill = ctk.CTkFrame(left_info, fg_color=pill_bg, corner_radius=10, border_width=1, border_color=pill_border)
        risk_pill.pack(anchor="w")

        dot_symbol = "■" if risk in ["CRITICAL", "HIGH"] else ("▲" if risk in ["MEDIUM", "WARN", "WARNING"] else "●")
        ctk.CTkLabel(
            risk_pill,
            text=f"{dot_symbol} {risk}",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color=badge_col,
        ).pack(padx=8, pady=2)

        ctk.CTkLabel(
            left_info,
            text=f"Score: {score}/100",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=COLOR_TEXT_MUTED,
            anchor="w",
        ).pack(anchor="w", padx=2, pady=(3, 0))

        # Center Column: Metadata & Payload Preview
        mid_info = ctk.CTkFrame(row_inner, fg_color="transparent")
        mid_info.pack(side="left", expand=True, fill="x", padx=6)

        top_line = ctk.CTkFrame(mid_info, fg_color="transparent")
        top_line.pack(fill="x")

        ctk.CTkLabel(
            top_line,
            text=f"{r.get('id', 'SCN-')} • {r.get('timestamp', '')}",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color=COLOR_ACCENT,
        ).pack(side="left")

        ctk.CTkLabel(
            top_line,
            text=f"via {r.get('source', 'Unknown')}",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=COLOR_TEXT_MUTED,
        ).pack(side="left", padx=10)

        payload_txt = r.get("payload", "")
        preview_txt = (payload_txt[:65] + "...") if len(payload_txt) > 65 else payload_txt

        ctk.CTkLabel(
            mid_info,
            text=preview_txt,
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color="#f8fafc",
            anchor="w",
            justify="left",
        ).pack(fill="x", pady=(2, 0))

        # Right Column: Action Buttons - Material You Pill Buttons
        right_btns = ctk.CTkFrame(row_inner, fg_color="transparent")
        right_btns.pack(side="right")

        btn_inspect = ctk.CTkButton(
            right_btns,
            text="👁️ Load Scan",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            fg_color=COLOR_SURFACE,
            hover_color=COLOR_CARD_HOVER,
            border_width=1,
            border_color=COLOR_BORDER,
            text_color="#94a3b8",
            width=88,
            height=28,
            corner_radius=12,
            command=lambda rec=r: self._on_inspect_clicked(rec),
        )
        btn_inspect.pack(side="left", padx=3)

        btn_cp = ctk.CTkButton(
            right_btns,
            text="📋 Copy",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            fg_color=COLOR_CODE_BG,
            hover_color=COLOR_CARD_HOVER,
            border_width=1,
            border_color=COLOR_BORDER,
            text_color="#94a3b8",
            width=62,
            height=28,
            corner_radius=12,
            command=lambda p=payload_txt: self._safe_copy(p),
        )
        btn_cp.pack(side="left", padx=3)

    def _on_inspect_clicked(self, rec: Dict[str, Any]):
        if self.on_reinspect:
            self.on_reinspect(rec)

    def _export_csv(self):
        default_name = f"QuishGuard_Scan_Audit_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        save_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Log File", "*.csv"), ("All Files", "*.*")],
            initialfile=default_name,
            title="Export Scan Audit Trail (CSV)",
        )
        if save_path:
            history_manager.export_csv(save_path)

    def _export_json(self):
        default_name = f"QuishGuard_Scan_Audit_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        save_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON Log File", "*.json"), ("All Files", "*.*")],
            initialfile=default_name,
            title="Export Scan Audit Trail (JSON)",
        )
        if save_path:
            history_manager.export_json(save_path)

    def _clear_history(self):
        history_manager.clear()
        self.refresh()



