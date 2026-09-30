# 📦 Packages & Extensions Needed

QuishGuard Desktop ko develop, modify ya run karne ke liye jo Python Packages aur VS Code / IDE Extensions chahiye, unki complete list yahan hai.

---

## 1. 🐍 Python Packages & Dependencies

Yeh saare packages `requirements.txt` me pinned hain.

### Ek command me install karne ke liye:
```bash
pip install -r requirements.txt
```

### Packages List & Unka Purpose:

| Package | Minimum Version | Kis Kaam Aata Hai? |
| :--- | :--- | :--- |
| **`customtkinter`** | `>=5.2.2` | Modern, clean dark-mode desktop GUI interface (widgets, buttons, tabs, banners) |
| **`pillow`** (PIL) | `>=10.3.0` | QR image files ko read karne, resize karne aur GUI me display karne ke liye |
| **`opencv-python`** | `>=4.9.0.80` | Real-time webcam video capture, computer vision CLAHE enhancement, aur QR fallback detection |
| **`pyzbar`** | `>=0.1.9` | Ultra-fast barcode & QR matrix barcode decoder library |
| **`requests`** | `>=2.32.0` | Safe HTTP redirect hops tracing (browser User-Agent, headers inspect karne ke liye) |
| **`python-Levenshtein`** | `>=0.25.1` | Typosquatting detection algorithm (fake domain brand distance calculate karta hai) |
| **`tldextract`** | `>=5.1.2` | Subdomain, primary domain aur TLDs (e.g. `.xyz`, `.com`, `.bank`) ko accurately separate karne ke liye |
| **`pyinstaller`** | `>=6.5.0` | Standalone `.exe` file compile karne ke liye |

---

## 2. 🧩 Recommended VS Code Extensions

Agar aap VS Code ya Antigravity IDE me code modify kar rahe hain, toh yeh extensions install karne chahiye:

### 1. **Python** (by Microsoft)
- **Extension ID**: `ms-python.python`
- **Purpose**: Python language support, code autocomplete, intellisense, inline documentation, aur syntax highlighting.

### 2. **Pylance** (by Microsoft)
- **Extension ID**: `ms-python.vscode-pylance`
- **Purpose**: Superfast type checking, auto-imports, aur parameter hover suggestions.

### 3. **autoDocstring - Python Docstring Generator**
- **Extension ID**: `njpwerner.autodocstring`
- **Purpose**: Python functions ke liye standard Google/Sphinx format docstrings generate karne ke liye.

### 4. **Batch Runner** (by NPE)
- **Extension ID**: `npe.batch-runner`
- **Purpose**: `build_exe.bat` jaise batch scripts ko editor ke andar se 1-click me run karne ke liye.

### 5. **Markdown All in One**
- **Extension ID**: `yzhang.markdown-all-in-one`
- **Purpose**: `README.md` aur `HOW_TO_RUN.md` jaise documents ko preview aur format karne ke liye.

---

## 3. ⚙️ System Requirements

- **Operating System**: Windows 10 / 11 (64-bit)
- **Python Version**: Python 3.10, 3.11, 3.12, 3.13, ya 3.14
- **Hardware Requirement**:
  - Webcam / Camera (agar real-time live QR scanning feature use karna hai).
  - Standalone `.exe` chalane ke liye kisi Python ya third-party installation ki zaroorat nahi hai.
