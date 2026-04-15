#!/usr/bin/env python3
"""
Convert all markdown documentation files to PDF.
Uses markdown-pdf library (PyMuPDF + markdown-it-py backend).
"""

import os
import sys
from pathlib import Path

try:
    from markdown_pdf import MarkdownPdf, Section
except ImportError:
    print("Installing markdown-pdf...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "markdown-pdf", "-q"])
    from markdown_pdf import MarkdownPdf, Section


def convert_markdown_to_pdf(md_path: Path, pdf_path: Path):
    """Convert a single markdown file to PDF."""
    print(f"Converting: {md_path.name} -> {pdf_path.name}")
    
    # Read markdown content
    content = md_path.read_text(encoding='utf-8')
    
    # Remove internal markdown links that cause issues (e.g., [text](#anchor))
    import re
    # Convert internal links to plain text to avoid TOC destination errors
    content = re.sub(r'\[([^\]]+)\]\(#[^)]+\)', r'\1', content)
    
    # Create PDF with no TOC to avoid link issues
    pdf = MarkdownPdf(toc_level=0)  # Disable TOC to avoid destination errors
    pdf.add_section(Section(content, toc=False))
    pdf.meta = {
        "title": md_path.stem.replace('_', ' ').title(),
        "author": "MAF 1.0 GA POC Team",
        "subject": "Multi-Agent Framework Documentation"
    }
    pdf.save(str(pdf_path))
    print(f"  -> Saved: {pdf_path}")


def main():
    # Get docs directory
    script_dir = Path(__file__).parent
    docs_dir = script_dir / "docs"
    pdf_output_dir = script_dir / "docs" / "pdf"
    
    # Create PDF output directory
    pdf_output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all markdown files in docs/
    md_files = list(docs_dir.glob("*.md"))
    
    # Also include important root-level markdown files
    root_md_files = [
        script_dir / "README.md",
        script_dir / "ARCHITECTURE.md",
        script_dir / "FEATURE_COMPARISON.md",
        script_dir / "IMPLEMENTATION_PLAN.md",
    ]
    for root_file in root_md_files:
        if root_file.exists() and root_file not in md_files:
            md_files.append(root_file)
    
    if not md_files:
        print(f"No markdown files found in {docs_dir}")
        return
    
    print(f"Found {len(md_files)} markdown files to convert")
    print("=" * 50)
    
    success_count = 0
    error_count = 0
    
    for md_file in md_files:
        pdf_path = pdf_output_dir / f"{md_file.stem}.pdf"
        try:
            convert_markdown_to_pdf(md_file, pdf_path)
            success_count += 1
        except Exception as e:
            print(f"  ERROR converting {md_file.name}: {e}")
            error_count += 1
    
    print("=" * 50)
    print(f"Conversion complete: {success_count} succeeded, {error_count} failed")
    print(f"PDF files saved to: {pdf_output_dir}")


if __name__ == "__main__":
    main()
