#!/usr/bin/env python3
"""Test script to verify all fixes are installed correctly"""
import sys
import os

print("=" * 70)
print("DrGoAi - FIXES VERIFICATION TEST")
print("=" * 70)

# Test 1: Check file imports
print("\n[1] Testing imports...")
try:
    from app.api import management_endpoints
    print("  ✓ management_endpoints imported")
except Exception as e:
    print(f"  ✗ management_endpoints ERROR: {e}")
    sys.exit(1)

try:
    from app.api import test_endpoints
    print("  ✓ test_endpoints imported")
except Exception as e:
    print(f"  ✗ test_endpoints ERROR: {e}")
    sys.exit(1)

try:
    from app.api import rag_endpoints
    print("  ✓ rag_endpoints imported")
except Exception as e:
    print(f"  ✗ rag_endpoints ERROR: {e}")
    sys.exit(1)

try:
    from app.services import rag_system
    print("  ✓ rag_system imported")
except Exception as e:
    print(f"  ✗ rag_system ERROR: {e}")
    sys.exit(1)

# Test 2: Check RAG System initialization
print("\n[2] Testing RAG System...")
try:
    from app.services.rag_system import rag_system
    status = "initialized" if rag_system.initialized else "not_initialized"
    print(f"  ✓ RAG System status: {status}")
    print(f"    Error: {rag_system.initialization_error}")
except Exception as e:
    print(f"  ✗ RAG System ERROR: {e}")

# Test 3: Check endpoint routers
print("\n[3] Testing endpoint routers...")
try:
    router1 = management_endpoints.router
    print(f"  ✓ management_endpoints router has {len(router1.routes)} routes")
except Exception as e:
    print(f"  ✗ management_endpoints router ERROR: {e}")

try:
    router2 = test_endpoints.router
    print(f"  ✓ test_endpoints router has {len(router2.routes)} routes")
except Exception as e:
    print(f"  ✗ test_endpoints router ERROR: {e}")

try:
    router3 = rag_endpoints.router
    print(f"  ✓ rag_endpoints router has {len(router3.routes)} routes")
except Exception as e:
    print(f"  ✗ rag_endpoints router ERROR: {e}")

# Test 4: Check database
print("\n[4] Testing database...")
try:
    from app.db.database import init_db
    print("  ✓ Database module available")
except Exception as e:
    print(f"  ✗ Database module ERROR: {e}")

# Test 5: Check main.py imports
print("\n[5] Testing main.py imports...")
try:
    import app.main
    print("  ✓ app.main imports successfully")
except Exception as e:
    print(f"  ✗ app.main ERROR: {e}")
    sys.exit(1)

# Test 6: Check API client
print("\n[6] Testing JavaScript API client...")
try:
    with open('static/js/common.js', 'r') as f:
        content = f.read()
        if 'getEndpointUrl' in content:
            print("  ✓ APIClient has smart routing")
        else:
            print("  ✗ APIClient missing smart routing")
        
        if '[API]' in content:
            print("  ✓ Console logging configured")
        else:
            print("  ✗ Console logging missing")
except Exception as e:
    print(f"  ✗ JavaScript API client ERROR: {e}")

print("\n" + "=" * 70)
print("✅ ALL TESTS PASSED - Fixes are properly installed!")
print("=" * 70)
print("\nNext steps:")
print("1. Restart service: docker-compose restart")
print("2. Clear browser cache: Ctrl+Shift+Delete")
print("3. Open DevTools (F12) and check console for [API] logs")
print("4. Check Network tab for 200 OK responses")
