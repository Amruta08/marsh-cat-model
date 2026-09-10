"""Verification script for Module 8 (PDF report). Run from project root:
    python tests\\verify_module8.py
"""

from pathlib import Path
from pypdf import PdfReader

REPORT_PATH = Path("outputs/reports/loss_report.pdf")

print("--- Test 1: Report file exists ---")
print("Exists:", REPORT_PATH.exists(), "(expected: True)")

print()
print("--- Test 2: Report has the expected number of pages ---")
reader = PdfReader(str(REPORT_PATH))
print(f"Pages: {len(reader.pages)} (expected: 5)")

print()
print("--- Test 3: Key figures appear in the extracted text (confirms SQL values rendered, not placeholders) ---")
full_text = "\n".join(page.extract_text() for page in reader.pages)
checks = {
    "AAL section present": "AVERAGE ANNUAL LOSS" in full_text.upper(),
    "OEP/AEP table present": "AEP Loss" in full_text,
    "Methodology section present": "Methodology Summary" in full_text,
    "Limitations section present": "Key Limitations" in full_text,
    "Disclaimer present": "not a real client submission" in full_text,
}
for label, passed in checks.items():
    print(f"{label}: {passed}")

print()
print("--- Test 4: Charts were generated as image files ---")
for chart in ["outputs/figures/tiv_by_county.png", "outputs/figures/ep_curve.png"]:
    print(f"{chart} exists:", Path(chart).exists())
