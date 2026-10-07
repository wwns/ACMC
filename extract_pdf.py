import sys
from pathlib import Path
pdf_path = Path(r"C:\Users\wiesl\ACMC\Bramka AC Mobile Control (SYNG1030HA-BMS) Instrukcja instalacji_PL.pdf")
out_path = Path(r"C:\Users\wiesl\ACMC\acmc_pdf_text.txt")

try:
    try:
        from pypdf import PdfReader as Reader
    except Exception:
        try:
            from PyPDF2 import PdfReader as Reader
        except Exception:
            import subprocess
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pypdf'])
            from pypdf import PdfReader as Reader

    reader = Reader(str(pdf_path))
    texts = []
    for p in reader.pages:
        try:
            texts.append(p.extract_text() or "")
        except Exception:
            texts.append("")
    out_path.write_text("\n\n----PAGE----\n\n".join(texts), encoding='utf-8')
    print('Wypisano tekst do', out_path)
except Exception as e:
    print('Błąd:', e)
    sys.exit(1)
