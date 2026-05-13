from agents.base_agent import BaseAgent
from utils.pdf_utils import sniff_esg_appendix

class AppendixSnifferAgent(BaseAgent):
    def __init__(self):
        super().__init__("AppendixSnifferAgent")
    def run(self, state):
        result = sniff_esg_appendix(state["pdf_path"])
        state["sniffer_result"] = result
        state["appendix_found"] = result.get("found", False)
        state["candidate_pages"] = result.get("expanded_page_numbers", [])
        self.log(f"appendix_found={state['appendix_found']}, pages={state['candidate_pages']}")
        return state
