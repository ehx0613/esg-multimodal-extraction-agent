from agents.base_agent import BaseAgent
from config.settings import (
    ROUTE_A_CANDIDATE_MIN_SCORE,
    ROUTE_A_CANDIDATE_TOP_K,
    ROUTE_A_EXPAND_AFTER,
    ROUTE_A_EXPAND_BEFORE,
)
from utils.pdf_ingest import ingest_pdf, select_route_a_candidate_pages
from utils.call_tracker import get_active_run_mode

class AppendixSnifferAgent(BaseAgent):
    def __init__(self):
        super().__init__("AppendixSnifferAgent")
    def run(self, state):
        ingest = ingest_pdf(state["pdf_path"], state["output_dir"])
        state["ingest"] = {
            "manifest": ingest["manifest"],
            "cache_used": ingest["cache_used"],
            "paths": ingest["paths"],
        }

        result = select_route_a_candidate_pages(
            ingest["page_features"],
            top_k=ROUTE_A_CANDIDATE_TOP_K,
            min_score=ROUTE_A_CANDIDATE_MIN_SCORE,
            expand_before=ROUTE_A_EXPAND_BEFORE,
            expand_after=ROUTE_A_EXPAND_AFTER,
        )
        state["sniffer_result"] = result
        state["appendix_found"] = result.get("found", False)
        candidate_pages = result.get("expanded_page_numbers", [])
        if get_active_run_mode() == "fast":
            high_value_pages = [
                int(item["page_number"])
                for item in result.get("candidates", [])
                if item.get("page_number")
            ]
            candidate_pages = list(dict.fromkeys([*high_value_pages, *candidate_pages]))
        state["candidate_pages"] = candidate_pages
        self.log(
            f"appendix_found={state['appendix_found']}, pages={state['candidate_pages']}, "
            f"ingest_cache={ingest['cache_used']}"
        )
        return state
