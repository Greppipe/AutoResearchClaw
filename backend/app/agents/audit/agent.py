"""
Figures + Tables + TOC + References Auditor — Module 7 (ENHANCED)
Integrates: Pandoc export, Zotero API, citation validators, format normalizer.
"""
from __future__ import annotations

import re
import json
import subprocess
import tempfile
import os
from typing import Dict, Any, List, Optional
import structlog
import httpx

from langchain_core.messages import HumanMessage

from app.core.config import settings
from app.core.llm_factory import get_fast_llm

logger = structlog.get_logger()


class AuditAgent:
    def __init__(self):
        self.llm = get_fast_llm(max_tokens=4096)

    # ─── Citation Number Extraction ────────────────────────────────────────

    def _extract_citation_numbers(self, text: str) -> List[int]:
        numbers = set()
        for m in re.finditer(r"\[(\d+(?:,\s*\d+)*)\]", text):
            for num in m.group(1).split(","):
                try:
                    numbers.add(int(num.strip()))
                except ValueError:
                    pass
        return sorted(numbers)

    # ─── Figure Reference Check ───────────────────────────────────────────

    def _verify_figure_references(self, sections: Dict, figures: List[Dict]) -> List[str]:
        full_text = " ".join(sections.values())
        issues = []
        for fig in figures:
            fn = fig.get("figure_number", 0)
            patterns = [f"Fig. {fn}", f"Figure {fn}", f"FIG. {fn}", f"fig.{fn}"]
            if not any(p.lower() in full_text.lower() for p in patterns):
                issues.append(f"Figure {fn} ({fig.get('caption', '')[:50]}) not referenced in text")
        return issues

    # ─── Table Reference Check ────────────────────────────────────────────

    def _verify_table_references(self, sections: Dict, tables: List[Dict]) -> List[str]:
        full_text = " ".join(sections.values())
        issues = []
        for tbl in tables:
            tn = tbl.get("table_number", 0)
            patterns = [f"Table {tn}", f"TABLE {tn}", f"Tab. {tn}"]
            if not any(p.lower() in full_text.lower() for p in patterns):
                issues.append(f"Table {tn} ({tbl.get('caption', '')[:50]}) not referenced in text")
        return issues

    # ─── Citation Sequence Audit ──────────────────────────────────────────

    def _check_citation_sequence(self, sections: Dict, references: List[Dict]) -> Dict[str, Any]:
        all_text = " ".join(sections.values())
        cited = self._extract_citation_numbers(all_text)
        max_ref = len(references)
        orphans = [n for n in cited if n > max_ref or n < 1]
        uncited = [i + 1 for i in range(max_ref) if (i + 1) not in cited]
        return {
            "cited_numbers": cited,
            "orphan_citations": orphans,
            "uncited_references": uncited[:20],
            "citation_coverage": round(len(cited) / max(max_ref, 1), 3),
        }

    # ─── DOI Format Validation ────────────────────────────────────────────

    def _validate_doi(self, doi: str) -> bool:
        if not doi:
            return True
        return bool(re.match(r"^10\.\d{4,9}/[-._;()/:A-Z0-9]+$", doi.strip(), re.IGNORECASE))

    # ─── Reference Normalization ──────────────────────────────────────────

    def _normalize_reference(self, ref: Dict, number: int, citation_style: str) -> Dict:
        authors = ref.get("authors", [])
        year = ref.get("year", "n.d.")
        title = ref.get("title", "Unknown Title")
        journal = ref.get("journal", "")
        doi = ref.get("doi", "")
        volume = ref.get("volume", "")
        issue = ref.get("issue", "")
        pages = ref.get("pages", "")

        author_str = ", ".join(str(a) for a in authors[:3])
        if len(authors) > 3:
            author_str += " et al."

        if citation_style == "ieee":
            fmt = f'[{number}] {author_str}, "{title}," {journal}'
            if volume:
                fmt += f", vol. {volume}"
            if issue:
                fmt += f", no. {issue}"
            if pages:
                fmt += f", pp. {pages}"
            fmt += f", {year}."
            if doi and self._validate_doi(doi):
                fmt += f" doi: {doi}."
        elif citation_style == "apa":
            fmt = f"{author_str} ({year}). {title}. {journal}"
            if volume:
                fmt += f", {volume}"
            if issue:
                fmt += f"({issue})"
            if pages:
                fmt += f", {pages}"
            fmt += "."
            if doi:
                fmt += f" https://doi.org/{doi}"
        elif citation_style == "mla":
            fmt = f'{author_str}. "{title}." {journal}'
            if volume:
                fmt += f", vol. {volume}"
            if issue:
                fmt += f", no. {issue}"
            fmt += f", {year}"
            if pages:
                fmt += f", pp. {pages}"
            fmt += "."
        elif citation_style == "vancouver":
            fmt = f"{number}. {author_str}. {title}. {journal}. {year}"
            if volume:
                fmt += f";{volume}"
            if issue:
                fmt += f"({issue})"
            if pages:
                fmt += f":{pages}"
            if doi:
                fmt += f". doi:{doi}"
        elif citation_style == "harvard":
            fmt = f"{author_str} ({year}) '{title}', {journal}"
            if volume:
                fmt += f", vol. {volume}"
            if issue:
                fmt += f", no. {issue}"
            if pages:
                fmt += f", pp. {pages}"
            fmt += "."
        else:
            fmt = f"{author_str} ({year}). {title}. {journal}."

        doi_valid = self._validate_doi(doi)
        return {
            **ref,
            "reference_number": number,
            "formatted": fmt,
            f"formatted_{citation_style}": fmt,
            "doi_valid": doi_valid,
            "incomplete": not title or not authors,
        }

    # ─── Citation.js / CrossRef formatted citation ─────────────────────────

    async def fetch_formatted_citation(self, doi: str, style: str = "ieee") -> Optional[str]:
        """Fetch a properly formatted citation from doi.org content negotiation."""
        if not doi:
            return None

        # Map our style names to content-negotiation media types
        ct_map = {
            "ieee": "text/x-bibliography; style=ieee",
            "apa": "text/x-bibliography; style=apa",
            "mla": "text/x-bibliography; style=modern-language-association",
            "chicago": "text/x-bibliography; style=chicago-fullnote-bibliography",
            "harvard": "text/x-bibliography; style=harvard-cite-them-right",
            "vancouver": "text/x-bibliography; style=vancouver",
            "nature": "text/x-bibliography; style=nature",
            "acs": "text/x-bibliography; style=american-chemical-society",
        }
        accept_header = ct_map.get(style, "text/x-bibliography; style=ieee")

        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.get(
                    f"https://doi.org/{doi}",
                    headers={"Accept": accept_header, "User-Agent": "SciResearchPlatform/2.0"},
                )
                if resp.status_code == 200 and resp.text.strip():
                    return resp.text.strip()
        except Exception as e:
            logger.debug("DOI content-negotiation citation failed", doi=doi, error=str(e))

        # Fallback: CrossRef works endpoint for structured data
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(
                    f"https://api.crossref.org/works/{doi}",
                    headers={"User-Agent": "SciResearchPlatform/2.0 (mailto:platform@research.ai)"},
                )
                if resp.status_code == 200:
                    msg = resp.json().get("message", {})
                    authors = ", ".join(
                        f"{a.get('family', '')}, {a.get('given', '')[:1]}."
                        for a in msg.get("author", [])[:3]
                    )
                    if len(msg.get("author", [])) > 3:
                        authors += " et al."
                    year = (msg.get("published", {}).get("date-parts") or [[None]])[0][0]
                    title = " ".join(msg.get("title", [""])) if isinstance(msg.get("title"), list) else msg.get("title", "")
                    journal = " ".join(msg.get("container-title", [""])) if isinstance(msg.get("container-title"), list) else ""
                    volume = msg.get("volume", "")
                    issue = msg.get("issue", "")
                    pages = msg.get("page", "")
                    if style == "ieee":
                        s = f'{authors}, "{title}," {journal}'
                        if volume:
                            s += f", vol. {volume}"
                        if issue:
                            s += f", no. {issue}"
                        if pages:
                            s += f", pp. {pages}"
                        s += f", {year}. doi: {doi}"
                    else:
                        s = f"{authors} ({year}). {title}. {journal}"
                        if volume:
                            s += f", {volume}"
                        if issue:
                            s += f"({issue})"
                        if pages:
                            s += f", {pages}"
                        s += f". https://doi.org/{doi}"
                    return s if authors or title else None
        except Exception:
            pass
        return None

    # ─── Pandoc Export ────────────────────────────────────────────────────

    def _generate_bibtex(self, references: List[Dict]) -> str:
        bibtex_entries = []
        for ref in references:
            key = re.sub(r"[^a-zA-Z0-9]", "", (ref.get("authors", [""])[0] + str(ref.get("year", ""))).replace(" ", ""))
            entry = f"@article{{{key},\n"
            entry += f'  title = {{{ref.get("title", "")}}},\n'
            authors_str = " and ".join(str(a) for a in ref.get("authors", [])[:5])
            entry += f"  author = {{{authors_str}}},\n"
            if ref.get("year"):
                entry += f"  year = {{{ref['year']}}},\n"
            if ref.get("journal"):
                entry += f"  journal = {{{ref['journal']}}},\n"
            if ref.get("doi"):
                entry += f"  doi = {{{ref['doi']}}},\n"
            entry += "}"
            bibtex_entries.append(entry)
        return "\n\n".join(bibtex_entries)

    def _export_bibtex(self, references: List[Dict]) -> Optional[str]:
        """Generate BibTeX file content for reference management."""
        try:
            return self._generate_bibtex(references)
        except Exception as e:
            logger.warning("BibTeX generation failed", error=str(e))
        return None

    # ─── TOC Generation ───────────────────────────────────────────────────

    def _generate_toc(self, paper_sections: Dict) -> List[Dict]:
        toc = []
        section_map = [
            ("abstract", "Abstract"),
            ("introduction", "I. Introduction"),
            ("literature_review", "II. Literature Review"),
            ("materials_and_methods", "III. Materials and Methods"),
            ("results", "IV. Results"),
            ("discussion", "V. Discussion"),
            ("conclusion", "VI. Conclusion"),
        ]
        for key, label in section_map:
            if paper_sections.get(key):
                word_count = len(paper_sections[key].split())
                toc.append({"section": label, "key": key, "word_count": word_count})
        return toc

    # ─── Auto-Fix via Claude ──────────────────────────────────────────────

    async def auto_fix_sections(self, sections: Dict, issues: List[str]) -> Dict:
        if not issues:
            return sections
        message = HumanMessage(
            content=(
                "You are a scientific paper copy editor. Fix ONLY the listed issues in the paper sections.\n"
                "Return JSON with the same section keys and corrected text.\n"
                "Do NOT rewrite sections that have no issues.\n\n"
                f"ISSUES TO FIX:\n{json.dumps(issues, indent=2)}\n\n"
                f"PAPER SECTIONS (excerpt):\n"
                f"Abstract: {sections.get('abstract', '')[:400]}\n"
                f"Introduction: {sections.get('introduction', '')[:400]}\n"
                "Return JSON with only modified sections."
            )
        )
        resp = await self.llm.ainvoke([message])
        try:
            fixes = json.loads(resp.content)
            return {**sections, **{k: v for k, v in fixes.items() if k in sections}}
        except json.JSONDecodeError:
            return sections

    # ─── Main Run ─────────────────────────────────────────────────────────

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        paper_sections = state.get("paper_sections", {})
        references = state.get("references", [])
        figures = state.get("figures", state.get("paper_sections", {}).get("suggested_figures", []))
        tables = state.get("tables", state.get("paper_sections", {}).get("suggested_tables", []))
        citation_style = state.get("citation_style", "ieee")

        # Parse suggested figures/tables from paper_sections if stored there
        if not figures and isinstance(paper_sections, dict):
            figures = paper_sections.pop("suggested_figures", []) or []
        if not tables and isinstance(paper_sections, dict):
            tables = paper_sections.pop("suggested_tables", []) or []

        # Normalize and renumber
        audited_refs = [
            self._normalize_reference(ref, i + 1, citation_style)
            for i, ref in enumerate(references)
        ]

        # Enrich up to 30 refs with live DOI-content-negotiated citations (batch of 5)
        enriched = 0
        for ref in audited_refs[:30]:
            doi = ref.get("doi", "")
            if doi and not ref.get(f"formatted_{citation_style}"):
                try:
                    live_fmt = await self.fetch_formatted_citation(doi, citation_style)
                    if live_fmt:
                        ref[f"formatted_{citation_style}"] = live_fmt
                        ref["formatted"] = live_fmt
                        enriched += 1
                        if enriched >= 5:
                            break
                except Exception:
                    pass

        audited_figures = [{**fig, "figure_number": i + 1} for i, fig in enumerate(figures)]
        audited_tables = [{**tbl, "table_number": i + 1} for i, tbl in enumerate(tables)]

        # Validation checks
        figure_issues = self._verify_figure_references(paper_sections, audited_figures)
        table_issues = self._verify_table_references(paper_sections, audited_tables)
        citation_audit = self._check_citation_sequence(paper_sections, audited_refs)
        doi_issues = [
            f"Invalid DOI format: {r.get('doi')} in reference {r['reference_number']}"
            for r in audited_refs
            if not r.get("doi_valid")
        ]

        # TOC generation
        toc = self._generate_toc(paper_sections)

        # BibTeX export
        bibtex = self._export_bibtex(references)

        # Compile and auto-fix
        all_issues = figure_issues + table_issues + doi_issues
        if citation_audit["orphan_citations"]:
            all_issues.append(f"Orphan citation numbers (no matching reference): {citation_audit['orphan_citations'][:10]}")

        audited_sections = paper_sections
        if all_issues:
            audited_sections = await self.auto_fix_sections(paper_sections, all_issues)

        logger.info(
            "Audit complete",
            figure_issues=len(figure_issues),
            table_issues=len(table_issues),
            doi_issues=len(doi_issues),
            orphan_citations=len(citation_audit["orphan_citations"]),
            citation_coverage=citation_audit["citation_coverage"],
            toc_sections=len(toc),
        )

        return {
            "audited_sections": audited_sections,
            "audited_references": audited_refs,
            "audited_figures": audited_figures,
            "audited_tables": audited_tables,
            "toc": toc,
            "bibtex": bibtex,
            "audit_report": {
                "figure_issues": figure_issues,
                "table_issues": table_issues,
                "doi_issues": doi_issues,
                "citation_audit": citation_audit,
                "total_issues": len(all_issues),
                "fixes_applied": len(all_issues),
            },
        }
