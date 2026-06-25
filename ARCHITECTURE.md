# SCI Research Platform — Advanced Multi-Agent Architecture

## Overview

A completely automated, production-grade multi-agent AI platform designed to generate scientific papers that meet the rigorous standards of the **top 1% of SCI/Scopus/Web of Science journals**. 

To achieve this elite quality, the platform abandons linear generation in favor of a **Deep Hierarchical Session Architecture**. Every chapter (Introduction, Methods, Results, Discussion, etc.) is treated as an isolated, high-intensity "Session". Within each session, specialized sub-agents independently handle text drafting, data validation, figure generation, and table formatting. 

The entire process is governed deterministically by a **Final Editorial Manager (Release Gate)**, ensuring 95%+ efficiency, zero system hangs, and zero requirement for human intervention prior to final approval.

## Architecture Diagram

```text
┌─────────────────────────────────────────────────────────────────┐
│                     CLIENT LAYER (Next.js)                       │
│  User Dashboard | Editor Dashboard | Admin Dashboard             │
│  Research Input | Raw Data Upload | Real-time Tracking           │
└──────────────────────┬──────────────────────────────────────────┘
                       │ HTTPS / WebSocket
┌──────────────────────▼──────────────────────────────────────────┐
│                    API GATEWAY (FastAPI)                          │
│  Auth (Clerk) | Rate Limiting | Request Routing | WebSocket Hub  │
└──────┬────────────────────────────────────────────┬─────────────┘
       │                                            │
┌──────▼──────────┐                    ┌────────────▼────────────┐
│   Task Queue    │                    │    PostgreSQL + Redis    │
│  Celery + Redis │                    │  Sessions | Cache | Jobs │
└──────┬──────────┘                    └─────────────────────────┘
       │
┌──────▼──────────────────────────────────────────────────────────┐
│         MULTI-AGENT ORCHESTRATION (LangGraph / Celery)           │
│                                                                  │
│  1. PRE-PROCESSING PHASE                                         │
│  ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │
│  │ Normalize│→ │ Extract  │→ │ Retrieve │→ │ Evidence Mapping │ │
│  │ Inputs   │  │  Data    │  │ Sources  │  │ (DOI grounding)  │ │
│  └─────────┘  └──────────┘  └──────────┘  └────────┬─────────┘ │
│                                                      │           │
│  2. HIERARCHICAL SESSION PHASE (Chapter-by-Chapter)  ▼           │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │ SESSION CONTROLLER (e.g., "Results Chapter Session")      │   │
│  │                                                           │   │
│  │ ┌────────────┐ ┌─────────────┐ ┌────────────┐ ┌─────────┐ │   │
│  │ │ Text Agent │ │Figure Agent │ │Table Agent │ │Methods &│ │   │
│  │ │ (Drafting) │ │(Graphs/Viz) │ │(Formatting)│ │Stats QA │ │   │
│  │ └────────────┘ └─────────────┘ └────────────┘ └─────────┘ │   │
│  │        ▼              ▼              ▼             ▼      │   │
│  │ ┌───────────────────────────────────────────────────────┐ │   │
│  │ │       CHAPTER-LEVEL REVIEWER (SCI Standard Check)     │ │   │
│  │ └───────────────────────────────────────────────────────┘ │   │
│  └───────────────────────────┬───────────────────────────────┘   │
│                              │                                   │
│  3. GLOBAL REVIEW & RELEASE GATE PHASE                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────────────┐   │
│  │Compliance│→ │Plagiarism│→ │ Audit /  │→ │ FINAL EDITORIAL │   │
│  │ & Ethics │  │  Guard   │  │ Conflict │  │    MANAGER      │   │
│  └──────────┘  └──────────┘  └──────────┘  └────────┬────────┘   │
│      ▲                                              │            │
│      └────────────────(REPAIR DISPATCH)─────────────┘            │
│                                                     │            │
│  4. PACKAGING PHASE                                 ▼            │
│                                          ┌─────────────────────┐ │
│                                          │  Document Generator │ │
│                                          │  (.docx, .pdf, tex) │ │
│                                          └─────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

## Deep Hierarchical Session Architecture

To prevent shallow summaries and ensure deep, high-fidelity scientific writing, the document generation is broken down into **Sessions** (Chapters).

1. **Session Controller**: Orchestrates the specific chapter. It receives the mapped evidence and strict word/depth requirements dictated by the target journal.
2. **Parallel Sub-Agents**:
   - **Text Agent**: Drafts deep scientific prose, ensuring logical flow, dense academic language, and zero fluff. If a section requires 1,500 words of rigorous analysis, this agent is constrained to deliver exactly that.
   - **Figure & Graph Agent**: Generates publication-grade graphs using Python (Matplotlib/Seaborn) based on raw data inputs, ensuring axes, legends, and DPI meet SCI standards.
   - **Table Agent**: Formats complex data into APA/SCI compliant tables.
   - **Methods & Stats QA Agent**: Validates p-values, sample sizes, and experimental design strictly within the text to ensure mathematical and scientific soundness.
3. **Chapter-Level Reviewer**: Evaluates the combined output of the sub-agents for that specific chapter. If the depth, citation density, or visual quality is lacking, it forces the specific sub-agent to iterate *before* the chapter is passed to the global flow.

## The Final Editorial Manager (Release Gate)

The previous architecture relied on a soft "score loop" (loop if score < 9), which can cause infinite hanging or timeout errors. This is replaced by the **Final Editorial Manager**, acting as a highly deterministic Release Gate.

- **Role**: The ultimate gatekeeper. It acts like a strict human Editor-in-Chief.
- **Action**: It scans the fully assembled document. If it detects an issue (e.g., a citation mismatch, a poorly formatted graph, a weak argument), it **does not loop the entire system**. Instead, it dispatches a highly specific "Repair Job" directly to the responsible department (e.g., sending a graph back to the Figure Agent with explicit correction instructions).
- **State Machine Enforcement**:
  - State progression is strictly tracked: `QUEUED` -> `RUNNING` -> `VERIFYING` -> `REPAIR_DISPATCHED` -> `APPROVED`.
  - Timeouts and strict retry limits are enforced. If a sub-agent fails to fix an issue after a set number of attempts, deterministic fail-safes are engaged, ensuring the pipeline *never* hangs and maintains 95%+ throughput efficiency.

## Key Agents in the Revised Pipeline

1. **Journal Intelligence Agent**: Sets the constraints (word limits, citation style, figure limits) based on the target journal *before* drafting begins.
2. **Evidence Mapper Agent**: Ties every claim to an exact DOI/Source paragraph to mathematically eliminate hallucination.
3. **Session Sub-Agents (Text, Figure, Table, Stats)**: Ensure deep, specialized generation per chapter.
4. **Final Editorial Manager**: The Release Gate Controller for targeted, parallel repairs.
