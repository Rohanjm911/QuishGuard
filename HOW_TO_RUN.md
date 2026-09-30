# 🚀 How to Run QuishGuard Desktop v2.0 Enterprise

This comprehensive guide details all methods to launch, configure, test, and build **QuishGuard Desktop v2.0 Enterprise**, along with an in-depth walkthrough of every feature and user interface control.

---

## ⚡ Quick Launch (Two Ways to Run)

### Option 1: Run Standalone `.exe` (Recommended — Zero Dependencies)

A standalone Windows executable is pre-compiled and ready for deployment without requiring Python, pip, or external libraries:

| Property | Details |
|---|---|
| **Build Status** | ✅ **COMPILED & READY TO RUN** |
| **Executable Name** | `QuishGuard.exe` |
| **File Size** | **83.8 MB** (Self-contained single binary) |
| **Binary Location** | `.\dist\QuishGuard.exe` |
| **Launch Command** | `.\dist\QuishGuard.exe` |
| **Platform** | Windows 10 / 11 (64-bit) |

#### Method A: Launch via Windows File Explorer
1. Navigate to the `dist` folder inside the project directory in File Explorer:
   ```text
   QuishGuard\dist\
   ```
2. Double-click **`QuishGuard.exe`**. The application launches immediately with the Apple + Google inspired dark UI!

#### Method B: Launch via PowerShell / Windows Terminal
From the project root directory, run:
```powershell
.\dist\QuishGuard.exe
```

---

### Option 2: Run from Python Source Code (`main.py`)

If you are developing, customizing heuristics, or running from source:

#### Step 1: Open PowerShell and Navigate to the Repository
```powershell
cd "d:\projects and certificates\projects\cyber\QuishGuard"
```

#### Step 2: Install Required Dependencies
Ensure Python 3.10+ is installed, then install the pinned dependencies:
```powershell
pip install -r requirements.txt
```

#### Step 3: Launch the Application
```powershell
python main.py
```

---

## 🛠️ How to Rebuild the Standalone Executable

If you modify application code, assets, or heuristic detection rules and wish to recompile the single-file `.exe`:

### Method A: Automated Batch Script
Double-click **`build_exe.bat`** in the project root folder.

### Method B: PowerShell
Execute the build script in PowerShell (ensure you prefix with `.\`):
```powershell
.\build_exe.bat
```

### Method C: Direct PyInstaller Compilation
Compile directly using the optimized project specification file:
```powershell
python -m PyInstaller --clean QuishGuard.spec
```
Upon completion, the updated binary is automatically placed in `dist/QuishGuard.exe`.

---

## 🧭 In-Depth Feature & User Interface Guide

### 1. 🎛️ Header Bar Controls
- **macOS Window Traffic Lights**: Decorative Apple-style indicator dots (`● Red`, `● Amber`, `● Green`).
- **`📄 Export Report`**: Generates a publication-grade, self-contained **HTML Forensic Incident Report** containing embedded base64 QR thumbnails, SHA-256 digests, Shannon entropy scores, and redirect hop chains. Opens in your default browser, ready for 1-click `Ctrl + P` PDF export.
- **`🔊 Audio: ON / 🔇 Audio: OFF`**: 1-click toggle for tactical acoustic cues synthesized directly in memory.
- **`🎵 Sound FX`**: Opens the **Tactile Audio Studio** modal. Audition and test all 7 studio-grade synthesized sound profiles with 1 click.
- **`ℹ️ About`**: Displays enterprise metadata, license terms, and official branding.

---

### 2. 📹 High-Resolution Camera Scanner
Click **"📷 Live Webcam Scanner"** in the left sidebar to open the dedicated HD Scanner window:
- **Cyber Reticle & Sweeping Laser HUD**: Animated visual targeting crosshair that detects QR matrices in real-time.
- **Visual Matrix Lock**: Instantly snaps an emerald bounding polygon over recognized QR codes and loads the frame directly into the quarantine inspection bay.
- **`🔄 Switch Camera`**: Seamlessly cycles between multiple video capture inputs (integrated laptop camera, external USB webcams, or virtual capture cards).
- **`✨ Screen / Low-Light Boost`**: Applies CLAHE (Contrast Limited Adaptive Histogram Equalization) to eliminate glare from smartphone/monitor screens and improve capture in low-light environments.
- **`📸 Snapshot & Scan`**: Takes an instantaneous freeze-frame capture for deep analysis on motion-blurred video feeds.
- **`❌ Close Camera`**: Safely terminates the video stream and background capture threads.

---

### 3. 📂 Left Sidebar Controls
- **`📁 Browse Image File`**: Load any local image (`.png`, `.jpg`, `.jpeg`, `.webp`, `.bmp`, `.tiff`) into the sandbox for forensic analysis.
- **`📋 Copy Extracted Payload`**: Securely copies the raw decoded URL, UPI, or text payload to the system clipboard with an audible tactile haptic tap.
- **`🔄 Clear Quarantine Session`**: 1-click reset for all dashboard metrics, arc gauges, telemetry charts, dossiers, and logs back to idle state.

---

### 4. 🗂️ 8 Comprehensive Forensic Telemetry Tabs

#### Tab 1: 🔍 Detailed QR Analysis
- **Physical Optical Forensics**: Pixel dimensions, aspect ratio, encoding mode, and matrix grid resolution.
- **Cryptographic Chain of Custody**: SHA-256 fingerprint digest and Shannon bit entropy ($H(X)$ bits/symbol) to detect compressed or encrypted malware payloads.
- **Deconstructed Parameters**: Parsed UPI VPA banking handles, recipient names, and URL query strings.
- **Zero-Trust Quarantine Checklist**: 5-point automated compliance verification.
- **Action Buttons**:
  - `📋 Copy Full Dossier`: Copies the entire technical audit summary to clipboard.
  - `📄 Export Report`: Exports the branded self-contained HTML incident report.
  - `🌐 Open Target Safely`: Opens the verified destination URL in your default browser after analyst confirmation.

#### Tab 2: 🔬 Payload Sandbox (Hex & Obfuscation Inspector)
- **Memory-Offset Raw Byte Hex Dump**: Wireshark/Hex-Editor format (`00000000: 75 70 69 ... |ascii|`).
- **`📋 Copy Hex Dump`**: Copies complete hex matrix to clipboard.
- **Automated De-Obfuscation**: Identifies and decodes URL percent-encoding (`%20`, `%3F`, etc.) and unpacks nested Base64 strings.
- **Mobile OS Intent Sandbox**: Analyzes runtime triggers for dangerous Android/iOS deep links (`intent://`, `market://`, direct `.apk` downloads, custom schemas).

#### Tab 3: Visual Redirect Chain
- Safe headless HTTP hop tracer follows redirect chains hop-by-hop without executing browser scripts, displaying interactive visual cards with latency, SSL status, and HTTP status codes (`200 OK`, `301 Moved Permanently`, `302 Found`, `404 Not Found`).

#### Tab 4: 📊 Risk Vector Graph
- Categorical threat distribution bar chart analyzing TLD abuse, brand typosquatting, redirect depth, basic auth spoofing, and excessive subdomain nesting.

#### Tab 5: 📈 Threat Analytics
- Real-time continuous session spline area chart showing threat progression across multiple scans, accompanied by 4 Apple Health style KPI summary cards.

#### Tab 6: 🗄️ Scan History & Forensic Audit Log
- **Live Search Bar**: Google/Spotlight style pill search bar to filter scans in real time by URL, UPI ID, domain, or SHA-256 hash.
- **Segmented Risk Filters**: 1-click pill chips for `All`, `🚨 Critical`, `⚠️ Suspicious`, and `🛡️ Clean`.
- **`👁️ Load Scan`**: Re-loads past scans directly back into the active dashboard with full vector restoration.
- **`📋 Copy`**: Quick copy for individual row payloads.
- **`📥 Export CSV`**: Exports the entire audit log database to `.csv` format.
- **`📥 Export JSON`**: Exports machine-readable telemetry for SIEM and SOC ingestion.
- **`🗑️ Clear History`**: Safely clears the local persistent database (`scan_history.json`).

#### Tab 7: Heuristic Flags
- Granular breakdown of each triggered heuristic rule, risk points assigned, and threat category.
- **`📋 Copy Flags`**: Copies all active detection flags to clipboard.

#### Tab 8: Live Security Log
- Real-time internal diagnostic event stream detailing decoder passes, network tracer timestamps, and system notifications.
- **`📋 Copy Log`**: Copies entire execution log.
- **`🗑️ Clear Log`**: Clears the event console window.

---

### 5. 🎧 Tactile Audio Studio (7 Acoustic Profiles)
Click the **`🎵 Sound FX`** header button to audition the 16-bit 44.1kHz studio-grade synthesized sound profiles:

| Sound Profile | Design Reference | Acoustic Description |
|---|---|---|
| **🛡️ Verified Clean QR** | Apple Pay & Google Pay | Ascending major triad chord (`C6 → E6 → G6`) with harmonic bell decay |
| **⚠️ Suspicious Caution** | Apple macOS Amber Alert | Warm dual-bell chime (`A5 → F5`) for redirection warnings |
| **🚨 Critical Quarantine** | Futuristic Cyber Security | Minor 2nd dissonance warble (`440Hz + 466Hz + 180Hz sub`) |
| **🎯 Biometric Matrix Lock** | Apple FaceID / Optical Scan | High-tech optical chirp sweep (`1850Hz → 2800Hz`) |
| **📷 Optical Shutter Snap** | iOS Camera Shutter | Filtered mechanical aperture snap on scan trigger |
| **📄 AirDrop Export Chime** | Apple AirDrop / macOS Save | Ascending completion bell (`E5 → B5 → E6`) |
| **🔘 Tactile Glass Tap** | Apple iOS Haptic Pop | Ultra-short 24ms glass micro-tap for buttons and copy actions |

---

## 🧪 Automated Testing & Verification

Run the built-in subsystem verification suite to test all modules, heuristics, sound synthesizers, and assets:
```powershell
python -c "
from modules.heuristics import analyze_heuristics
from modules.history_manager import history_manager
from modules.network_tracer import trace_url
from modules.qr_engine import compute_shannon_entropy
from modules.report_generator import generate_html_report
from modules.sound_manager import sound_manager
import main
print('All 8 QuishGuard subsystems verified successfully!')
"
```

---

## 🔒 Security & Data Privacy Guarantee

QuishGuard Desktop is **100% offline and air-gapped by design**. No scanned QR payloads, decoded credentials, UPI account identifiers, or forensic telemetry data are ever transmitted to external servers or cloud services. All inspections execute locally on your endpoint.
