"""
Clinical Scribe Platform - Universal Health Check Script
Pings and reports live health status for all integrated microservices.
"""
import sys
import json
import urllib.request
import urllib.error

SERVICES = [
    {
        "name": "Dashboard Backend",
        "url": "http://localhost:8000/api/health",
        "expected_status": 200,
        "critical": True,
    },
    {
        "name": "Clinical NLP & Safety Service",
        "url": "http://localhost:8002/v1/health",
        "expected_status": 200,
        "critical": True,
    },
    {
        "name": "Transcription Service",
        "url": "http://localhost:8003/api/v1/health",
        "expected_status": 200,
        "critical": True,
    },
    {
        "name": "Mock EHR Service",
        "url": "http://localhost:8001/health",
        "expected_status": 200,
        "critical": False,
    },
]


def check_service(service):
    name = service["name"]
    url = service["url"]
    expected = service["expected_status"]
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ClinicalScribe-HealthCheck"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            code = resp.getcode()
            body = resp.read().decode("utf-8", errors="replace")
            try:
                data = json.loads(body)
            except Exception:
                data = body[:100]

            if code == expected:
                print(f"[ONLINE]  {name:<30} -> {url} [HTTP {code}]")
                return True
            else:
                print(f"[UNEXPECTED] {name:<30} -> {url} [HTTP {code}, expected {expected}]")
                return False
    except urllib.error.URLError as e:
        status = "[OFFLINE]" if service["critical"] else "[OPTIONAL/OFFLINE]"
        print(f"{status:<10} {name:<30} -> {url} (Error: {e.reason})")
        return False
    except Exception as e:
        print(f"[ERROR]   {name:<30} -> {url} (Exception: {e})")
        return False


def main():
    print("=" * 60)
    print(" Clinical Scribe Unified Platform - Health Verification")
    print("=" * 60)
    results = [check_service(s) for s in SERVICES]
    print("=" * 60)
    critical_ok = all(res for s, res in zip(SERVICES, results) if s["critical"])
    if critical_ok:
        print(">> Status: ALL CRITICAL SERVICES HEALTHY")
        return 0
    else:
        print(">> Status: ONE OR MORE SERVICES NOT READY")
        return 1


if __name__ == "__main__":
    sys.exit(main())
