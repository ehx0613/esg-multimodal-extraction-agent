from agents.base_agent import BaseAgent
from utils.json_utils import save_json

class ValidationAgent(BaseAgent):
    def __init__(self):
        super().__init__("ValidationAgent")
    def run(self, state):
        total = len(state.get("standard_results", {}))
        extracted = len(state.get("extracted_fields", []))
        summary = {"total_fields": total, "extracted_fields": extracted, "missing_fields": total - extracted, "coverage_rate": round(extracted / total, 4) if total else 0, "raw_row_count": state.get("raw_row_count", 0), "unknown_metrics": len(state.get("unknown_metrics", []))}
        state["validation_summary"] = summary
        save_json(summary, state["output_dir"] / "validation_summary.json")
        self.log(str(summary))
        return state
