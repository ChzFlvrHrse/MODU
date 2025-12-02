import fitz

def rasterize_page(doc: fitz.Document, page_index: int, dpi: int = 200) -> bytes:
    page = doc.load_page(page_index)

    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)

    pix = page.get_pixmap(matrix=mat, alpha=False)
    return pix.tobytes("png")

async def rasterize_pdf(pdf_path: str, dpi: int = 200, start_page: int = 0, end_page: int = None) -> list[dict[int, bytes]]:
    doc = fitz.open(pdf_path) # PyMuPDF: open the PDF file
    results: list[dict[int, bytes]] = []
    if end_page is None: # all pages
        pages = range(len(doc))
    else:
        pages = range(start_page, end_page + 1)
    for page_index in pages:
        results.append({"page_index": page_index, "bytes": rasterize_page(doc, page_index, dpi)})
    doc.close()
    return results
