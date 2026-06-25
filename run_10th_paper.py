"""
Runner: Career Guidance Paper for 10th Grade Completers
Topic: Post-10th class career pathways, skill building, and future-readiness
"""
import asyncio
import os
import sys
from pathlib import Path

# Load env vars from .env.local BEFORE any app imports
env_file = Path(__file__).parent / ".env.local"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.local_pipeline import run_paper

PARAMS = {
    "title": (
        "Post-Secondary School Career Pathways in the Digital Age: "
        "A Comprehensive Guide to Skills, Trends, and Future Opportunities "
        "for 10th Grade Completers"
    ),
    "domain": "Educational Research / Career Development / Human Capital",
    "keywords": [
        "career guidance", "10th grade completers", "skill development",
        "vocational education", "future of work", "digital skills",
        "career pathways India", "21st century skills", "emerging jobs",
        "educational planning"
    ],
    "objectives": (
        "1. Map the full landscape of career options available to students completing 10th grade "
        "in the current (2024–2025) educational and economic climate. "
        "2. Identify the most in-demand technical, vocational, and soft skills required across "
        "major career pathways. "
        "3. Analyse emerging trends in AI, green economy, digital services, and how they reshape "
        "traditional career options. "
        "4. Provide a data-driven, actionable framework for 10th-grade completers to make "
        "informed decisions about their next steps — streams, vocational courses, skill platforms, "
        "and self-employment. "
        "5. Compare outcomes (employability, salary, career growth) across different post-10th "
        "pathways using available research and labour market data."
    ),
    "problem_statement": (
        "Millions of students complete 10th grade every year without a clear, evidence-based "
        "roadmap for their future. The traditional Science/Commerce/Arts stream choice is "
        "increasingly insufficient in an era disrupted by AI, gig economy, green jobs, and "
        "rapid skill obsolescence. Students lack structured guidance on: which skills to build, "
        "which platforms to use, what timelines to follow, and how to align personal strengths "
        "with labour market demand. This paper addresses that gap by synthesising current "
        "research on career trends, skill requirements, and educational pathways."
    ),
    "research_gap": (
        "Existing career guidance literature either focuses narrowly on academic streams or "
        "addresses mature workforce transitions. There is a significant gap in comprehensive, "
        "data-driven guidance specifically tailored to 10th-grade completers that integrates "
        "emerging digital skills, vocational pathways, entrepreneurship, and traditional career "
        "routes within a unified decision framework."
    ),
    "hypothesis": (
        "Students who receive structured, skill-aligned career guidance at the post-10th "
        "inflection point demonstrate significantly better career-readiness scores and "
        "employability outcomes compared to those relying on conventional stream-choice advice."
    ),
    "novel_contribution": (
        "This paper introduces a 'Career Readiness Quadrant' framework mapping (1) skill "
        "acquisition timelines, (2) earning potential trajectories, (3) AI-disruption risk, "
        "and (4) entry accessibility — enabling 10th-grade completers to make optimally "
        "personalised post-school decisions."
    ),
    "scope": (
        "Focus on Indian context with global applicability. Covers: academic streams (Sci/Comm/Arts), "
        "vocational training (ITI, polytechnic, NSDC), digital skill platforms (Coursera, NPTEL, "
        "YouTube), emerging sectors (AI/ML, cybersecurity, green energy, healthcare tech, "
        "content creation, logistics tech), and entrepreneurship pathways."
    ),
    "study_type": "systematic_review",
    "journal_type": "scopus",
    "citation_style": "apa",
    "preferred_word_count": 7000,
    "writing_tone": "academic",
    "author_name": "Research Platform",
    "author_affiliation": "SCI Research Platform",
    "methodology_description": (
        "Systematic literature review of career guidance research (2019–2025) combined with "
        "analysis of labour market data from NASSCOM, World Economic Forum Future of Jobs "
        "Report, NSDC Skill India data, LinkedIn Economic Graph, and OECD education outcomes. "
        "Qualitative thematic analysis of 50+ career pathway studies. Quantitative analysis "
        "of salary data, employability rates, and skill demand trends across sectors."
    ),
    "dataset_description": (
        "Primary datasets: WEF Future of Jobs 2023, NASSCOM IT Sector Report 2024, "
        "LinkedIn India Jobs Trends 2024, NSDC Sector Skill Councils data, "
        "AISHE (All India Survey on Higher Education) 2022-23, "
        "India Skills Report 2024, UNDP Human Development Report 2023-24."
    ),
    "analysis_methods": (
        "Thematic synthesis of career guidance literature; trend analysis of job market data; "
        "comparative analysis of pathway outcomes (employability rate, median salary, "
        "career growth, AI-disruption risk index); framework development using career theory "
        "(Holland Codes, Social Cognitive Career Theory, Planned Happenstance Theory)."
    ),
    "tools_used": "PRISMA systematic review protocol, NVivo thematic analysis, Excel for quantitative trend analysis",
    "expected_findings": (
        "Digital/tech skills show highest demand growth; hybrid pathways (stream + skill "
        "certification) outperform single-path choices; vocational + digital skilling "
        "demonstrates strong ROI for non-science stream students; AI-adjacent roles require "
        "only 6-18 months of focused upskilling from zero base."
    ),
    "research_significance": (
        "Provides actionable, evidence-based career decision framework for India's ~17 million "
        "annual 10th-grade completers. Addresses a critical policy gap in career counselling "
        "and contributes to reducing youth unemployment through informed pathway selection."
    ),
    "additional_instructions": (
        "IMPORTANT: This paper MUST include: "
        "(1) A comprehensive table comparing all major post-10th pathways with columns: "
        "Path, Duration, Cost, Skills Gained, Avg Starting Salary, Growth Potential, "
        "AI Disruption Risk (Low/Med/High). "
        "(2) A step-by-step skill-building roadmap with months/years timeline. "
        "(3) Top 10 in-demand skills ranked by market demand (2025 data). "
        "(4) A comparison chart showing salary trajectories across 5 years for different paths. "
        "(5) Clear sections: Stream Options | Vocational Routes | Digital Upskilling | "
        "Emerging Sectors | Entrepreneurship | Action Plan. "
        "Write as if guiding a real 10th-class student — practical, data-backed, inspiring. "
        "Include real platforms (Coursera, NPTEL, Internshala, GitHub, etc.) and real programs "
        "(ITI, Polytechnic, NSDC courses, JEE/NEET/CLAT, CA Foundation, etc.)."
    ),
}


def progress(msg: str, pct: float, preview: str = "") -> None:
    filled = int(pct / 5)
    bar = "#" * filled + "-" * (20 - filled)
    line = f"\r[{bar}] {pct:5.1f}%  {msg[:60]}"
    try:
        print(line, end="", flush=True)
    except UnicodeEncodeError:
        safe = line.encode("ascii", errors="replace").decode("ascii")
        print(safe, end="", flush=True)
    if pct >= 100:
        print()


async def main():
    print("\n" + "="*70)
    print("  SCI RESEARCH PLATFORM — Career Guidance Paper Runner")
    print("  Topic: Post-10th Class Career Pathways & Skills")
    print("  Provider: GROQ (llama-3.3-70b-versatile)")
    print("="*70 + "\n")

    result = await run_paper(
        params=PARAMS,
        file_paths=[],
        progress_callback=progress,
    )

    print("\n" + "="*70)
    print("  PIPELINE COMPLETE")
    print("="*70)
    print(f"  Project ID   : {result['project_id']}")
    print(f"  Output dir   : {result['output_dir']}")
    print(f"  Editor Score : {result.get('editor_score', 0):.1f}/10")
    print(f"  Plagiarism   : {result.get('plagiarism_score', 0):.1f}%")
    print(f"  AI Detection : {result.get('ai_detection_score', 0):.1f}%")
    print(f"  Novelty Score: {result.get('novelty_score', 0):.1f}/10")
    print(f"  References   : {result.get('reference_count', 0)}")
    print(f"  Charts       : {result.get('chart_count', 0)}")
    print(f"  Tables       : {result.get('table_count', 0)}")
    print()
    for label in ("paper", "cover letter", "editorial report", "latex source"):
        path = result.get(label)
        if path:
            print(f"  {label.upper():20s} → {path}")
    print("="*70 + "\n")
    return result


if __name__ == "__main__":
    asyncio.run(main())
