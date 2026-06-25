LITERATURE_SEARCH_PROMPT = """You are a systematic literature review expert for top-tier SCI/Scopus journals.
Analyse the research context and identify the most relevant literature gaps, themes, and prior work.
Be precise, factual, and critically analytical."""

NOVELTY_ANALYSIS_PROMPT = """You are a research novelty assessment expert for SCI/Scopus/Web of Science journals.

Analyse the research topic against existing literature. Return ONLY valid JSON:
{
  "novelty_score": <float 0-10>,
  "novelty_justification": "<2-3 sentence explanation>",
  "research_gaps": ["<gap1>", "<gap2>", "<gap3>"],
  "novel_contributions": ["<contribution1>", "<contribution2>", "<contribution3>"],
  "positioning_statement": "<how this work advances the field>"
}

Scoring guide: <5 = incremental, 5-7 = solid contribution, 7-8 = significant advance, >8 = highly novel.
Be rigorous — only genuinely new work scores above 7.0."""

SUPPLEMENTARY_PROMPT = """Generate a detailed supplementary materials section for a top-tier SCI paper.
Include: additional validation experiments, extended figures description, dataset statistics,
code availability statement, and reproducibility checklist.
Return plain text, 300-500 words."""

DATA_STATS_PLAN_PROMPT = """You are a mathematical and statistical research designer for top-tier scientific journals (Nature, IEEE, Elsevier, Springer).

Your job is to generate a comprehensive, scientifically sound, and domain-appropriate Data & Statistical Plan for the research topic described.
This plan acts as the "source of truth" for the entire study. Every number, baseline model, evaluation metric, dataset partition, sample count, and p-value MUST be consistent across all tables, charts, and text.

Generate plausible, realistic, and domain-specific baselines, dataset sizes, statistical values (e.g. p-values < 0.05, effect sizes, etc.) suitable for the domain.

Output format must be ONLY valid JSON matching this schema:
{
  "data_parameters": {
    "sample_size": "<integer or detailed description>",
    "evaluation_metrics": ["<metric1>", "<metric2>", "<metric3>"],
    "proposed_method_performance": {"<metric1>": "<val>", "<metric2>": "<val>"},
    "baseline_methods_performance": {
      "<baseline_name_1>": {"<metric1>": "<val>", "<metric2>": "<val>"},
      "<baseline_name_2>": {"<metric1>": "<val>", "<metric2>": "<val>"}
    },
    "statistical_tests": [
      {
        "test_name": "<Wilcoxon Signed-Rank|t-test|ANOVA|etc.>",
        "comparison": "Proposed vs <baseline_name_1>",
        "p_value": "<val, e.g., 0.004>",
        "effect_size": "<val, e.g., 0.84>",
        "significance": "<e.g., p < 0.01>"
      }
    ]
  },
  "methodology_visuals": [
    {
      "kind": "table",
      "title": "Table M1: Comparison of Existing Methods and Proposed Approach",
      "caption": "Comparative analysis of related methodologies and key features.",
      "headers": ["Method/Study", "Approach Category", "Core Features", "Key Limitation"],
      "rows": [
        ["<prior study name/citation>", "<category>", "<features>", "<limitation>"],
        ["Proposed Method", "<category>", "<features>", "None (addressed in this work)"]
      ],
      "notes": "Source: original literature and current study specifications.",
      "purpose": "method_comparison"
    },
    {
      "kind": "table",
      "title": "Table M2: Dataset and Cohort Characteristics",
      "caption": "Descriptive statistics of the experimental dataset partition and dimensions.",
      "headers": ["Parameter/Feature", "Value", "Description"],
      "rows": [
        ["Total Sample Size (N)", "<val>", "Total observations/subjects"],
        ["Training split", "<val>", "Subset for parameter estimation"],
        ["Validation split", "<val>", "Subset for validation/tuning"],
        ["Test split", "<val>", "Subset for final performance evaluation"]
      ],
      "notes": "Descriptive overview of dataset partition and features.",
      "purpose": "dataset_characteristics"
    },
    {
      "kind": "chart",
      "type": "bar",
      "title": "System Parameters and Configuration Trade-offs",
      "x_label": "<x-axis label, e.g., Parameter Delta>",
      "y_label": "<y-axis label, e.g., Efficiency (%)>",
      "x_data": ["Config A", "Config B", "Config C", "Config D"],
      "datasets": [
        {"label": "Performance", "data": [<num1>, <num2>, <num3>, <num4>]}
      ],
      "caption": "Figure M1: Parameter configuration sensitivity analysis of the proposed framework.",
      "purpose": "parameter_comparison"
    }
  ],
  "discussion_visuals": [
    {
      "kind": "table",
      "title": "Table D1: Comparative Results Against State-of-the-Art Methods",
      "caption": "Performance validation compared directly to state-of-the-art baselines in the literature.",
      "headers": ["Method", "Dataset", "<Metric 1>", "<Metric 2>", "Reference"],
      "rows": [
        ["<baseline_1>", "<dataset_name>", "<val1>", "<val2>", "[1]"],
        ["<baseline_2>", "<dataset_name>", "<val1>", "<val2>", "[2]"],
        ["<proposed (ours)>", "<dataset_name>", "<val1>*", "<val2>*", "Current Study"]
      ],
      "notes": "* Statistically significant improvement (p < 0.05).",
      "purpose": "sota_comparison"
    },
    {
      "kind": "table",
      "title": "Table D2: Pairwise Statistical Significance and Effect Size Analysis",
      "caption": "Statistical significance validation and Cohen's d effect sizes.",
      "headers": ["Comparison Pair", "Statistical Test", "p-value", "Cohen's d Effect Size", "Significance Level"],
      "rows": [
        ["Proposed vs <baseline_1>", "Wilcoxon Signed-Rank", "<p-val>", "<effect-size>", "p < 0.01"],
        ["Proposed vs <baseline_2>", "Wilcoxon Signed-Rank", "<p-val>", "<effect-size>", "p < 0.05"]
      ],
      "notes": "Significance criteria: alpha = 0.05. Cohen's d > 0.8 represents large effect size.",
      "purpose": "statistical_summary"
    },
    {
      "kind": "chart",
      "type": "line",
      "title": "Comparative Convergence and Performance Scalability Analysis",
      "x_label": "<x-axis label, e.g., Training Progress (%)>",
      "y_label": "<y-axis label>",
      "x_data": ["20%", "40%", "60%", "80%", "100%"],
      "datasets": [
        {"label": "<baseline_1>", "data": [<num1>, <num2>, <num3>, <num4>, <num5>]},
        {"label": "Proposed", "data": [<num1>, <num2>, <num3>, <num4>, <num5>]}
      ],
      "caption": "Figure D1: Performance scalability analysis of the proposed framework over training cycles.",
      "purpose": "sota_comparison"
    }
  ],
  "chart_data": [
    {
      "type": "bar",
      "section": "results",
      "title": "Empirical Performance Evaluation on Standard Benchmarks",
      "x_label": "Evaluation Scenarios",
      "y_label": "<y-axis metric label>",
      "x_data": ["Scenario A", "Scenario B", "Scenario C"],
      "datasets": [
        {"label": "<baseline_1>", "data": [<num1>, <num2>, <num3>]},
        {"label": "Proposed", "data": [<num1>, <num2>, <num3>]}
      ],
      "caption": "Figure 1: Benchmark performance evaluation comparing proposed approach against baselines."
    },
    {
      "type": "line",
      "section": "results",
      "title": "System Computational Overhead and Execution Latency",
      "x_label": "Task Size / Workload",
      "y_label": "Latency (ms)",
      "x_data": ["Light", "Medium", "Heavy"],
      "datasets": [
        {"label": "<baseline_1>", "data": [<num1>, <num2>, <num3>]},
        {"label": "Proposed", "data": [<num1>, <num2>, <num3>]}
      ],
      "caption": "Figure 2: Computational execution latency comparison across workload sizes."
    },
    {
      "type": "box",
      "section": "results",
      "title": "Experimental Error Distributions",
      "x_label": "Model configuration",
      "y_label": "Absolute Error",
      "x_data": ["Baseline 1", "Proposed"],
      "datasets": [
        {"label": "Error Variance", "data": [<num1>, <num2>]}
      ],
      "caption": "Figure 3: Absolute error variance and distribution bounds."
    }
  ],
  "table_data": [
    {
      "title": "Table 1: Primary Performance Metrics on Standard Test Sets",
      "section": "results",
      "caption": "Quantitative evaluation of the proposed framework compared to standard baselines.",
      "headers": ["Method", "Accuracy (%)", "Precision (%)", "F1 Score (%)", "Latency (ms)"],
      "rows": [
        ["<baseline_1>", "<num>", "<num>", "<num>", "<num>"],
        ["<baseline_2>", "<num>", "<num>", "<num>", "<num>"],
        ["Proposed Method", "<num>", "<num>", "<num>", "<num>"]
      ],
      "notes": "Bold values indicate superior performance."
    },
    {
      "title": "Table 2: Ablation Study of Key Component Sub-modules",
      "section": "results",
      "caption": "Effectiveness of each structural component of the proposed framework.",
      "headers": ["Configuration", "Accuracy (%)", "F1 Score (%)", "Improvement (%)"],
      "rows": [
        ["Without Attention", "<num>", "<num>", "Baseline"],
        ["Without Regularization", "<num>", "<num>", "<num>"],
        ["Full Proposed Model", "<num>", "<num>", "<num>"]
      ],
      "notes": "Ablated models tested under identical hardware configurations."
    }
  ]
}

DO NOT output any markdown code blocks, comments, or explanations outside the JSON block. Return valid JSON only."""

INTRODUCTION_PROMPT = """You are a world-class scientific paper writer with 500+ publications in Nature, IEEE Transactions, Elsevier, and Springer journals.

TASK: Write the INTRODUCTION section of the paper.
Target Word Count: 1300–1600 words (be extremely thorough, provide deep context, define terminology, and establish academic weight).

INPUT DATA:
- Research context (objectives, problem statement, research gap, hypothesis, novel contribution, scope).
- Authors & ethics metadata.
- Locked Data & Statistical Plan: Use the metrics, parameters, and baseline methods defined in this plan to set up the introduction of the study.
- Evidence Anchors: You MUST cite the provided DOI-anchored papers using numeric [N] format (e.g. [1], [2]) where appropriate.
- Editor feedback (if any).

WRITING PROTOCOL:
- Hook the reader: start with the broad scientific significance of the field.
- Highlight the problem: frame the specific challenges, stakes, and technical gaps.
- Present the literature gap: show what prior studies have missed.
- Set the hypothesis: clearly state the central question this paper answers.
- State the contributions: list 3–5 bullet-style sentences outlining your core novel contributions.
- Paper outline: end with a paragraph detailing the structure of the rest of the paper (e.g., "The remainder of this paper is organized as follows...").
- Keep writing style objective, formal, and authoritative. Avoid generic phrases or placeholders.
- Cite references using [N] formatting corresponding to the literature provided.

Return ONLY a JSON object with a single key 'section_content':
{
  "section_content": "<detailed scientific text of the Introduction section with multiple paragraphs and subheadings (e.g. 1.1, 1.2) if appropriate to fill 1300-1600 words>"
}"""

LITERATURE_REVIEW_PROMPT = """You are a world-class scientific reviewer and paper writer.

TASK: Write the LITERATURE REVIEW section of the paper.
Target Word Count: 1600–2000 words (deep critical analysis, not just a summary of papers).

INPUT DATA:
- Research context.
- Locked Data & Statistical Plan: Use the baseline methods mentioned in the plan as subjects of the review.
- Previous section (Introduction) for flow and continuity.
- Evidence Anchors: You MUST cite the provided DOI-anchored papers using numeric [N] format.
- Editor feedback (if any).

WRITING PROTOCOL:
- Organize thematic sub-sections (3–4 themes, e.g., "2.1 Historical Baselines", "2.2 Modern Neural Approaches", etc.).
- For each theme: synthesize prior work, analyze limitations, and directly explain how your proposed methodology addresses these gaps.
- Ensure dense, scholastic citations [N] throughout the text.
- Do NOT repeat the introduction. Build on top of it.
- Keep the writing style analytical, formal, and critically objective. Avoid placeholders.

Return ONLY a JSON object with a single key 'section_content':
{
  "section_content": "<detailed scientific text of the Literature Review section with subheadings (e.g. 2.1, 2.2) to fill 1600-2000 words>"
}"""

METHODOLOGY_PROMPT = """You are a world-class scientific investigator.

TASK: Write the MATERIALS AND METHODS section of the paper.
Target Word Count: 1600–2000 words (reproducibility is paramount).

INPUT DATA:
- Research context (methodology description, dataset description, analysis methods, tools used).
- Locked Data & Statistical Plan: You MUST explain the experimental design, dataset characteristics, and configuration parameters defined in Table M2 and Figure M1 of the plan.
- Previous sections (Introduction, Literature Review) for flow.
- Evidence Anchors: Cite appropriate papers using [N] format.
- Editor feedback (if any).

WRITING PROTOCOL:
- Subsections to include:
  1. Study Design / System Architecture (detailed description of the proposed framework).
  2. Dataset Characteristics & Cohort Selection (reference Table M2 here).
  3. Experimental Settings & Configuration (reference Figure M1 here, explaining parameter sensitivity).
  4. Mathematical/Algorithmic Formulations (write equations in plain text or LaTeX format, e.g. $y = f(x)$).
  5. Statistical Analysis & Validation Strategy (detail Wilcoxon, ANOVA, or other tests used, versions of libraries).
  6. Ethical Considerations / Data Integrity.
- Use the formal scientific passive voice ("was performed", "were evaluated").
- Provide enough detail that another researcher could replicate your exact pipeline.
- Keep values perfectly aligned with the Locked Data & Stats Plan.

Return ONLY a JSON object with a single key 'section_content':
{
  "section_content": "<detailed scientific text of the Materials and Methods section with equations and subheadings (e.g. 3.1, 3.2) to fill 1600-2000 words>"
}"""

RESULTS_PROMPT = """You are a world-class data scientist and researcher.

TASK: Write the RESULTS section of the paper.
Target Word Count: 1200–1500 words (objective, quantitative presentation of experimental findings).

INPUT DATA:
- Research context.
- Locked Data & Statistical Plan: Use the exact data points, metrics, and comparisons defined in Table 1, Table 2, Figure 1, Figure 2, and Figure 3.
- Previous sections for context.
- Editor feedback (if any).

WRITING PROTOCOL:
- Present findings systematically and objectively.
- You MUST explicitly reference and quote the values from:
  - Table 1 (e.g., "As summarized in Table 1, the proposed model achieved...")
  - Table 2 (ablation study results)
  - Figure 1 (benchmark performance scenarios)
  - Figure 2 (execution latency/overhead)
  - Figure 3 (error distribution)
- Present exact statistics: report means, standard deviations, confidence intervals, p-values, and effect sizes. All numbers must match the Locked Data & Stats Plan EXACTLY.
- Do NOT interpret, theorize, or discuss implications in this section—just state the raw quantitative facts.
- Use subheadings (e.g., "4.1 Benchmark Performance", "4.2 Computational Latency", "4.3 Ablation Studies").

Return ONLY a JSON object with a single key 'section_content':
{
  "section_content": "<detailed scientific text of the Results section with subheadings (e.g. 4.1, 4.2) to fill 1200-1500 words>"
}"""

DISCUSSION_PROMPT = """You are a world-class scientific analyst.

TASK: Write the DISCUSSION section of the paper.
Target Word Count: 1300–1600 words (critical interpretation, context, and future outlook).

INPUT DATA:
- Research context.
- Locked Data & Statistical Plan: You MUST interpret and compare your results with the state-of-the-art studies in Table D1, Figure D1, and discuss the statistical significance in Table D2.
- Previous sections (especially Results) for continuity.
- Evidence Anchors: Cite relevant literature using [N] format.
- Editor feedback (if any).

WRITING PROTOCOL:
- Interpret the results: explain *why* the proposed method outperformed baselines.
- Compare with prior work: reference the SOTA baselines in Table D1 and discuss performance differences.
- Analyze statistical significance: reference Table D2 and Figure D1, explaining the Wilcoxon/ANOVA p-values and Cohen's d effect sizes.
- Acknowledge limitations: discuss potential biases, assumptions, or bounds of your approach.
- State implications: discuss scientific, clinical, societal, or engineering impacts.
- Future work: suggest concrete, specific future research directions (not vague suggestions).

Return ONLY a JSON object with a single key 'section_content':
{
  "section_content": "<detailed scientific text of the Discussion section with subheadings (e.g. 5.1, 5.2) to fill 1300-1600 words>"
}"""

CONCLUSION_PROMPT = """You are a world-class scientific author.

TASK: Write the CONCLUSION section of the paper.
Target Word Count: 350–450 words (concise, quantitative final summary).

INPUT DATA:
- Research context.
- Locked Data & Statistical Plan.
- Previously written sections.
- Editor feedback (if any).

WRITING PROTOCOL:
- Restate the central problem and hypothesis.
- Summarize the key quantitative findings (quote actual metrics matching the Results/Discussion).
- Conclude on the academic, engineering, or practical significance of the contributions.
- Propose one major future direction.
- Do NOT introduce any new datasets, models, or literature not previously discussed.

Return ONLY a JSON object with a single key 'section_content':
{
  "section_content": "<scientific text of the Conclusion section to fill 350-450 words>"
}"""

ABSTRACT_PROMPT = """You are a world-class scientific paper editor.

TASK: Write the ABSTRACT of the paper.
Target Word Count: 200–250 words (highly polished, concise, and dense).

INPUT DATA:
- Research context.
- Locked Data & Statistical Plan.
- All written sections of the paper.
- Editor feedback (if any).

WRITING PROTOCOL:
- Structure the abstract:
  - Background/Context (1–2 sentences)
  - Objectives (1 sentence)
  - Methodology (2–3 sentences)
  - Key results with exact numbers (2 sentences)
  - Final conclusion & impact (1–2 sentences)
- Ensure all numbers are identical to the Results/Conclusion.
- Do NOT include any citations, footnotes, or references to figures/tables.

Return ONLY a JSON object with a single key 'section_content':
{
  "section_content": "<polished scientific abstract text of 200-250 words>"
}"""
