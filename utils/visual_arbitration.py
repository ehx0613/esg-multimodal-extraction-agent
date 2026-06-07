from pathlib import Path
from typing import Any, Dict, Iterable, List

from utils.pdf_geometry import render_pdf_bbox


def build_table_arbitration_queue(
    assessments: Iterable[Dict[str, Any]],
    *,
    max_regions: int = 10,
) -> List[Dict[str, Any]]:
    candidates = [
        {
            "source_region_id": item.get("source_region_id"),
            "chunk_id": item.get("chunk_id"),
            "page_number": item.get("page_number"),
            "bbox": item.get("bbox"),
            "quality_score": item.get("quality_score", 0.0),
            "reasons": item.get("reasons", []),
            "status": "queued",
        }
        for item in assessments
        if item.get("needs_visual") and item.get("page_number") and item.get("bbox")
    ]
    candidates.sort(key=lambda item: (float(item["quality_score"]), int(item["page_number"])))
    return candidates[:max_regions]


def prepare_table_arbitration_images(
    pdf_path: Path,
    report_dir: Path,
    queue: Iterable[Dict[str, Any]],
    *,
    max_regions: int,
) -> List[Dict[str, Any]]:
    output_dir = Path(report_dir) / "arbitration_regions"
    prepared: List[Dict[str, Any]] = []
    for index, item in enumerate(list(queue)[:max_regions]):
        result = dict(item)
        output_path = output_dir / f"region_{index + 1}_page_{item['page_number']}.png"
        try:
            render_pdf_bbox(
                pdf_path,
                page_number=int(item["page_number"]),
                bbox=item["bbox"],
                output_path=output_path,
            )
            result["status"] = "image_prepared"
            result["image_path"] = str(output_path)
        except Exception as exc:
            result["status"] = "crop_failed"
            result["error"] = str(exc)
        prepared.append(result)
    return prepared

