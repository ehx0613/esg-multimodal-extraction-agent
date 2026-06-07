from pathlib import Path
import re

from agents.base_agent import BaseAgent
from config.settings import ROUTE_A_ADAPTIVE_SPLIT_RETRY, ROUTE_A_USE_VLM_CACHE
from utils.json_utils import load_json
from utils.vlm_client import extract_all_table_rows_from_image
from utils.json_utils import save_json
from utils.pdf_utils import render_pdf_page_split_images


VLM_TABLE_OCR_VERSION = "table_and_chart_v3"


class VLMTableOCRAgent(BaseAgent):
    def __init__(self):
        super().__init__("VLMTableOCRAgent")

    def _count_rows(self, items):
        count = 0
        for item in items:
            if not isinstance(item, dict):
                continue
            for table in item.get("tables", []):
                if isinstance(table, dict) and isinstance(table.get("rows"), list):
                    count += len(table["rows"])
        return count

    def _count_result_rows(self, item):
        return self._count_rows([item])

    def _page_number_from_image(self, image_path):
        match = re.search(r"page_(\d+)(?:_|\.png)", Path(image_path).name)
        if not match:
            return None
        return int(match.group(1))

    def _page_numbers_from_results(self, items):
        page_numbers = set()
        for item in items:
            if not isinstance(item, dict):
                continue
            page_image = item.get("page_image") or item.get("image") or item.get("source")
            if not page_image:
                continue
            page_number = self._page_number_from_image(page_image)
            if page_number is not None:
                page_numbers.add(page_number)
        return page_numbers

    def _cache_version_ok(self, items):
        return all(
            isinstance(item, dict)
            and item.get("extractor_version") == VLM_TABLE_OCR_VERSION
            and item.get("page_note") != "model_call_budget_exhausted"
            for item in items
        )

    def _requested_page_numbers(self, state):
        page_numbers = set()
        for image_path in state.get("page_images", []):
            page_number = self._page_number_from_image(image_path)
            if page_number is not None:
                page_numbers.add(page_number)
        return page_numbers

    def _filter_results_to_pages(self, items, page_numbers):
        filtered = []
        for item in items:
            if not isinstance(item, dict):
                continue
            page_image = item.get("page_image") or item.get("image") or item.get("source")
            page_number = self._page_number_from_image(page_image)
            if page_number in page_numbers:
                filtered.append(item)
        return filtered

    def run(self, state):
        cache_path = state["output_dir"] / "all_table_rows.json"
        cached = []
        requested_pages = self._requested_page_numbers(state)
        if ROUTE_A_USE_VLM_CACHE and cache_path.exists():
            cached = load_json(cache_path)
            cached_pages = self._page_numbers_from_results(cached)
            cache_version_ok = self._cache_version_ok(cached)
            if cache_version_ok and self._count_rows(cached) > 0 and requested_pages.issubset(cached_pages):
                self.log(f"cache hit {cache_path}, filtered_pages={sorted(requested_pages)}")
                state["all_table_rows"] = cached
                return state
            self.log(
                f"cache miss {cache_path}: requested_pages={sorted(requested_pages)}, "
                f"cached_pages={sorted(cached_pages)}"
            )
            if not cache_version_ok:
                cached = []

        results = []
        for img in state.get("page_images", []):
            try:
                self.log(f"extract {img}")
                result = extract_all_table_rows_from_image(img)
                result["extractor_version"] = VLM_TABLE_OCR_VERSION
                results.append(result)

                if (
                    ROUTE_A_ADAPTIVE_SPLIT_RETRY
                    and self._count_result_rows(result) == 0
                    and "_left" not in Path(img).stem
                    and "_right" not in Path(img).stem
                ):
                    page_number = self._page_number_from_image(img)
                    if page_number is not None:
                        split_images = render_pdf_page_split_images(
                            state["pdf_path"],
                            page_number,
                            Path(img).parent,
                        )
                        for split_img in split_images:
                            self.log(f"adaptive split extract {split_img}")
                            split_result = extract_all_table_rows_from_image(split_img)
                            split_result["extractor_version"] = VLM_TABLE_OCR_VERSION
                            results.append(split_result)
            except Exception as e:
                results.append({"page_image": Path(img).name, "page_type": "error", "page_note": str(e), "tables": [], "extractor_version": VLM_TABLE_OCR_VERSION})
        preserved = [
            item
            for item in cached
            if self._page_number_from_image(
                item.get("page_image") or item.get("image") or item.get("source")
            )
            not in requested_pages
        ]
        combined = [*preserved, *results]
        state["all_table_rows"] = combined
        save_json(combined, state["output_dir"] / "all_table_rows.json")
        return state
