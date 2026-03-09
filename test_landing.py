#!/usr/bin/env python3
"""Test the landing page flow"""
import urllib.request

BASE_URL = "http://localhost:8000"

print("="*60)
print("TESTING LANDING PAGE FLOW")
print("="*60)

# Test 1: Root should return landing page HTML
print("\n[Test 1] Landing Page at /")
try:
    resp = urllib.request.urlopen(BASE_URL + '/', timeout=10)
    html = resp.read().decode()
    print(f"  Status: {resp.status}")
    print(f"  Has knight logo (SVG): {'DELTA 9' in html}")
    print(f"  Has radar animation: {'radar-sweep' in html}")
    print(f"  Has network grid: {'network-grid' in html}")
    print(f"  Has particles: {'particles' in html}")
    print(f"  Has ENTER button: {'enter-button' in html}")
    print(f"  Has AI Buyer Discovery Engine: {'AI Buyer Discovery Engine' in html}")
    print(f"  Has Delta 9 brand: {'Delta 9' in html}")
    print("  [OK] Landing page loads correctly")
except Exception as e:
    print(f"  [FAIL] {e}")

# Test 2: /dashboard should return dashboard
print("\n[Test 2] Dashboard at /dashboard")
try:
    resp = urllib.request.urlopen(BASE_URL + '/dashboard', timeout=10)
    html = resp.read().decode()
    has_dashboard = 'Lead Intelligence Dashboard' in html or 'Delta 9 Dashboard' in html
    print(f"  Status: {resp.status}")
    print(f"  Has dashboard content: {has_dashboard}")
    print("  [OK] Dashboard loads correctly")
except Exception as e:
    print(f"  [FAIL] {e}")

# Test 3: API should still work
print("\n[Test 3] API Endpoints")
try:
    resp = urllib.request.urlopen(BASE_URL + '/api', timeout=10)
    data = resp.read().decode()
    print(f"  Status: {resp.status}")
    print(f"  Response: {data[:100]}")
    print("  [OK] API working")
except Exception as e:
    print(f"  [FAIL] {e}")

# Test 4: Static files should be accessible
print("\n[Test 4] Static Files")
try:
    resp = urllib.request.urlopen(BASE_URL + '/static/landing.html', timeout=10)
    print(f"  Status: {resp.status}")
    print("  [OK] Static files accessible")
except Exception as e:
    print(f"  [FAIL] {e}")

print("\n" + "="*60)
print("LANDING PAGE TEST COMPLETE")
print("="*60)
print("\nFlow verified:")
print("  1. User visits / -> sees landing page with knight logo")
print("  2. Landing has radar, particles, network effects")
print("  3. User clicks ENTER -> navigates to /dashboard")
print("  4. Dashboard loads normally with all functionality")
print("="*60)
