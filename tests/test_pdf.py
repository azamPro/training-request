"""
Run this locally to visually verify the PDF fills correctly.

    python -m tests.test_pdf

Opens the generated PDF so you can check every field lands in the right place.
Tweak FIELDS coordinates in bot/pdf/filler.py if anything is off.
"""

import os
import sys
import subprocess

# Allow running from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

from bot.pdf.filler import FormData, fill_form

OUTPUT = "/tmp/test_training_form.pdf"

sample = FormData(
    full_name="عزام بن محمد العنزي",
    university_id="441012345",
    department="علوم الحاسب",
    remaining_hours="42",
    company_name="شركة أرامكو السعودية",
    signature="عزام العنزي",
)

fill_form(sample, OUTPUT)
print(f"PDF written to: {OUTPUT}")

# Open for visual inspection
if sys.platform == "darwin":
    subprocess.run(["open", OUTPUT])
elif sys.platform == "linux":
    subprocess.run(["xdg-open", OUTPUT])
