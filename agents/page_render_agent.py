from agents.base_agent import BaseAgent
from utils.pdf_utils import render_pdf_pages_to_images

class PageRenderAgent(BaseAgent):
    def __init__(self):
        super().__init__("PageRenderAgent")
    def run(self, state):
        if not state.get("appendix_found"):
            state["page_images"] = []
            return state
        out = state["output_dir"] / "page_images"
        state["page_images"] = render_pdf_pages_to_images(state["pdf_path"], state.get("candidate_pages", []), out)
        self.log(f"rendered={len(state['page_images'])}")
        return state
