import json
from pathlib import Path
from agents.appendix_sniffer_agent import AppendixSnifferAgent
from agents.page_render_agent import PageRenderAgent
from agents.vlm_table_ocr_agent import VLMTableOCRAgent
from agents.schema_match_agent import SchemaMatchAgent
from agents.validation_agent import ValidationAgent
from utils.csv_export import export_standard_results_csv, export_unknown_metrics_csv

class ESGAppendixPipeline:
    def __init__(self, output_dir):
        self.output_dir = Path(output_dir)
        self.agents = [AppendixSnifferAgent(), PageRenderAgent(), VLMTableOCRAgent(), SchemaMatchAgent(), ValidationAgent()]
    def run(self, pdf_path):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        state = {"pdf_path": str(pdf_path), "output_dir": self.output_dir}
        for agent in self.agents:
            print(f"\n----- Running {agent.name} -----")
            state = agent.run(state)
        export_standard_results_csv(state.get("standard_results", {}), self.output_dir / "standard_esg_results.csv")
        export_unknown_metrics_csv(state.get("unknown_metrics", []), self.output_dir / "unknown_metrics.csv")
        save_state = dict(state)
        save_state["output_dir"] = str(save_state["output_dir"])
        with open(self.output_dir / "pipeline_state.json", "w", encoding="utf-8") as f:
            json.dump(save_state, f, ensure_ascii=False, indent=2)
        print(f"\nOutput dir: {self.output_dir}")
        return state
