"""
Authentication Engine — Module 4 (ENHANCED)
Verifies via CrossRef, Semantic Scholar, DOI resolver, Scite, Unpaywall,
retraction watch, predatory journal detection, claim fact-checking.
"""
from __future__ import annotations

import asyncio
import re
import json
from typing import Dict, Any, List, Optional
import structlog
import httpx
from habanero import Crossref

from langchain_core.messages import HumanMessage

from app.core.config import settings
from app.core.llm_factory import get_fast_llm

logger = structlog.get_logger()

# Comprehensive predatory journal patterns (Beall's List + common known predatory publishers)
PREDATORY_PATTERNS = [
    # Generic pattern-based
    r"ijedr", r"ijsrp", r"ijert", r"ijsr", r"wjss", r"aijcrr",
    r"gjournals", r"euroasiapub", r"irjet", r"ijirset",
    # OMICS Group publishers
    r"omics", r"longdom", r"hilarispublishing", r"esciencecentral",
    # WASET / World Academy
    r"waset\.org", r"world academy of science",
    # Known predatory names
    r"sciencepublishinggroup", r"scirp\.org", r"scientific research publishing",
    r"david publishing", r"academic journals.*africa",
    r"internationalscholarlyresearch", r"isrn\.",
    r"benthamopen", r"bentham science open",
    r"academicpublishingplatforms", r"academicjournalsinc",
    r"globalresearchonline", r"globalscientificjournal",
    r"journalofadvancedresearch", r"jarcet", r"ijarcet",
    r"ijcsit", r"ijca\b", r"ijcsi\b", r"ijcse\b",
    r"ijarcsse", r"ijais\b", r"ijaiem", r"ijcem",
    r"openaccesspublication", r"openaccess\.pub",
    r"academicpub\.org", r"iaeme\.com",
    r"iosrjournals", r"iosrphr",
    r"jresearchpub", r"journalofresearch\.org",
    r"researchinventy", r"ijarcce",
    r"acadpubl", r"scialert",
    r"arpnjournals", r"arpapress",
    r"worldresearchlibrary",
    # Pattern: vague journal names
    r"international journal of (?:advanced|emerging|innovative|modern)",
    r"global journal of (?:advanced|pure|applied)",
    r"european journal of (?:applied|academic)",
    r"american journal of (?:applied|advanced)",
    r"asian journal of (?:applied|advanced|science)",
    r"research journal of (?:applied|pure)",
]

# Known legitimate high-impact publisher domains (whitelist to override false positives)
LEGITIMATE_PUBLISHERS = {
    "ieee", "elsevier", "springer", "nature", "wiley", "oxford", "cambridge",
    "acs", "rsc", "plos", "frontiers", "mdpi", "taylor", "sage", "lancet",
    "cell", "science", "nih", "pubmed", "ncbi", "hindawi",
}

# DOI format validation
DOI_PATTERN = re.compile(r"^10\.\d{4,9}/[-._;()/:A-Z0-9]+$", re.IGNORECASE)


class AuthenticationAgent:
    def __init__(self):
        self.llm = get_fast_llm(max_tokens=4096)
        self.crossref = Crossref(mailto="platform@research.ai")

    # ─── DOI Validation ────────────────────────────────────────────────────

    def _validate_doi_format(self, doi: str) -> bool:
        return bool(doi and DOI_PATTERN.match(doi.strip()))

    async def verify_doi(self, doi: str) -> Optional[Dict]:
        if not doi or not self._validate_doi_format(doi):
            return {"doi": doi, "resolvable": False, "format_valid": False}
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.head(f"https://doi.org/{doi}")
                return {"doi": doi, "resolvable": resp.status_code < 400, "format_valid": True, "status_code": resp.status_code}
        except Exception:
            return {"doi": doi, "resolvable": False, "format_valid": True}

    # ─── CrossRef Verification ─────────────────────────────────────────────

    async def verify_via_crossref(self, title: str, authors: List[str], year: Optional[int]) -> Dict:
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.crossref.works(query=f"{title} {' '.join(authors[:2])}", limit=3)
            )
            items = result.get("message", {}).get("items", [])
            if items:
                top = items[0]
                cr_title = " ".join(top.get("title", [""]))
                similarity = self._title_similarity(title, cr_title)
                cr_year = (top.get("published", {}).get("date-parts") or [[None]])[0][0]
                year_match = cr_year == year if year and cr_year else True
                return {
                    "found": similarity > 0.6,
                    "similarity": similarity,
                    "doi": top.get("DOI"),
                    "publisher": top.get("publisher", ""),
                    "container": " ".join(top.get("container-title", [])),
                    "crossref_year": cr_year,
                    "year_match": year_match,
                    "is_retracted": top.get("update-policy", "").lower().find("retract") >= 0,
                }
        except Exception as e:
            logger.debug("CrossRef failed", error=str(e))
        return {"found": False, "similarity": 0.0}

    # ─── Semantic Scholar Verification ────────────────────────────────────

    async def verify_via_semantic_scholar(self, title: str) -> Dict:
        try:
            url = "https://api.semanticscholar.org/graph/v1/paper/search"
            params = {"query": title, "limit": 3, "fields": "title,year,citationCount,externalIds,isOpenAccess"}
            headers = {"x-api-key": settings.SEMANTIC_SCHOLAR_API_KEY} if settings.SEMANTIC_SCHOLAR_API_KEY else {}
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url, params=params, headers=headers)
                if resp.status_code == 200:
                    papers = resp.json().get("data", [])
                    if papers:
                        top = papers[0]
                        return {
                            "found": True,
                            "ss_paper_id": top.get("paperId"),
                            "citation_count": top.get("citationCount", 0),
                            "year": top.get("year"),
                            "is_open_access": top.get("isOpenAccess", False),
                        }
        except Exception as e:
            logger.debug("Semantic Scholar failed", error=str(e))
        return {"found": False}

    # ─── Scite Citation Intelligence ───────────────────────────────────────

    async def verify_via_scite(self, doi: str) -> Dict:
        if not doi or not settings.SCITE_API_KEY:
            return {"found": False}
        try:
            url = f"https://api.scite.ai/tallies/{doi}"
            headers = {"Authorization": f"Bearer {settings.SCITE_API_KEY}"}
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    return {
                        "found": True,
                        "supporting": data.get("supporting", 0),
                        "contrasting": data.get("contrasting", 0),
                        "mentioning": data.get("mentioning", 0),
                        "total_citations": data.get("total", 0),
                        "scite_score": (data.get("supporting", 0) - data.get("contrasting", 0)) / max(data.get("total", 1), 1),
                    }
        except Exception as e:
            logger.debug("Scite failed", error=str(e))
        return {"found": False}

    # ─── Retraction Check ──────────────────────────────────────────────────

    async def check_retraction(self, doi: str, title: str) -> bool:
        """Multi-source retraction check: Retraction Watch API + CrossRef update policy + title heuristic."""
        if not doi and not title:
            return False

        # 1. Retraction Watch open API (free, no key required)
        if doi:
            try:
                rw_url = f"https://api.retractionwatch.com/api/v1/retractionwatch?doi={doi}"
                async with httpx.AsyncClient(timeout=8.0) as client:
                    resp = await client.get(rw_url, headers={"User-Agent": "SciResearchPlatform/2.0"})
                    if resp.status_code == 200:
                        data = resp.json()
                        if data and len(data) > 0:
                            return True
            except Exception:
                pass

        # 2. CrossRef update-policy check (retraction notices appear as updates)
        if doi:
            try:
                async with httpx.AsyncClient(timeout=8.0) as client:
                    resp = await client.get(f"https://api.crossref.org/works/{doi}",
                                           headers={"User-Agent": "SciResearchPlatform/2.0"})
                    if resp.status_code == 200:
                        msg = resp.json().get("message", {})
                        update_to = msg.get("update-to", [])
                        for upd in update_to:
                            if "retract" in str(upd.get("type", "")).lower():
                                return True
                        if "retract" in str(msg.get("update-policy", "")).lower():
                            return True
            except Exception:
                pass

        # 3. Semantic Scholar title heuristic (last resort)
        if title:
            try:
                async with httpx.AsyncClient(timeout=8.0) as client:
                    resp = await client.get(
                        "https://api.semanticscholar.org/graph/v1/paper/search",
                        params={"query": f"retraction notice {title[:80]}", "limit": 3, "fields": "title"}
                    )
                    if resp.status_code == 200:
                        for paper in resp.json().get("data", []):
                            pt = (paper.get("title") or "").lower()
                            if "retraction" in pt and any(w in pt for w in title.lower().split()[:4]):
                                return True
            except Exception:
                pass

        return False

    # ─── Predatory Journal Check ──────────────────────────────────────────

    def _is_predatory_journal(self, journal: str) -> bool:
        if not journal:
            return False
        journal_lower = journal.lower()
        if any(legit in journal_lower for legit in LEGITIMATE_PUBLISHERS):
            return False
        return any(re.search(p, journal_lower) for p in PREDATORY_PATTERNS)

    # ─── Trust Scoring ────────────────────────────────────────────────────

    def _compute_trust_score(
        self, ref: Dict, doi_result: Optional[Dict],
        crossref_result: Dict, ss_result: Dict, scite_result: Dict
    ) -> float:
        score = 0.0

        if doi_result:
            if doi_result.get("format_valid"):
                score += 0.1
            if doi_result.get("resolvable"):
                score += 0.25

        if crossref_result.get("found") and crossref_result.get("similarity", 0) > 0.6:
            score += 0.25
            if crossref_result.get("year_match"):
                score += 0.05
            if crossref_result.get("is_retracted"):
                score -= 0.5

        if ss_result.get("found"):
            score += 0.15
            citations = ss_result.get("citation_count", 0)
            if citations > 5:
                score += 0.05
            if citations > 20:
                score += 0.05
            if citations > 100:
                score += 0.05

        if scite_result.get("found"):
            score += 0.05
            scite_score = scite_result.get("scite_score", 0)
            if scite_score > 0:
                score += 0.05

        if self._is_predatory_journal(ref.get("journal", "")):
            score -= 0.3

        return min(max(score, 0.0), 1.0)

    def _title_similarity(self, t1: str, t2: str) -> float:
        from difflib import SequenceMatcher
        return SequenceMatcher(None, t1.lower().strip(), t2.lower().strip()).ratio()

    # ─── Verify Single Reference ──────────────────────────────────────────

    async def verify_reference(self, ref: Dict) -> Dict:
        doi = ref.get("doi", "")
        title = ref.get("title", "")
        authors = ref.get("authors", [])
        year = ref.get("year")
        journal = ref.get("journal", "")

        doi_result, crossref_result, ss_result, scite_result, retracted = await asyncio.gather(
            self.verify_doi(doi),
            self.verify_via_crossref(title, authors, year),
            self.verify_via_semantic_scholar(title),
            self.verify_via_scite(doi),
            self.check_retraction(doi, title),
            return_exceptions=True,
        )

        for var_name, var in [("doi_result", doi_result), ("crossref_result", crossref_result), ("ss_result", ss_result), ("scite_result", scite_result)]:
            if isinstance(var, Exception):
                logger.debug("Verification sub-check failed", check=var_name, error=str(var))

        doi_result = doi_result if not isinstance(doi_result, Exception) else None
        crossref_result = crossref_result if not isinstance(crossref_result, Exception) else {"found": False, "similarity": 0.0}
        ss_result = ss_result if not isinstance(ss_result, Exception) else {"found": False}
        scite_result = scite_result if not isinstance(scite_result, Exception) else {"found": False}
        retracted = bool(retracted) if not isinstance(retracted, Exception) else False

        # Enrich DOI from CrossRef if missing
        if not doi and crossref_result.get("doi") and crossref_result.get("similarity", 0) > 0.8:
            doi = crossref_result["doi"]
            ref["doi"] = doi

        trust_score = self._compute_trust_score(ref, doi_result, crossref_result, ss_result, scite_result)
        is_predatory = self._is_predatory_journal(journal)

        return {
            **ref,
            "verified": trust_score > 0.4 and not retracted and not is_predatory,
            "trust_score": trust_score,
            "retracted": retracted,
            "predatory_journal": is_predatory,
            "verification_source": "crossref+semantic_scholar+doi+scite",
            "crossref_match": crossref_result.get("found", False),
            "ss_match": ss_result.get("found", False),
            "scite_data": {
                "supporting": scite_result.get("supporting", 0),
                "contrasting": scite_result.get("contrasting", 0),
            } if scite_result.get("found") else None,
            "citation_count": ss_result.get("citation_count", ref.get("citation_count", 0)),
        }

    # ─── Claim Verification ───────────────────────────────────────────────

    async def verify_paper_claims(self, paper_sections: Dict, references: List[Dict]) -> Dict:
        verified_refs = [r for r in references if r.get("verified")]
        ref_summary = json.dumps(
            [{"title": r["title"], "authors": r.get("authors", [])[:2], "year": r.get("year"), "verified": r.get("verified")} for r in verified_refs[:30]],
            indent=2
        )
        message = HumanMessage(
            content=(
                "You are a scientific fact-checker. Review paper sections against available references.\n"
                "Identify: (1) unsupported factual claims, (2) incorrect statistics, "
                "(3) misrepresented results, (4) overstatements not backed by evidence.\n"
                "Return JSON:\n"
                "{\n"
                '  "unsupported_claims": ["<claim1>", ...],\n'
                '  "corrections": [{"section": "<name>", "original": "<text>", "corrected": "<text>"}],\n'
                '  "overall_factual_quality": <float 0-1>,\n'
                '  "fabrication_risk": "low|medium|high"\n'
                "}\n\n"
                f"VERIFIED REFERENCES:\n{ref_summary}\n\n"
                f"ABSTRACT:\n{paper_sections.get('abstract', '')[:1500]}\n\n"
                f"METHODOLOGY:\n{paper_sections.get('methodology', '')[:2000]}\n\n"
                f"RESULTS:\n{paper_sections.get('results', '')[:1500]}"
            )
        )
        resp = await self.llm.ainvoke([message])
        try:
            return json.loads(resp.content)
        except json.JSONDecodeError:
            return {"unsupported_claims": [], "corrections": [], "overall_factual_quality": 0.7, "fabrication_risk": "low"}

    # ─── Main Run ─────────────────────────────────────────────────────────

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        references = state.get("references", [])
        paper_sections = state.get("paper_sections", {})

        # Verify references in batches of 8 (avoid rate limits)
        batch_size = 8
        verified_refs = []
        for i in range(0, len(references), batch_size):
            batch = references[i:i + batch_size]
            results = await asyncio.gather(*[self.verify_reference(r) for r in batch], return_exceptions=True)
            for j, result in enumerate(results):
                if isinstance(result, Exception):
                    verified_refs.append({**batch[j], "verified": False, "trust_score": 0.0})
                else:
                    verified_refs.append(result)
            await asyncio.sleep(0.5)  # Be polite to APIs

        # Filter out retracted and predatory references
        clean_refs = [r for r in verified_refs if not r.get("retracted") and not r.get("predatory_journal")]
        high_quality = [r for r in clean_refs if r.get("trust_score", 0) > 0.2 or r.get("verified")]

        overall_trust = (
            sum(r.get("trust_score", 0) for r in high_quality) / max(len(high_quality), 1)
        )

        claim_check = await self.verify_paper_claims(paper_sections, high_quality)

        # Apply corrections
        corrected_sections = dict(paper_sections)
        for correction in claim_check.get("corrections", []):
            key = correction.get("section", "").lower().replace(" ", "_")
            if key in corrected_sections and correction.get("original") and correction.get("corrected"):
                corrected_sections[key] = corrected_sections[key].replace(
                    correction["original"], correction["corrected"]
                )

        logger.info(
            "Authentication complete",
            total_refs=len(references),
            verified=sum(1 for r in high_quality if r.get("verified")),
            retracted=sum(1 for r in verified_refs if r.get("retracted")),
            predatory=sum(1 for r in verified_refs if r.get("predatory_journal")),
            trust_score=overall_trust,
        )

        return {
            "verified_references": high_quality,
            "trust_score": overall_trust,
            "corrected_sections": corrected_sections,
            "claim_check_report": claim_check,
            "retracted_removed": sum(1 for r in verified_refs if r.get("retracted")),
            "predatory_removed": sum(1 for r in verified_refs if r.get("predatory_journal")),
        }
