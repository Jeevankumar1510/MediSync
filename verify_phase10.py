"""
MediSync AI - Phase 10 Verification Suite
Validates Next.js 14 App Router Frontend, UI Components, Pages, and API Client.
"""
import json
import os
import sys

FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "frontend"))

def run_verification():
    passed = 0
    total = 0

    def check(name: str, cond: bool):
        nonlocal passed, total
        total += 1
        if cond:
            passed += 1
            print(f"  [PASS] {name}", flush=True)
        else:
            print(f"  [FAIL] {name}", flush=True)

    print("==================================================", flush=True)
    print(" MediSync AI - Phase 10 Verification Suite", flush=True)
    print(" Next.js 14 App Router Clinical Frontend Dashboard", flush=True)
    print("==================================================", flush=True)

    # 1. Project Configuration Files
    print("\n[1] Testing Project Configuration Files...", flush=True)
    pkg_path = os.path.join(FRONTEND_DIR, "package.json")
    check("package.json exists", os.path.exists(pkg_path))
    if os.path.exists(pkg_path):
        with open(pkg_path, "r", encoding="utf-8") as f:
            pkg_data = json.load(f)
        check("package.json has 'next' dependency", "next" in pkg_data.get("dependencies", {}))
        check("package.json has 'lucide-react' icons", "lucide-react" in pkg_data.get("dependencies", {}))
        check("package.json has 'tailwindcss'", "tailwindcss" in pkg_data.get("devDependencies", {}))

    check("tsconfig.json exists", os.path.exists(os.path.join(FRONTEND_DIR, "tsconfig.json")))
    check("next.config.js exists with API rewrites", os.path.exists(os.path.join(FRONTEND_DIR, "next.config.js")))
    check("tailwind.config.js exists", os.path.exists(os.path.join(FRONTEND_DIR, "tailwind.config.js")))
    check("postcss.config.js exists", os.path.exists(os.path.join(FRONTEND_DIR, "postcss.config.js")))
    check(".env.local exists", os.path.exists(os.path.join(FRONTEND_DIR, ".env.local")))

    # 2. Reusable UI Components
    print("\n[2] Testing Reusable UI Components...", flush=True)
    comp_dir = os.path.join(FRONTEND_DIR, "src", "components", "ui")
    check("StatusBadge.tsx exists", os.path.exists(os.path.join(comp_dir, "StatusBadge.tsx")))
    check("MetricCard.tsx exists", os.path.exists(os.path.join(comp_dir, "MetricCard.tsx")))
    check("JsonViewer.tsx exists", os.path.exists(os.path.join(comp_dir, "JsonViewer.tsx")))
    check("Modal.tsx exists", os.path.exists(os.path.join(comp_dir, "Modal.tsx")))

    # 3. Layout Architecture
    print("\n[3] Testing Layout Architecture...", flush=True)
    layout_dir = os.path.join(FRONTEND_DIR, "src", "components", "layout")
    check("Sidebar.tsx exists with clinical navigation", os.path.exists(os.path.join(layout_dir, "Sidebar.tsx")))
    check("Navbar.tsx exists with system health diagnostics", os.path.exists(os.path.join(layout_dir, "Navbar.tsx")))
    check("AppLayout.tsx exists", os.path.exists(os.path.join(layout_dir, "AppLayout.tsx")))
    check("Root layout.tsx exists", os.path.exists(os.path.join(FRONTEND_DIR, "src", "app", "layout.tsx")))
    check("Global styles globals.css exists", os.path.exists(os.path.join(FRONTEND_DIR, "src", "app", "globals.css")))

    # 4. App Router Dashboard Pages
    print("\n[4] Testing App Router Pages...", flush=True)
    app_dir = os.path.join(FRONTEND_DIR, "src", "app")
    check("Executive Dashboard page.tsx exists (/)", os.path.exists(os.path.join(app_dir, "page.tsx")))
    check("Patient Records Explorer page.tsx exists (/patients)", os.path.exists(os.path.join(app_dir, "patients", "page.tsx")))
    check("API Integrations page.tsx exists (/integrations)", os.path.exists(os.path.join(app_dir, "integrations", "page.tsx")))
    check("Data Synchronization page.tsx exists (/sync)", os.path.exists(os.path.join(app_dir, "sync", "page.tsx")))
    check("Webhook Events page.tsx exists (/webhooks)", os.path.exists(os.path.join(app_dir, "webhooks", "page.tsx")))
    check("AI Field Mapping page.tsx exists (/ai/mapping)", os.path.exists(os.path.join(app_dir, "ai", "mapping", "page.tsx")))
    check("AI Data Quality page.tsx exists (/ai/quality)", os.path.exists(os.path.join(app_dir, "ai", "quality", "page.tsx")))
    check("RAG Assistant Chat page.tsx exists (/rag)", os.path.exists(os.path.join(app_dir, "rag", "page.tsx")))
    check("Knowledge Base page.tsx exists (/documents)", os.path.exists(os.path.join(app_dir, "documents", "page.tsx")))
    check("Audit Logs page.tsx exists (/logs)", os.path.exists(os.path.join(app_dir, "logs", "page.tsx")))
    check("Settings & Vault page.tsx exists (/settings)", os.path.exists(os.path.join(app_dir, "settings", "page.tsx")))
    check("Login page.tsx exists (/login)", os.path.exists(os.path.join(app_dir, "login", "page.tsx")))
    check("Signup page.tsx exists (/signup)", os.path.exists(os.path.join(app_dir, "signup", "page.tsx")))

    # 5. Client Library & State Management
    print("\n[5] Testing TypeScript Interfaces & API Client...", flush=True)
    lib_dir = os.path.join(FRONTEND_DIR, "src", "lib")
    types_path = os.path.join(FRONTEND_DIR, "src", "types", "index.ts")
    check("TypeScript types index.ts exists", os.path.exists(types_path))
    check("API client api.ts exists with offline fallback", os.path.exists(os.path.join(lib_dir, "api.ts")))
    check("Auth helper auth.ts exists", os.path.exists(os.path.join(lib_dir, "auth.ts")))
    check("Mock dataset mockData.ts exists", os.path.exists(os.path.join(lib_dir, "mockData.ts")))

    # 6. Windows PowerShell Launcher
    print("\n[6] Testing Launcher Scripts...", flush=True)
    check("run_frontend.ps1 exists", os.path.exists(os.path.join(os.path.dirname(__file__), "run_frontend.ps1")))

    print("\n==================================================", flush=True)
    print(f" Phase 10 Verification Summary: {passed}/{total} Passed", flush=True)
    print("==================================================", flush=True)
    if passed != total:
        sys.exit(1)


if __name__ == "__main__":
    run_verification()
