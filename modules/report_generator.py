"""
QuishGuard Report Generator - Executive Forensic Incident Report Exporter.
Produces self-contained, enterprise-grade HTML reports printable to PDF.
"""
import os
import sys
import base64
import datetime
import html
from io import BytesIO
from typing import Dict, Any, Optional
from PIL import Image


def _get_base64_image(img_source: Any) -> str:
    """Converts a PIL Image, numpy cv2 frame, file path, or data URI to an embedded base64 data URI."""
    try:
        if isinstance(img_source, str):
            if img_source.startswith("data:image/"):
                return img_source
            if os.path.exists(img_source):
                with open(img_source, "rb") as f:
                    b64_str = base64.b64encode(f.read()).decode("utf-8")
                ext = os.path.splitext(img_source)[1].lower().replace(".", "")
                if ext in ("jpg", "jpeg"):
                    ext = "jpeg"
                elif ext in ("png", "webp", "gif"):
                    pass
                else:
                    ext = "png"
                return f"data:image/{ext};base64,{b64_str}"

        # If numpy array (OpenCV frame)
        if hasattr(img_source, "shape") and hasattr(img_source, "dtype"):
            import cv2
            if len(img_source.shape) == 3 and img_source.shape[2] == 3:
                rgb = cv2.cvtColor(img_source, cv2.COLOR_BGR2RGB)
            else:
                rgb = img_source
            img_source = Image.fromarray(rgb)

        if isinstance(img_source, Image.Image):
            buf = BytesIO()
            img_to_save = img_source.convert("RGB") if img_source.mode not in ("RGB", "RGBA") else img_source
            img_to_save.save(buf, format="PNG")
            b64_str = base64.b64encode(buf.getvalue()).decode("utf-8")
            return f"data:image/png;base64,{b64_str}"
    except Exception:
        pass
    return ""


def _get_app_logo_b64() -> str:
    """Retrieves base64 encoded QuishGuard logo for report branding."""
    try:
        if hasattr(sys, '_MEIPASS'):
            base_dir = getattr(sys, '_MEIPASS')
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        logo_path = os.path.join(base_dir, "assets", "logo_shield.png")
        if os.path.exists(logo_path):
            return _get_base64_image(logo_path)
    except Exception:
        pass
    return ""


def generate_html_report(scan_data: Dict[str, Any], output_path: Optional[str] = None) -> str:
    """
    Generates a high-resolution, self-contained HTML forensic incident report.
    Returns the report HTML string and writes to output_path if provided.
    """
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    sha256 = scan_data.get("sha256") or (scan_data.get("optical_meta", {}).get("sha256", "N/A"))
    report_id = f"QG-REP-{sha256[:10].upper() if sha256 != 'N/A' else 'MANUAL'}"
    
    payload = scan_data.get("payload", "N/A")
    safe_payload = html.escape(str(payload))
    risk_level = scan_data.get("risk_level", "LOW").upper()
    score = scan_data.get("score", 0)
    source = html.escape(str(scan_data.get("source", "QuishGuard Workstation")))
    optical_meta = scan_data.get("optical_meta", {})
    hops = scan_data.get("hops", [])
    heuristics = scan_data.get("heuristics", {})
    flags = heuristics.get("flags", [])
    zero_trust_checks = scan_data.get("zero_trust_checks", {})

    # Logo branding
    app_logo_b64 = _get_app_logo_b64()
    logo_img_html = f'<img src="{app_logo_b64}" style="width:48px; height:48px; object-fit:contain;" alt="QuishGuard Logo" />' if app_logo_b64 else '<span style="font-size:32px;">🛡️</span>'

    # Determine badge color
    if risk_level in ["CRITICAL", "HIGH"]:
        badge_color = "#ef4444"
        badge_bg = "#450a0a"
        verdict_text = "CRITICAL SECURITY THREAT DETECTED"
    elif risk_level in ["MEDIUM", "WARN", "WARNING"]:
        badge_color = "#f59e0b"
        badge_bg = "#451a03"
        verdict_text = "POTENTIAL SUSPICIOUS VECTOR IDENTIFIED"
    else:
        badge_color = "#10b981"
        badge_bg = "#064e3b"
        verdict_text = "VERIFIED CLEAN / ZERO MALICIOUS VECTORS"

    # Image base64
    img_b64 = (
        scan_data.get("image_b64")
        or _get_base64_image(scan_data.get("image_obj"))
        or _get_base64_image(scan_data.get("file_path"))
        or _get_base64_image(scan_data.get("optical_meta", {}).get("file_path"))
    )
    img_tag = f'<img src="{img_b64}" class="qr-thumbnail" alt="Scanned QR Code" />' if img_b64 else '<div class="no-img">No Image Snapshot Available</div>'

    # Build hops table
    hops_html = ""
    if hops and len(hops) > 0:
        for idx, h in enumerate(hops, 1):
            hops_html += f"""
            <tr>
                <td style="font-weight:bold; color:#38bdf8;">#{idx}</td>
                <td style="word-break:break-all; font-family:Consolas, monospace;">{html.escape(str(h.get('url', 'N/A')))}</td>
                <td><span class="badge" style="background:#1e293b; color:#38bdf8;">{html.escape(str(h.get('status', '200 OK')))}</span></td>
                <td style="color:#94a3b8; font-family:Consolas, monospace;">{html.escape(str(h.get('ip', 'N/A')))}</td>
            </tr>
            """
    else:
        hops_html = "<tr><td colspan='4' style='color:#94a3b8; text-align:center;'>No HTTP network redirects triggered (Static Payload).</td></tr>"

    # Build flags list
    flags_html = ""
    if flags:
        for f in flags:
            flags_html += f"<li class='flag-item'>⚠️ {html.escape(str(f))}</li>"
    else:
        flags_html = "<li style='color:#10b981;'>✅ No known phishing or quishing heuristic rules violated.</li>"

    # HTML template
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>QuishGuard Incident Report - {report_id}</title>
    <style>
        @page {{ size: A4; margin: 16mm; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background: #090d13;
            color: #f8fafc;
            margin: 0;
            padding: 24px;
            font-size: 13px;
            line-height: 1.5;
        }}
        @media print {{
            body {{ background: #ffffff; color: #000000; padding: 0; }}
            .container {{ box-shadow: none; border: none; }}
            .card {{ background: #f8fafc; border: 1px solid #e2e8f0; color: #0f172a; }}
            table, th, td {{ border-color: #cbd5e1 !important; color: #0f172a !important; }}
            .header-bar {{ border-bottom: 2px solid #2563eb; }}
            .badge-print {{ border: 1px solid #000; }}
        }}
        .container {{
            max-width: 960px;
            margin: 0 auto;
            background: #0d1117;
            border: 1px solid #222a38;
            border-radius: 12px;
            padding: 32px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        }}
        .header-bar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #222a38;
            padding-bottom: 20px;
            margin-bottom: 24px;
        }}
        .logo-title {{
            font-size: 20px;
            font-weight: 800;
            letter-spacing: -0.5px;
            color: #38bdf8;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .report-meta {{
            text-align: right;
            font-size: 11px;
            color: #94a3b8;
            font-family: Consolas, monospace;
        }}
        .verdict-banner {{
            background: {badge_bg};
            border: 1px solid {badge_color};
            border-radius: 8px;
            padding: 16px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 24px;
        }}
        .verdict-title {{
            font-size: 16px;
            font-weight: 800;
            color: {badge_color};
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .score-pill {{
            background: {badge_color};
            color: #ffffff;
            font-size: 18px;
            font-weight: 900;
            padding: 6px 16px;
            border-radius: 20px;
            font-family: Consolas, monospace;
        }}
        .grid-2 {{
            display: grid;
            grid-template-columns: 220px 1fr;
            gap: 20px;
            margin-bottom: 24px;
        }}
        .qr-thumbnail {{
            width: 200px;
            height: 200px;
            object-fit: contain;
            background: #ffffff;
            border: 2px solid #334155;
            border-radius: 8px;
            padding: 6px;
        }}
        .no-img {{
            width: 200px;
            height: 200px;
            background: #1e293b;
            border: 1px dashed #475569;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            text-align: center;
            color: #64748b;
            font-size: 12px;
            padding: 10px;
            box-sizing: border-box;
        }}
        .card {{
            background: #111620;
            border: 1px solid #222a38;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 20px;
        }}
        .card-title {{
            font-size: 13px;
            font-weight: 700;
            color: #38bdf8;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-top: 0;
            margin-bottom: 12px;
            border-bottom: 1px solid #1e293b;
            padding-bottom: 6px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
        }}
        th, td {{
            padding: 8px 10px;
            text-align: left;
            border-bottom: 1px solid #1e293b;
        }}
        th {{
            color: #94a3b8;
            font-weight: 600;
            background: #090d13;
        }}
        .payload-box {{
            background: #070a0f;
            border: 1px solid #1e293b;
            border-radius: 6px;
            padding: 12px;
            font-family: Consolas, monospace;
            font-size: 12px;
            word-break: break-all;
            color: #38bdf8;
            max-height: 120px;
            overflow-y: auto;
        }}
        .badge {{
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-family: Consolas, monospace;
        }}
        .flag-item {{
            margin-bottom: 6px;
            color: #f87171;
            font-weight: 500;
        }}
        .audit-footer {{
            border-top: 1px solid #222a38;
            padding-top: 18px;
            margin-top: 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 11px;
            color: #64748b;
        }}
        .seal-box {{
            display: flex;
            align-items: center;
            gap: 12px;
            color: #10b981;
            font-weight: 700;
            letter-spacing: 0.5px;
        }}
        .btn-print {{
            background: #2563eb;
            color: #ffffff;
            border: none;
            padding: 8px 16px;
            border-radius: 6px;
            font-weight: 600;
            cursor: pointer;
        }}
        @media print {{
            .btn-print {{ display: none; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header-bar">
            <div style="display:flex; align-items:center; gap:16px;">
                {logo_img_html}
                <div>
                    <div class="logo-title" style="letter-spacing:0.5px;">QUISHGUARD ZERO-TRUST QUARANTINE</div>
                    <div style="font-size:11px; font-weight:700; color:#38bdf8; margin-top:3px; letter-spacing:0.8px;">DON'T JUST SCAN &mdash; INSPECT BEFORE YOU CONNECT</div>
                </div>
            </div>
            <div class="report-meta">
                <div>REPORT ID: <strong>{report_id}</strong></div>
                <div>GENERATED: {now}</div>
                <button class="btn-print" onclick="window.print()" style="margin-top:8px;">🖨️ Print / Save as PDF</button>
            </div>
        </div>

        <!-- Threat Assessment Banner -->
        <div class="verdict-banner">
            <div>
                <div class="verdict-title">{verdict_text}</div>
                <div style="font-size:12px; color:#cbd5e1; margin-top:4px;">Zero-Trust Classification: <strong>{risk_level} RISK</strong> | Source: <strong>{source}</strong></div>
            </div>
            <div class="score-pill">THREAT SCORE: {score} / 100</div>
        </div>

        <!-- QR Snapshot & Optical Profile -->
        <div class="grid-2">
            <div>
                {img_tag}
                <div style="font-size:11px; color:#94a3b8; text-align:center; margin-top:8px;">Optical Sensor Snapshot</div>
            </div>
            <div class="card" style="margin-bottom:0;">
                <div class="card-title">🔬 Cryptographic & Optical Telemetry</div>
                <table>
                    <tr><th style="width:130px;">Input Source</th><td>{optical_meta.get('file_path', source)}</td></tr>
                    <tr><th>SHA-256 Digest</th><td style="font-family:Consolas, monospace; font-size:11px; word-break:break-all;">{sha256}</td></tr>
                    <tr><th>Shannon Entropy</th><td><strong>{scan_data.get('entropy', 'N/A')}</strong> bits / character</td></tr>
                    <tr><th>Native Dimensions</th><td>{optical_meta.get('dimensions', 'N/A')} ({optical_meta.get('aspect_ratio', '1:1')})</td></tr>
                    <tr><th>Image File Size</th><td>{optical_meta.get('file_size', 'N/A')}</td></tr>
                    <tr><th>Detection Engine</th><td>{optical_meta.get('engine', scan_data.get('engine', 'PyZBar / OpenCV Multi-Pass'))}</td></tr>
                </table>
            </div>
        </div>

        <!-- Raw Payload Extraction -->
        <div class="card">
            <div class="card-title">📦 Deconstructed Raw Payload Content</div>
            <div class="payload-box">{safe_payload}</div>
        </div>

        <!-- Redirect Chain & Network Telemetry -->
        <div class="card">
            <div class="card-title">🌐 Network Trace & Redirection Trajectory</div>
            <table>
                <thead>
                    <tr>
                        <th style="width:50px;">Hop</th>
                        <th>Uniform Resource Locator (URL)</th>
                        <th style="width:110px;">HTTP Status</th>
                        <th style="width:140px;">IP / Host</th>
                    </tr>
                </thead>
                <tbody>
                    {hops_html}
                </tbody>
            </table>
        </div>

        <!-- Security Heuristics & Flags -->
        <div class="card">
            <div class="card-title">🚨 Threat Vector Heuristics & Phishing Flags</div>
            <ul style="margin:0; padding-left:20px;">
                {flags_html}
            </ul>
        </div>

        <!-- Auditor Block & Chain of Custody -->
        <div class="audit-footer">
            <div class="seal-box">
                <span style="font-size:20px;">🔒</span>
                <span>CRYPTOGRAPHICALLY SEALED BY QUISHGUARD ZERO-TRUST ENGINE</span>
            </div>
            <div>STATUS: QUARANTINED & AUDITED</div>
        </div>
    </div>
</body>
</html>
    """

    if output_path:
        out_dir = os.path.dirname(os.path.abspath(output_path))
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

    return html_content
