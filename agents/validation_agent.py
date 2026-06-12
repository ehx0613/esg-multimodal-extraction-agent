from agents.base_agent import BaseAgent
from config.settings import ROUTE_A_B2_MIN_EXTRACTED_FIELDS
from utils.json_utils import save_json

class ValidationAgent(BaseAgent):
    def __init__(self):
        super().__init__("ValidationAgent")
    def run(self, state):
        total = len(state.get("standard_results", {}))
        extracted = len(state.get("extracted_fields", []))
        missing = total - extracted
        needs_route_b2 = bool(missing and extracted < ROUTE_A_B2_MIN_EXTRACTED_FIELDS)
        summary = {
            "total_fields": total,
            "extracted_fields": extracted,
            "missing_fields": missing,
            "coverage_rate": round(extracted / total, 4) if total else 0,
            "raw_row_count": state.get("raw_row_count", 0),
            "unknown_metrics": len(state.get("unknown_metrics", [])),
            "metric_candidates": len(state.get("metric_candidates", [])),
            "validated_metrics": len(state.get("validated_metrics", [])),
            "needs_route_b2": needs_route_b2,
            "route_b2_reason": (
                f"route_a_extracted_below_{ROUTE_A_B2_MIN_EXTRACTED_FIELDS}"
                if needs_route_b2
                else ""
            ),
        }
        state["validation_summary"] = summary
        state["needs_route_b2"] = needs_route_b2
        save_json(summary, state["output_dir"] / "validation_summary.json")
        self.log(str(summary))
        return state
