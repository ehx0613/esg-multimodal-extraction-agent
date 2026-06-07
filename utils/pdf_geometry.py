from pathlib import Path
from typing import Any, Iterable

import fitz


def bbox_to_pdf_rect(
    bbox: Iterable[Any],
    page_rect: fitz.Rect,
    *,
    expand_points: float = 24.0,
    coordinate_space: str = "auto",
) -> fitz.Rect:
    values = [float(value) for value in bbox]
    if len(values) != 4:
        raise ValueError("bbox must contain four coordinates")
    x0, y0, x1, y1 = values

    # MinerU content-list coordinates are commonly normalized to a 1000x1000 canvas.
    if coordinate_space == "mineru_normalized" or (
        coordinate_space == "auto"
        and max(abs(value) for value in values) <= 1000
        and (
        x1 > page_rect.width * 1.15 or y1 > page_rect.height * 1.15
        )
    ):
        x0, x1 = x0 / 1000 * page_rect.width, x1 / 1000 * page_rect.width
        y0, y1 = y0 / 1000 * page_rect.height, y1 / 1000 * page_rect.height

    rect = fitz.Rect(
        max(page_rect.x0, min(x0, x1) - expand_points),
        max(page_rect.y0, min(y0, y1) - expand_points),
        min(page_rect.x1, max(x0, x1) + expand_points),
        min(page_rect.y1, max(y0, y1) + expand_points),
    )
    if rect.is_empty or rect.width < 1 or rect.height < 1:
        raise ValueError("bbox resolves to an empty PDF region")
    return rect


def render_pdf_bbox(
    pdf_path: Path,
    *,
    page_number: int,
    bbox: Iterable[Any],
    output_path: Path,
    expand_points: float = 24.0,
    zoom: float = 3.0,
) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with fitz.open(pdf_path) as document:
        page_index = int(page_number) - 1
        if page_index < 0 or page_index >= len(document):
            raise ValueError(f"page_number out of range: {page_number}")
        page = document[page_index]
        clip = bbox_to_pdf_rect(
            bbox,
            page.rect,
            expand_points=expand_points,
            coordinate_space="mineru_normalized",
        )
        pixmap = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=clip, alpha=False)
        pixmap.save(str(output_path))
    return output_path
