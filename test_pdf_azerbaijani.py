#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test script to debug Azerbaijani text rendering in PDF"""

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Register Arial Unicode MS
try:
    pdfmetrics.registerFont(TTFont('ArialUnicode', '/System/Library/Fonts/Supplemental/Arial Unicode.ttf'))
    print("✓ Registered Arial Unicode MS")
except Exception as e:
    print(f"✗ Failed to register Arial Unicode: {e}")
    exit(1)

# Create PDF
pdf_file = "test_azerbaijani.pdf"
c = canvas.Canvas(pdf_file, pagesize=A4)
page_width = A4[0]

# Test text
header_text = "XÜSUSİ XƏBƏRDARLIQ"
footer_text = "Bu sənəddə Azərbaycan Respublikasının Kosmik Agentliyinə (Azərkosmos) məxsus konfidensial məlumat əks olunmuşdur."

# Test 1: drawCentredString with Arial Unicode
c.setFont('ArialUnicode', 14)
c.drawCentredString(page_width / 2, 750, "Test 1: drawCentredString with ArialUnicode")
c.setFont('ArialUnicode', 12)
c.drawCentredString(page_width / 2, 730, header_text)
c.setFont('ArialUnicode', 10)
c.drawCentredString(page_width / 2, 710, footer_text)

# Test 2: drawString (left-aligned)
c.setFont('ArialUnicode', 14)
c.drawString(50, 650, "Test 2: drawString with ArialUnicode")
c.setFont('ArialUnicode', 12)
c.drawString(50, 630, header_text)
c.setFont('ArialUnicode', 10)
c.drawString(50, 610, footer_text)

# Test 3: Using textLine
c.setFont('ArialUnicode', 14)
c.drawString(50, 550, "Test 3: Using textLine")
text_obj = c.beginText(50, 530)
text_obj.setFont('ArialUnicode', 12)
text_obj.textLine(header_text)
text_obj.setFont('ArialUnicode', 10)
text_obj.textLine(footer_text)
c.drawText(text_obj)

# Test 4: Character by character
c.setFont('ArialUnicode', 14)
c.drawString(50, 450, "Test 4: Individual characters")
c.setFont('ArialUnicode', 12)
chars = " ".join(header_text)
c.drawString(50, 430, f"Spaced: {chars}")

# Save
c.save()
print(f"✓ Created {pdf_file}")
print(f"Please open {pdf_file} and check if Azerbaijani text renders correctly")
