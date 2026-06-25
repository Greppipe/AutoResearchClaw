import asyncio
import os
import sys
from pathlib import Path

# Fix paths so we can import from backend
ROOT = Path(__file__).parent
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env.local", override=True)

from app.local_pipeline import run_paper

async def main():
    params = {
        "title": "Nurturing the Next Generation: A Comprehensive Framework for Cognitive and Emotional Development in Child Psychology for Future Readiness",
        "domain": "Psychology & Behavioral Science",
        "keywords": ["Child Psychology", "Cognitive Development", "Emotional Intelligence", "Future Readiness", "Resilience Training", "Skill Development"],
        "study_type": "Theoretical / Conceptual Paper",
        "problem_statement": "As the world rapidly changes, traditional child development paradigms often fail to adequately prepare children for the complex, unpredictable demands of the future.",
        "research_gap": "There is a lack of integrated frameworks that combine emotional intelligence, cognitive adaptability, and resilience training specifically targeted for future-readiness in children.",
        "hypothesis": "Implementing a holistic training approach focusing on emotional intelligence, critical thinking, and adaptability will significantly boost children's preparedness for future societal and technological challenges.",
        "novel_contribution": "A new synthesized model for multi-dimensional child development focusing on future-ready skills: The 'Future-Ready Child Development Framework'.",
        "research_significance": "Provides actionable insights for educators, parents, and policymakers to foster resilient, adaptable, and emotionally intelligent future generations.",
        "objectives": "To identify key psychological aspects that require training, formulate strategies to boost child development, and present a structured framework for preparing children for future challenges.",
        "author_name": "Dr. Ranganath",
        "author_affiliation": "Global Research Institute",
        "all_authors": [{"name": "Dr. Ranganath", "affiliation": "Global Research Institute", "email": ""}],
        "funding_source": "",
        "conflicts_of_interest": "",
        "ethics_statement": "",
        "methodology_description": "Comprehensive review of current literature in child psychology, cognitive science, and future studies, synthesizing findings into a conceptual framework.",
        "dataset_description": "N/A",
        "analysis_methods": "Thematic analysis and framework synthesis.",
        "tools_used": "Literature review, Conceptual modeling.",
        "expected_findings": "A structured set of core competencies (emotional regulation, cognitive flexibility, social resilience) essential for future readiness.",
        "journal_type": "SCI",
        "citation_style": "apa",
        "preferred_word_count": 3000,
        "writing_tone": "academic",
        "additional_instructions": "",
    }
    
    file_paths = []
    
    def progress_cb(msg, pct, preview):
        clean_msg = str(msg).encode("ascii", "ignore").decode("ascii")
        print(f"[{pct}%] {clean_msg}")

    print("Starting pipeline for Child Psychology paper...")
    try:
        result = await run_paper(params, file_paths, progress_callback=progress_cb)
        print("Pipeline finished successfully:", result)
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
