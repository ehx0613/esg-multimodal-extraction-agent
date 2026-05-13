from pathlib import Path
from agents.base_agent import BaseAgent
from utils.vlm_client import extract_all_table_rows_from_image
from utils.json_utils import save_json

class VLMTableOCRAgent(BaseAgent):
    def __init__(self):
        super().__init__("VLMTableOCRAgent")
    def run(self, state):
        results = []
        for img in state.get("page_images", []):
            try:
                self.log(f"extract {img}")
                results.append(extract_all_table_rows_from_image(img))
            except Exception as e:
                results.append({"page_image": Path(img).name, "page_type": "error", "page_note": str(e), "tables": []})
        state["all_table_rows"] = results
        save_json(results, state["output_dir"] / "all_table_rows.json")
        return state
