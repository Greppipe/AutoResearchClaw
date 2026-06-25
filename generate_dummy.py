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
        "title": "A Novel Machine Learning Approach to Quantum Cryptography",
        "domain": "Computer Science & Software Engineering",
        "keywords": ["Machine Learning", "Quantum Cryptography", "Cybersecurity"],
        "study_type": "Experimental Study",
        "problem_statement": "Current cryptographic algorithms are vulnerable to quantum attacks.",
        "research_gap": "Lack of efficient ML-based hybrid quantum models.",
        "hypothesis": "A hybrid ML model can detect and adapt to quantum cryptographic attacks in real time.",
        "novel_contribution": "Adaptive hybrid quantum detection model.",
        "research_significance": "Securing next-gen internet infrastructure.",
        "objectives": "Evaluate detection rate of quantum attacks.",
        "author_name": "Dr. Ranganath",
        "author_affiliation": "Global Research Institute",
        "all_authors": [{"name": "Dr. Ranganath", "affiliation": "Global Research Institute", "email": ""}],
        "funding_source": "",
        "conflicts_of_interest": "",
        "ethics_statement": "",
        "methodology_description": "We simulated a quantum network and used supervised learning.",
        "dataset_description": "Simulated quantum traffic logs.",
        "analysis_methods": "Neural networks, cross-validation.",
        "tools_used": "Python, Qiskit, PyTorch.",
        "expected_findings": "99% detection rate.",
        "journal_type": "SCI",
        "citation_style": "ieee",
        "preferred_word_count": 2000,  # Keep it short for faster testing
        "writing_tone": "academic",
        "additional_instructions": "",
    }
    
    file_paths = []
    
    def progress_cb(msg, pct, preview):
        try:
            print(f"[{pct}%] {msg}")
        except UnicodeEncodeError:
            print(f"[{pct}%] {msg.encode('ascii', errors='replace').decode('ascii')}")


    print("Starting pipeline test...")
    try:
        result = await run_paper(params, file_paths, progress_callback=progress_cb)
        print("Pipeline finished successfully:", result)
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
