"""
Network Tracer - Safe URL redirect hop tracing and network inspection.
"""
from typing import Dict, Any, Optional
from urllib.parse import urlparse
import requests
import urllib3

# Suppress insecure request warnings if user or target triggers unverified SSL certs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DESKTOP_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)


def trace_url(target_url: str, max_hops: int = 5, timeout: int = 5) -> Dict[str, Any]:
    """
    Safely traces redirect hops for a given URL without executing scripts or rendering pages.
    Enforces protocol validation (http/https), custom User-Agent, hop limit, and robust error handling.
    
    Returns:
        {
            "initial_url": str,
            "final_url": str,
            "hops": list[dict],
            "redirect_count": int,
            "error": str | None
        }
    """
    result: Dict[str, Any] = {
        "initial_url": target_url,
        "final_url": target_url,
        "hops": [],
        "redirect_count": 0,
        "error": None,
    }

    parsed = urlparse(target_url)
    if parsed.scheme not in ("http", "https"):
        result["error"] = f"Unsupported or missing URL scheme: '{parsed.scheme}'. Only http:// and https:// are permitted."
        return result

    current_url = target_url
    session = requests.Session()
    session.headers.update({
        "User-Agent": DESKTOP_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    })

    try:
        for hop_index in range(1, max_hops + 1):
            try:
                # Perform HEAD request first; if rejected with 405/501, fallback to GET (stream=True)
                try:
                    response = session.head(
                        current_url,
                        allow_redirects=False,
                        timeout=timeout,
                        verify=True,
                    )
                    if response.status_code in (405, 501):
                        response.close()
                        response = session.get(
                            current_url,
                            allow_redirects=False,
                            timeout=timeout,
                            stream=True,
                            verify=True,
                        )
                except (requests.exceptions.SSLError, requests.exceptions.Timeout, requests.exceptions.ConnectionError):
                    raise
                except requests.exceptions.RequestException:
                    response = session.get(
                        current_url,
                        allow_redirects=False,
                        timeout=timeout,
                        stream=True,
                        verify=True,
                    )

                status_code = response.status_code
                next_url = response.headers.get("Location")
                response.close()

                # If relative redirect, build absolute URL
                if next_url:
                    next_url = requests.compat.urljoin(current_url, next_url)

                hop_record = {
                    "hop_number": hop_index,
                    "status_code": status_code,
                    "from_url": current_url,
                    "to_url": next_url or current_url,
                }
                result["hops"].append(hop_record)

                # Check if it's a redirect status code
                if 300 <= status_code < 400 and next_url:
                    result["redirect_count"] += 1
                    current_url = next_url
                    result["final_url"] = current_url
                    continue
                else:
                    result["final_url"] = current_url
                    break

            except requests.exceptions.SSLError as ssl_err:
                # Retry with verify=False to inspect self-signed or invalid cert destinations, but log error
                result["error"] = f"SSL Certificate Verification Failed: {ssl_err}"
                hop_record = {
                    "hop_number": hop_index,
                    "status_code": 0,
                    "from_url": current_url,
                    "to_url": current_url,
                }
                result["hops"].append(hop_record)
                break
            except requests.exceptions.Timeout:
                result["error"] = f"Connection timed out ({timeout}s limit reached) at hop {hop_index}."
                break
            except requests.exceptions.ConnectionError as conn_err:
                result["error"] = f"Connection failed at hop {hop_index}: {conn_err}"
                break
            except requests.exceptions.RequestException as req_err:
                result["error"] = f"Network inspection error: {req_err}"
                break

        if result["redirect_count"] >= max_hops:
            result["error"] = f"Exceeded maximum hop count limit ({max_hops}). Possible redirect loop."

    finally:
        session.close()

    return result
