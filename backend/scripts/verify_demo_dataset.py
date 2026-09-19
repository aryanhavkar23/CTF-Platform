"""
Verification Script for OWASP CTF Platform Demo Dataset
Tests all major API endpoints against the running server.
"""

import sys
import json
import urllib.request
import urllib.error

API_BASE = "http://127.0.0.1:8000"


def make_request(path, method="GET", data=None, token=None):
    url = f"{API_BASE}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req_data = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body) if body else None
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        return e.code, json.loads(body) if body else None


def main():
    print("=" * 70)
    print(" Verifying Demo Dataset API Endpoints")
    print("=" * 70)

    # 1. Test Student Login
    print("[1] Authenticating DEMO_STUDENT_01...")
    status, res = make_request("/api/auth/login", "POST", {
        "email": "demo_student_01@owasp-ctf.org",
        "password": "DemoPass2026!"
    })
    assert status == 200, f"Student login failed: {status} {res}"
    student_token = res["access_token"]
    student_user = res["user"]
    print(f"  [OK] Login OK: {student_user['username']} ({student_user['role']})")

    # 2. Test Admin Login
    print("[2] Authenticating DEMO_ADMIN...")
    status, res = make_request("/api/auth/login", "POST", {
        "email": "demo_admin@owasp-ctf.org",
        "password": "DemoPass2026!"
    })
    assert status == 200, f"Admin login failed: {status} {res}"
    admin_token = res["access_token"]
    admin_user = res["user"]
    print(f"  [OK] Login OK: {admin_user['username']} ({admin_user['role']})")

    # 3. Test Challenges Endpoint
    print("[3] Inspecting Challenges catalog...")
    status, res = make_request("/api/challenges", token=student_token)
    assert status == 200, f"Challenges list failed: {status} {res}"
    challs = res if isinstance(res, list) else res.get("items", [])
    print(f"  [OK] Found {len(challs)} challenges available to students.")

    # 4. Test Global Leaderboard
    print("[4] Inspecting Leaderboard standings...")
    status, res = make_request("/api/leaderboard/global", token=student_token)
    assert status == 200, f"Leaderboard failed: {status} {res}"
    lb = res.get("entries", []) if isinstance(res, dict) else res
    top_standings = [(entry.get("username"), entry.get("total_points", entry.get("score"))) for entry in lb[:5]]
    print(f"  [OK] Top standings: {top_standings}")

    # 5. Test Events Endpoint
    print("[5] Inspecting Events list...")
    status, res = make_request("/api/events", token=student_token)
    assert status == 200, f"Events failed: {status} {res}"
    events = res if isinstance(res, list) else res.get("items", [])
    event_names = [e.get("name") for e in events]
    print(f"  [OK] Events registered: {len(events)} -> {event_names[:3]}")

    # 6. Test Teams Endpoint
    print("[6] Inspecting Teams...")
    status, res = make_request("/api/teams", token=student_token)
    assert status == 200, f"Teams failed: {status} {res}"
    teams = res if isinstance(res, list) else res.get("items", [])
    team_names = [t.get("name") for t in teams]
    print(f"  [OK] Teams found: {len(teams)} -> {team_names}")

    # 7. Test Student Profile & Badges
    print("[7] Inspecting Student Profile & Badges...")
    status, res = make_request("/api/profile/me", token=student_token)
    assert status == 200, f"Profile failed: {status} {res}"
    print(f"  [OK] Student profile: Points={res.get('points', res.get('total_points'))} Solves={res.get('solves_count', res.get('solve_count'))}")

    status, res = make_request("/api/badges/my", token=student_token)
    assert status == 200, f"Badges failed: {status} {res}"
    badges = res if isinstance(res, list) else res.get("items", [])
    badge_names = [b.get("name", b.get("badge", {}).get("name")) for b in badges]
    print(f"  [OK] Badges earned: {len(badges)} -> {badge_names[:4]}")

    # 8. Test Notifications
    print("[8] Inspecting Notifications...")
    status, res = make_request("/api/notifications", token=student_token)
    assert status == 200, f"Notifications failed: {status} {res}"
    notifs = res.get("items", []) if isinstance(res, dict) else res
    print(f"  [OK] Notifications found: {len(notifs)} for student.")

    # 9. Test Admin Analytics
    print("[9] Testing Admin Analytics & Anti-Cheat...")
    status, res = make_request("/api/analytics/overview", token=admin_token)
    assert status == 200, f"Analytics overview failed: {status} {res}"
    print(f"  [OK] Analytics Overview: Users={res.get('total_users')}, Solves={res.get('total_solves')}, Submissions={res.get('total_submissions')}")

    status, res = make_request("/api/anti-cheat/events", token=admin_token)
    assert status == 200, f"Anti-cheat list failed: {status} {res}"
    sec_events = res if isinstance(res, list) else res.get("items", [])
    print(f"  [OK] Anti-cheat flagged events: {len(sec_events)}")

    print("=" * 70)
    print(" All API Endpoints Verified Successfully!")
    print("=" * 70)


if __name__ == "__main__":
    main()
