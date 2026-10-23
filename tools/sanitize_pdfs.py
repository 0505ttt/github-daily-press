#!/usr/bin/env python3
"""只清理公开副本的 PDF 元数据和本地文件链接，不改原始资料。"""
from pathlib import Path
import os
import tempfile
from pypdf import PdfReader, PdfWriter


def sanitize(directory: Path) -> int:
    count = 0
    for path in sorted(directory.glob("*.pdf")):
        reader = PdfReader(path)
        writer = PdfWriter()
        writer.append_pages_from_reader(reader)
        writer.add_metadata({"/Title": path.stem, "/Creator": "GitHub 每日项目推送 · 公开史料"})
        for page in writer.pages:
            if "/AA" in page:
                del page["/AA"]
            for ref in list(page.get("/Annots", [])):
                annotation = ref.get_object()
                action = annotation.get("/A")
                if action:
                    action = action.get_object()
                    uri = str(action.get("/URI", ""))
                    if str(action.get("/S")) != "/URI" or not uri.startswith(("https://", "http://")):
                        del annotation["/A"]
        fd, name = tempfile.mkstemp(suffix=".pdf", dir=path.parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                writer.write(stream)
            os.replace(name, path)
        finally:
            Path(name).unlink(missing_ok=True)
        count += 1
    return count


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    print("已清理公开副本 PDF 元数据：", sanitize(root / "GitHub项目分析"))
