"""
Heuristics Engine - Local offline heuristic risk scoring for URLs.
"""
from typing import Dict, Any, List
import ipaddress
import re
from urllib.parse import urlparse

try:
    import tldextract
except ImportError:
    tldextract = None

try:
    import Levenshtein
except ImportError:
    Levenshtein = None

HIGH_VALUE_TARGETS = [
    "google",
    "paypal",
    "microsoft",
    "amazon",
    "apple",
    "netflix",
    "wellsfargo",
    "chase",
    "binance",
    "coinbase",
    "sbi",
    "hdfcbank",
]

SUSPICIOUS_TLDS = {
    "xyz",
    "top",
    "buzz",
    "ru",
    "work",
    "icu",
    "gq",
    "tk",
    "cn",
}


def _is_ip_address(host: str) -> bool:
    """Checks whether the host is a raw IPv4 or IPv6 address."""
    clean_host = host.split(":")[0].strip("[]")
    try:
        ipaddress.ip_address(clean_host)
        return True
    except ValueError:
        return False


def _compute_distance(s1: str, s2: str) -> int:
    """Computes Levenshtein distance using C-extension or pure Python fallback."""
    if Levenshtein:
        return Levenshtein.distance(s1, s2)
    # Basic Wagner-Fischer algorithm fallback
    if len(s1) < len(s2):
        return _compute_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]


def analyze_heuristics(url: str, redirect_count: int = 0) -> Dict[str, Any]:
    """
    Performs comprehensive offline heuristic risk scoring on target URL.
    
    Checks:
      1. Raw IP Address Host (+35)
      2. Suspicious High-Abuse TLDs (+25)
      3. Brand Impersonation / Typosquatting (+45)
      4. Basic Auth Credentials in URL (+30)
      5. Excessive Subdomains (> 3 dots) (+10)
      6. Multi-hop redirect (> 2 hops) (+15)
      
    Returns:
      {
          "score": int (0-100),
          "verdict": "LOW" | "MEDIUM" | "CRITICAL",
          "flags": list[str]
      }
    """
    score = 0
    flags: List[str] = []

    # Normalize URL if missing scheme for accurate netloc parsing
    normalized_url = url.strip()
    if "://" not in normalized_url and not normalized_url.startswith("//"):
        normalized_url = "http://" + normalized_url

    parsed = urlparse(normalized_url)
    netloc = parsed.netloc.lower()

    # Check 4: Basic Auth Credentials in URL (e.g., https://paypal.com@malicious.com)
    if "@" in netloc or (parsed.username is not None):
        score += 30
        flags.append("Basic Auth credentials detected in URL (Possible credential spoofing/obfuscation).")

    # Clean host without username/password or port
    host = netloc.split("@")[-1].split(":")[0]

    # Check 1: Raw IP Address Host
    if _is_ip_address(host):
        score += 35
        flags.append(f"Raw IP address host detected ('{host}'). Legitimate services rarely use direct IP links.")

    # Domain extraction
    domain = ""
    subdomain = ""
    suffix = ""
    registered_domain = ""

    if tldextract:
        ext = tldextract.extract(url)
        domain = ext.domain.lower()
        subdomain = ext.subdomain.lower()
        suffix = ext.suffix.lower()
        registered_domain = ext.registered_domain.lower()
    else:
        # Fallback domain split
        parts = host.split(".")
        if len(parts) >= 2:
            suffix = parts[-1]
            domain = parts[-2]
            subdomain = ".".join(parts[:-2])
            registered_domain = f"{domain}.{suffix}"
        else:
            domain = host

    # Check 2: Suspicious High-Abuse TLDs
    if suffix:
        # Check against last part of multi-part suffix like 'ru' or whole suffix
        suffix_parts = suffix.split(".")
        if any(sp in SUSPICIOUS_TLDS for sp in suffix_parts) or suffix in SUSPICIOUS_TLDS:
            score += 25
            flags.append(f"High-abuse/suspicious top-level domain detected ('.{suffix}').")

    # Check 3: Brand Impersonation / Typosquatting
    # Check registered domain name against high value targets
    matched_brand = None
    for brand in HIGH_VALUE_TARGETS:
        if domain == brand:
            # Exact match of brand name (legitimate or exact clone on other TLD)
            pass
        else:
            dist = _compute_distance(domain, brand)
            if 0 < dist <= 2:
                matched_brand = (brand, dist)
                score += 45
                flags.append(
                    f"Possible typosquatting detected! Domain '{domain}' is distance {dist} from target brand '{brand}'."
                )
                break

    # Also check if brand is inside subdomain to disguise phishing (e.g., paypal.login-verify.com)
    if not matched_brand and subdomain:
        for brand in HIGH_VALUE_TARGETS:
            if brand in subdomain.split("."):
                score += 20
                flags.append(f"Target brand keyword '{brand}' found in subdomain ('{subdomain}').")
                break

    # Check 5: Excessive Subdomains (> 3 dot-separated subdomains)
    if subdomain:
        subdomain_depth = len(subdomain.split("."))
        if subdomain_depth > 3:
            score += 10
            flags.append(f"Excessive subdomain nesting detected ({subdomain_depth} levels). Often used to bypass filters.")

    # Check 6: Multi-hop redirect (> 2 hops)
    if redirect_count > 2:
        score += 15
        flags.append(f"Multi-hop redirect chain detected ({redirect_count} hops). Often indicative of evasive routing.")

    # Cap score at 100
    score = min(100, max(0, score))

    # Determine Verdict
    if score >= 60:
        verdict = "CRITICAL"
    elif score >= 25:
        verdict = "MEDIUM"
    else:
        verdict = "LOW"

    return {
        "score": score,
        "verdict": verdict,
        "flags": flags,
    }
