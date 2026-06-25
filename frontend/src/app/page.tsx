"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { ArrowRight, Zap, Shield, FileText, Brain, BarChart3, Award, CheckCircle, Code2, BookMarked, Telescope } from "lucide-react";

const FEATURES = [
  { icon: Brain,      title: "11-Source Literature Engine",   desc: "Semantic Scholar, CrossRef, arXiv, PubMed, OpenAlex, CORE, Europe PMC, Scite, Google Scholar, Unpaywall + Tavily — all queried in parallel." },
  { icon: Shield,     title: "Zero Hallucinated References",  desc: "Every citation verified via DOI resolver, CrossRef, Scite retraction database, and predatory journal blacklist before inclusion." },
  { icon: Zap,        title: "AI Detection < 5%",            desc: "Iterative Claude humanization loop rewrites every sentence until it passes all AI detection thresholds — ready for any journal." },
  { icon: Code2,      title: "LaTeX + BibTeX Export",        desc: "Download publication-ready .tex files pre-formatted for Nature, IEEE, Elsevier. Paste directly into Overleaf or your LaTeX editor." },
  { icon: BarChart3,  title: "7-Dimension Editor Scoring",   desc: "Automated Editor-in-Chief agent scores novelty, methodology, clarity, literature, results, technical depth, and journal readiness — retries until ≥ 9.0/10." },
  { icon: Telescope,  title: "Journal Fit Recommendations",  desc: "Platform analyses your domain and suggests the 5 best journals with impact factors, quartile rankings, and submission likelihood." },
  { icon: FileText,   title: "Complete Submission Package",  desc: "Full paper .docx with embedded charts, personalised cover letter, reviewer response letter, editorial quality report — one click." },
  { icon: Award,      title: "SCI / Scopus / IEEE Ready",    desc: "Supports all major citation styles: APA, MLA, IEEE, Chicago, Harvard, Vancouver, Nature, ACS. Auto-formats for your target journal." },
  { icon: BookMarked, title: "Reference Manager Export",     desc: ".bib file for Zotero, Mendeley, and EndNote. All references include DOI, open-access status, and citation counts." },
];

const PIPELINE_STEPS = [
  { label: "User Input + Files",      desc: "Research topic, methodology, uploaded data/PDFs" },
  { label: "Multi-Modal Extraction",  desc: "OCR, Camelot, Tabula, Tesseract, Unstructured.io" },
  { label: "Literature Research",     desc: "11 academic databases queried in parallel" },
  { label: "Data Intelligence",       desc: "AI-generated charts, tables, statistical visuals" },
  { label: "Reference Authentication",desc: "DOI verification, retraction check, trust scoring" },
  { label: "Plagiarism + AI Scan",    desc: "< 15% similarity · < 5% AI detection" },
  { label: "AI Humanization",         desc: "Iterative rewrite until AI score drops below threshold" },
  { label: "Figures & Table Audit",   desc: "Caption check, TOC generation, BibTeX export" },
  { label: "Editor Review Loop",      desc: "7-dimension score — retries until ≥ 9.0/10" },
  { label: "Document Generation",     desc: "DOCX + Cover Letter + LaTeX + BibTeX + Report" },
];

const STATS = [
  { value: "11",    label: "Literature Sources",   sub: "queried per paper" },
  { value: "< 5%",  label: "AI Detection Rate",    sub: "guaranteed threshold" },
  { value: "< 15%", label: "Plagiarism Score",     sub: "enforced by pipeline" },
  { value: "9.0+",  label: "Min. Editor Score",    sub: "out of 10" },
];

const JOURNALS = ["Nature", "IEEE", "Elsevier", "Springer", "Wiley", "ACS", "PLOS", "BMC"];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 overflow-x-hidden">

      {/* ── Navigation ── */}
      <nav className="fixed top-0 w-full z-50 bg-gray-950/80 backdrop-blur-md border-b border-gray-800">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }}
            className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
              <Brain className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-lg tracking-tight">SCI Research Platform</span>
          </motion.div>
          <div className="flex items-center gap-4">
            <Link href="/sign-in" className="text-sm text-gray-400 hover:text-white transition-colors">Sign In</Link>
            <Link href="/sign-up" className="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-sm font-semibold transition-colors">
              Get Started Free
            </Link>
          </div>
        </div>
      </nav>

      {/* ── Hero ── */}
      <section className="pt-32 pb-20 px-6">
        <div className="max-w-5xl mx-auto text-center">
          <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}>
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-sm mb-8">
              <Zap className="w-3.5 h-3.5" />
              10-Agent Pipeline · LaTeX + BibTeX Export · Editor Score ≥ 9/10 · SCI Journal Ready
            </div>
            <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-6 leading-tight">
              Accelerate Your Research
              <br />
              <span className="gradient-text">From Data to Submission</span>
            </h1>
            <p className="text-xl text-gray-400 max-w-2xl mx-auto mb-10 leading-relaxed">
              Upload your raw research data, hypotheses, and methodology. Our 10-agent AI pipeline generates
              a fully verified, plagiarism-checked, humanized scientific paper — complete with LaTeX source,
              BibTeX references, cover letter, and journal recommendations.
            </p>
            <div className="flex items-center justify-center gap-4 flex-wrap">
              <Link href="/dashboard"
                className="group flex items-center gap-2 px-8 py-4 bg-blue-600 hover:bg-blue-500 rounded-xl text-base font-semibold transition-all duration-200 glow-blue">
                Start Your Research
                <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </Link>
              <Link href="/dashboard"
                className="px-8 py-4 border border-gray-700 hover:border-gray-500 rounded-xl text-base font-medium transition-colors">
                View Sample Output
              </Link>
            </div>
          </motion.div>
        </div>
      </section>

      {/* ── Stats bar ── */}
      <section className="py-10 px-6 border-y border-gray-800 bg-gray-900/40">
        <div className="max-w-4xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-6">
          {STATS.map((s, i) => (
            <motion.div key={s.label} initial={{ opacity: 0, y: 10 }} whileInView={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.08 }} className="text-center">
              <div className="text-3xl font-bold gradient-text">{s.value}</div>
              <div className="text-sm font-semibold text-gray-300 mt-1">{s.label}</div>
              <div className="text-xs text-gray-600">{s.sub}</div>
            </motion.div>
          ))}
        </div>
      </section>

      {/* ── Journal compatibility strip ── */}
      <section className="py-8 px-6 border-b border-gray-800">
        <div className="max-w-4xl mx-auto">
          <p className="text-center text-xs text-gray-600 uppercase tracking-widest mb-5">
            Formatted for submission to publishers including
          </p>
          <div className="flex flex-wrap justify-center items-center gap-6">
            {JOURNALS.map((j) => (
              <span key={j} className="text-sm font-semibold text-gray-500 hover:text-gray-300 transition-colors cursor-default">
                {j}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* ── Pipeline visualization ── */}
      <section className="py-20 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-12">
            <span className="text-xs text-blue-400 font-semibold tracking-widest uppercase">How it works</span>
            <h2 className="text-3xl font-bold mt-3 mb-3">Automated 10-Stage Research Pipeline</h2>
            <p className="text-gray-500 max-w-xl mx-auto text-sm">Every stage is fully automated. You provide the research context — we produce the submission-ready paper.</p>
          </div>
          <div className="relative">
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
              {PIPELINE_STEPS.map((step, i) => (
                <motion.div key={step.label}
                  initial={{ opacity: 0, y: 15 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.06 }}
                  className="glass-card p-4 relative group hover:border-blue-500/30 transition-colors">
                  <div className="w-6 h-6 rounded-full bg-blue-600/20 border border-blue-600/40 flex items-center justify-center text-xs font-bold text-blue-400 mb-2">
                    {i + 1}
                  </div>
                  <p className="text-xs font-semibold text-gray-200 leading-tight mb-1">{step.label}</p>
                  <p className="text-xs text-gray-600 leading-relaxed hidden group-hover:block">{step.desc}</p>
                </motion.div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── Features grid ── */}
      <section className="py-20 px-6 bg-gray-900/30">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <span className="text-xs text-purple-400 font-semibold tracking-widest uppercase">Capabilities</span>
            <h2 className="text-4xl font-bold mt-3 mb-4">
              Built for <span className="gradient-text">Serious Researchers</span>
            </h2>
            <p className="text-gray-400 max-w-lg mx-auto text-sm">
              Every feature engineered to meet the standards of top-tier international journals.
            </p>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
            {FEATURES.map((feature, i) => (
              <motion.div key={feature.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.07 }}
                className="glass-card p-6 hover:border-blue-500/30 transition-colors group">
                <div className="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center mb-4 group-hover:bg-blue-500/20 transition-colors">
                  <feature.icon className="w-5 h-5 text-blue-400" />
                </div>
                <h3 className="font-semibold text-base mb-2">{feature.title}</h3>
                <p className="text-gray-500 text-sm leading-relaxed">{feature.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ── What you get ── */}
      <section className="py-20 px-6">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold mb-3">Every Project Delivers</h2>
            <p className="text-gray-500 text-sm">Six export formats, zero additional work.</p>
          </div>
          <div className="grid md:grid-cols-2 gap-4">
            {[
              { icon: FileText, color: "emerald", title: "Full Paper (.docx)", desc: "Complete paper with embedded bar charts, line charts, and data tables — formatted for target journal." },
              { icon: Code2,    color: "orange",  title: "LaTeX Source (.tex)", desc: "Overleaf-ready .tex file with correct citation commands, section structure, and journal formatting packages." },
              { icon: BookMarked, color: "cyan",  title: "BibTeX References (.bib)", desc: "All verified references with DOIs, author names, journal names — import directly into Zotero or Mendeley." },
              { icon: FileText, color: "blue",    title: "Cover Letter (.docx)", desc: "Personalised to the target journal with author credentials, paper significance, and novelty highlights." },
              { icon: Shield,   color: "purple",  title: "Reviewer Response (.docx)", desc: "Pre-written response to anticipated reviewer comments — saves days of post-review revision work." },
              { icon: BarChart3, color: "yellow", title: "Editorial Report (.docx)", desc: "Full 7-dimension quality audit with section-by-section feedback, scores, and improvement recommendations." },
            ].map((item, i) => (
              <motion.div key={item.title}
                initial={{ opacity: 0, x: i % 2 === 0 ? -20 : 20 }}
                whileInView={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.07 }}
                className="flex items-start gap-4 p-5 glass-card hover:border-gray-600 transition-colors">
                <div className={`w-10 h-10 rounded-lg bg-${item.color}-500/10 flex items-center justify-center flex-shrink-0`}>
                  <item.icon className={`w-5 h-5 text-${item.color}-400`} />
                </div>
                <div>
                  <p className="font-semibold text-sm text-gray-100 mb-1">{item.title}</p>
                  <p className="text-xs text-gray-500 leading-relaxed">{item.desc}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Quality guarantees ── */}
      <section className="py-14 px-6 bg-gray-900/30">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-center text-2xl font-bold mb-8 text-gray-200">Quality Gates — Non-Negotiable</h2>
          <div className="space-y-3">
            {[
              { check: "Plagiarism score < 15%",   detail: "Enforced by sentence-transformer similarity scan" },
              { check: "AI detection score < 5%",  detail: "Iterative Claude humanization loop with 7-signal heuristic" },
              { check: "Editor score ≥ 9.0 / 10",  detail: "7-dimension weighted rubric, auto-retries weakest module" },
              { check: "All references DOI-verified", detail: "CrossRef + Scite retraction check + predatory journal filter" },
              { check: "Reference trust score > 0.6", detail: "Scite citation intelligence scoring per paper" },
              { check: "Minimum 15 verified references", detail: "Pipeline blocks finalization until threshold is met" },
            ].map((item, i) => (
              <motion.div key={item.check}
                initial={{ opacity: 0, x: -15 }}
                whileInView={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.06 }}
                className="flex items-start gap-3 p-4 glass-card">
                <CheckCircle className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-semibold text-gray-100">{item.check}</p>
                  <p className="text-xs text-gray-500 mt-0.5">{item.detail}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA ── */}
      <section className="py-24 px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          className="max-w-3xl mx-auto text-center glass-card p-14">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs mb-6">
            <CheckCircle className="w-3 h-3" /> Pipeline verified · All quality gates active
          </div>
          <h2 className="text-4xl font-bold mb-4">
            Ready to Publish in <span className="gradient-text">Top-Tier Journals?</span>
          </h2>
          <p className="text-gray-400 mb-10 max-w-lg mx-auto">
            From raw research inputs to a complete submission package — in one automated pipeline.
          </p>
          <Link href="/dashboard"
            className="inline-flex items-center gap-2 px-12 py-4 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 rounded-xl text-lg font-bold transition-all duration-200">
            Begin Your Research
            <ArrowRight className="w-5 h-5" />
          </Link>
          <p className="text-xs text-gray-700 mt-5">No credit card required · First paper free</p>
        </motion.div>
      </section>

      {/* ── Footer ── */}
      <footer className="border-t border-gray-800 py-10 px-6">
        <div className="max-w-4xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
              <Brain className="w-4 h-4 text-white" />
            </div>
            <span className="text-sm font-semibold text-gray-400">SCI Research Platform</span>
          </div>
          <p className="text-xs text-gray-700">© 2026 · Powered by Claude AI · 10-Agent LangGraph Pipeline</p>
          <div className="flex gap-5 text-xs text-gray-600">
            <Link href="/dashboard" className="hover:text-gray-400 transition-colors">Dashboard</Link>
            <Link href="/sign-in" className="hover:text-gray-400 transition-colors">Sign In</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
