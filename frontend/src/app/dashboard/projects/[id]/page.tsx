"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { useAuth } from "@clerk/nextjs";
import toast from "react-hot-toast";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Download, CheckCircle, AlertCircle, Loader2, ChevronDown, ChevronUp,
  Shield, Brain, FileText, BarChart3, Zap, BookOpen, RefreshCw,
  ExternalLink, Star, AlertTriangle, Info, TrendingUp, Code2, BookMarked,
  Telescope, Award
} from "lucide-react";
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
  LineChart, Line, Legend,
} from "recharts";
import { apiClient } from "@/lib/api";
import { ResearchProjectDetail, EditorReport, Reference } from "@/types/research";

// ─── Pipeline stages ───────────────────────────────────────────────────────

const STAGES = [
  { key: "extracting",        label: "Multi-Modal Extraction",      desc: "Camelot, Tabula, Tesseract, OpenCV, Unstructured.io" },
  { key: "researching",       label: "Literature Research",          desc: "11 sources: S2, CrossRef, arXiv, PubMed, OpenAlex, CORE, EuropePMC, Scite, Scholar, Tavily" },
  { key: "data_intelligence", label: "Data Intelligence",            desc: "AI-generated methodology comparison tables, discussion charts, and statistical visuals" },
  { key: "authenticating",    label: "Reference Authentication",     desc: "DOI resolver, CrossRef, Scite, retraction check, predatory journal filter" },
  { key: "plagiarism_check",  label: "Plagiarism + AI Scan",         desc: "Sentence-transformers similarity + LLM AI detection (7-signal heuristic)" },
  { key: "humanizing",        label: "AI Humanization",              desc: "Iterative Claude rewrite until AI detection < 5%" },
  { key: "auditing",          label: "Figures & Table Audit",        desc: "Citation sequence, DOI validation, TOC generation, BibTeX export" },
  { key: "editor_review",     label: "Editor-in-Chief Review",       desc: "7-dimension scoring — retries until ≥ 9.0/10" },
  { key: "generating",        label: "Document Generation",          desc: "DOCX + Cover Letter + Reviewer Response + Editorial Report" },
];

const ACTIVE_STATUSES = new Set(["extracting","researching","data_intelligence","authenticating","plagiarism_check","humanizing","auditing","editor_review","generating"]);

// ─── Pre-process paper text for clean rendering ───────────────────────────
function preparePaperText(raw: string): string {
  // Convert [1], [1,2], [1-3] citation markers to superscript markdown footnote style
  return raw.replace(/\[(\d+(?:[,\-]\d+)*)\]/g, (_, n) => `^[${n}]^`);
}

// ─── Score colour ─────────────────────────────────────────────────────────

function scoreColour(val: number, max: number, invert = false) {
  const pct = val / max;
  const good = invert ? pct <= 0.15 : pct >= 0.9;
  const warn = invert ? pct <= 0.30 : pct >= 0.7;
  if (good) return "text-emerald-400";
  if (warn) return "text-yellow-400";
  return "text-red-400";
}

// ─── Main page ────────────────────────────────────────────────────────────

export default function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { getToken } = useAuth();
  const queryClient = useQueryClient();
  const [expandedSection, setExpandedSection] = useState<string | null>("abstract");
  const [expandedReport, setExpandedReport] = useState(false);
  const [expandedRefs, setExpandedRefs] = useState(false);
  const [expandedJournals, setExpandedJournals] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  // Journal recommendations
  const { data: journalData } = useQuery({
    queryKey: ["journals", id],
    queryFn: () => apiClient.get<any>(`/api/v1/research/projects/${id}/journal-recommendations`),
    enabled: !!id,
    staleTime: Infinity,
  });

  const { data: project, isLoading } = useQuery({
    queryKey: ["project", id],
    queryFn: () => apiClient.get<ResearchProjectDetail>(`/api/v1/research/projects/${id}`),
    refetchInterval: (query) => {
      const d = query.state.data;
      return d && !ACTIVE_STATUSES.has(d.status) ? false : 4000;
    },
  });

  // ─── WebSocket for real-time progress ──────────────────────────────────
  useEffect(() => {
    let ws: WebSocket;
    let closed = false;

    const connect = async () => {
      const token = await getToken();
      const wsBase = (process.env.NEXT_PUBLIC_API_WS_URL ?? "ws://localhost:8000").replace(/^http/, "ws");
      ws = new WebSocket(`${wsBase}/ws/projects/${id}/progress?token=${token ?? ""}`);
      wsRef.current = ws;

      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data);
          if (msg.type === "complete" || msg.type === "progress") {
            queryClient.invalidateQueries({ queryKey: ["project", id] });
          }
        } catch {}
      };

      ws.onerror = () => {};
      ws.onclose = () => {
        if (!closed) setTimeout(connect, 3000);
      };
    };

    if (project && ACTIVE_STATUSES.has(project.status)) {
      connect();
    }

    return () => {
      closed = true;
      ws?.close();
    };
  }, [id, project?.status, getToken, queryClient]);

  // ─── Download handler ─────────────────────────────────────────────────
  const handleDownload = useCallback(async (type: "docx" | "cover" | "reviewer" | "report") => {
    try {
      const links = await apiClient.get<{
        docx_url?: string; cover_letter_url?: string; reviewer_response_url?: string; report_url?: string;
      }>(`/api/v1/research/projects/${id}/download`);
      const url =
        type === "docx" ? links.docx_url
        : type === "cover" ? links.cover_letter_url
        : type === "reviewer" ? links.reviewer_response_url
        : links.report_url;
      if (url) window.open(url, "_blank");
      else toast.error("File not ready yet");
    } catch (e: any) {
      toast.error(e.message);
    }
  }, [id]);

  const handleDownloadText = useCallback(async (type: "latex" | "bibtex") => {
    try {
      const resp = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1/research/projects/${id}/${type}`,
        { headers: { Authorization: `Bearer ${await (window as any).__clerk?.session?.getToken()}` } }
      );
      if (!resp.ok) { toast.error("File not ready yet"); return; }
      const blob = await resp.blob();
      const ext = type === "latex" ? "tex" : "bib";
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = `paper.${ext}`; a.click();
      URL.revokeObjectURL(url);
    } catch (e: any) {
      toast.error(e.message ?? "Download failed");
    }
  }, [id]);

  if (isLoading || !project) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-blue-400" />
      </div>
    );
  }

  const isComplete = project.status === "completed";
  const isFailed = project.status === "failed";
  const isRunning = ACTIVE_STATUSES.has(project.status);
  const currentStageIdx = STAGES.findIndex((s) => s.key === project.status);
  const editorReport = project.editor_feedback as EditorReport | null;

  return (
    <div className="p-6 text-gray-100 min-h-screen">
      <div className="max-w-5xl mx-auto space-y-6">

        {/* ── Header ── */}
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <h1 className="text-2xl font-bold text-white leading-tight">{project.title}</h1>
            <p className="text-gray-400 text-sm mt-1">
              {project.domain} · {project.pipeline_iteration} iteration{project.pipeline_iteration !== 1 ? "s" : ""} · {project.citation_style?.toUpperCase()}
            </p>
          </div>
          {isComplete && (
            <div className="flex gap-2 flex-shrink-0">
              <button onClick={() => handleDownload("docx")} className="flex items-center gap-1.5 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 rounded-lg text-sm font-medium transition-colors">
                <Download className="w-4 h-4" /> Paper
              </button>
              <button onClick={() => handleDownload("cover")} className="flex items-center gap-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-sm font-medium transition-colors">
                <FileText className="w-4 h-4" /> Cover Letter
              </button>
              <button onClick={() => handleDownload("report")} className="flex items-center gap-1.5 px-3 py-2 border border-gray-700 hover:border-gray-500 rounded-lg text-sm font-medium transition-colors">
                <BarChart3 className="w-4 h-4" /> Report
              </button>
            </div>
          )}
        </div>

        {/* ── Score dashboard ── */}
        {(project.editor_score != null || project.plagiarism_score != null) && (
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
            {[
              { label: "Editor Score", val: project.editor_score, suffix: "/10", max: 10, invert: false },
              { label: "Plagiarism", val: project.plagiarism_score, suffix: "%", max: 100, invert: true },
              { label: "AI Detection", val: project.ai_detection_score, suffix: "%", max: 100, invert: true },
              { label: "Trust Score", val: project.trust_score != null ? project.trust_score * 100 : null, suffix: "%", max: 100, invert: false },
              { label: "Novelty", val: project.novelty_score, suffix: "/10", max: 10, invert: false },
            ].map(({ label, val, suffix, max, invert }) =>
              val != null ? (
                <div key={label} className="glass-card p-4 text-center">
                  <div className={`text-2xl font-bold ${scoreColour(val, max, invert)}`}>
                    {val.toFixed(1)}{suffix}
                  </div>
                  <div className="text-xs text-gray-500 mt-0.5">{label}</div>
                </div>
              ) : null
            )}
          </div>
        )}

        {/* ── Pipeline progress ── */}
        <div className="glass-card p-6">
          <h2 className="font-semibold mb-5 flex items-center gap-2">
            Pipeline Progress
            {isRunning && <Loader2 className="w-4 h-4 animate-spin text-blue-400" />}
            {isComplete && <CheckCircle className="w-4 h-4 text-emerald-400" />}
            {isFailed && <AlertCircle className="w-4 h-4 text-red-400" />}
          </h2>
          <div className="space-y-2">
            {STAGES.map((stage, i) => {
              const isActive = stage.key === project.status;
              const isDone = currentStageIdx > i || isComplete;
              return (
                <div key={stage.key} className={`flex items-start gap-4 p-3 rounded-lg transition-colors ${isActive ? "bg-blue-500/10 border border-blue-500/20" : isDone ? "bg-emerald-500/5" : "opacity-35"}`}>
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 ${isDone ? "bg-emerald-600" : isActive ? "bg-blue-600" : "bg-gray-800"}`}>
                    {isDone ? <CheckCircle className="w-4 h-4 text-white" /> : isActive ? <Loader2 className="w-4 h-4 text-white animate-spin" /> : <div className="w-2 h-2 rounded-full bg-gray-600" />}
                  </div>
                  <div>
                    <p className={`text-sm font-medium ${isActive ? "text-blue-300" : isDone ? "text-emerald-300" : "text-gray-600"}`}>{stage.label}</p>
                    <p className="text-xs text-gray-600 mt-0.5">{stage.desc}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* ── Editor report ── */}
        {editorReport && (
          <div className="glass-card overflow-hidden">
            <button className="w-full flex items-center justify-between p-5 text-left hover:bg-white/2 transition-colors" onClick={() => setExpandedReport(!expandedReport)}>
              <div className="flex items-center gap-3">
                <BarChart3 className="w-5 h-5 text-purple-400" />
                <span className="font-semibold">Editor-in-Chief Report</span>
                <span className={`text-sm font-bold ml-2 ${editorReport.pass_threshold ? "text-emerald-400" : "text-yellow-400"}`}>
                  {editorReport.pass_threshold ? "✅ PASSED" : `Iteration ${project.pipeline_iteration}`}
                </span>
              </div>
              {expandedReport ? <ChevronUp className="w-4 h-4 text-gray-500" /> : <ChevronDown className="w-4 h-4 text-gray-500" />}
            </button>
            <AnimatePresence>
              {expandedReport && (
                <motion.div initial={{ height: 0 }} animate={{ height: "auto" }} exit={{ height: 0 }} className="overflow-hidden">
                  <div className="p-5 pt-0 border-t border-gray-800 space-y-5">
                    {/* Overall score */}
                    <div className="flex items-center gap-3 p-3 bg-gray-900 rounded-lg">
                      <div className={`text-3xl font-bold ${scoreColour(editorReport.overall_score, 10)}`}>
                        {editorReport.overall_score?.toFixed(1)}<span className="text-sm text-gray-500">/10</span>
                      </div>
                      <div>
                        <p className="text-xs font-semibold text-gray-300">Overall Editor Score</p>
                        <p className="text-xs text-gray-500">Acceptance probability: {(editorReport.acceptance_probability * 100).toFixed(0)}%</p>
                      </div>
                    </div>
                    {/* 7-dimension scores */}
                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                      {[
                        { label: "Novelty", val: editorReport.novelty_score, weight: "25%" },
                        { label: "Methodology", val: editorReport.methodology_score, weight: "20%" },
                        { label: "Clarity", val: editorReport.clarity_score, weight: "15%" },
                        { label: "Literature", val: editorReport.literature_score, weight: "15%" },
                        { label: "Results", val: editorReport.results_score, weight: "10%" },
                        { label: "Technical Depth", val: editorReport.technical_depth_score, weight: "10%" },
                        { label: "Journal Readiness", val: editorReport.journal_readiness_score, weight: "5%" },
                      ].map(({ label, val, weight }) => (
                        <div key={label} className="bg-gray-900 rounded-lg p-3 text-center">
                          <div className={`text-xl font-bold ${scoreColour(val ?? 0, 10)}`}>{(val ?? 0).toFixed(1)}</div>
                          <div className="text-xs text-gray-400 mt-0.5">{label}</div>
                          <div className="text-xs text-gray-600">weight {weight}</div>
                        </div>
                      ))}
                    </div>
                    {/* Strengths / Weaknesses / Recommendations */}
                    {[
                      { key: "strengths", label: "Strengths", icon: CheckCircle, color: "text-emerald-400" },
                      { key: "weaknesses", label: "Weaknesses", icon: AlertTriangle, color: "text-yellow-400" },
                      { key: "recommendations", label: "Recommendations", icon: TrendingUp, color: "text-blue-400" },
                    ].map(({ key, label, icon: Icon, color }) => {
                      const items = (editorReport as any)[key] as string[];
                      if (!items?.length) return null;
                      return (
                        <div key={key}>
                          <h4 className={`text-sm font-semibold mb-2 flex items-center gap-1.5 ${color}`}><Icon className="w-4 h-4" />{label}</h4>
                          <ul className="space-y-1">
                            {items.map((item, i) => <li key={i} className="text-sm text-gray-300 flex gap-2"><span className="text-gray-600 flex-shrink-0">•</span>{item}</li>)}
                          </ul>
                        </div>
                      );
                    })}
                    {/* ── Radar chart ── */}
                    <div>
                      <h4 className="text-sm font-semibold mb-3 text-gray-300 flex items-center gap-1.5">
                        <BarChart3 className="w-4 h-4 text-purple-400" /> Quality Dimensions
                      </h4>
                      <ResponsiveContainer width="100%" height={280}>
                        <RadarChart data={[
                          { dim: "Novelty",      val: editorReport.novelty_score ?? 0 },
                          { dim: "Methodology",  val: editorReport.methodology_score ?? 0 },
                          { dim: "Clarity",      val: editorReport.clarity_score ?? 0 },
                          { dim: "Literature",   val: editorReport.literature_score ?? 0 },
                          { dim: "Results",      val: editorReport.results_score ?? 0 },
                          { dim: "Tech Depth",   val: editorReport.technical_depth_score ?? 0 },
                          { dim: "Readiness",    val: editorReport.journal_readiness_score ?? 0 },
                        ]}>
                          <PolarGrid stroke="#374151" />
                          <PolarAngleAxis dataKey="dim" tick={{ fill: "#9CA3AF", fontSize: 11 }} />
                          <PolarRadiusAxis angle={90} domain={[0, 10]} tick={{ fill: "#6B7280", fontSize: 9 }} tickCount={6} />
                          <Radar name="Score" dataKey="val" stroke="#818CF8" fill="#818CF8" fillOpacity={0.25} strokeWidth={2} />
                        </RadarChart>
                      </ResponsiveContainer>
                    </div>

                    {/* Section feedback */}
                    {editorReport.detailed_feedback && Object.keys(editorReport.detailed_feedback).length > 0 && (
                      <div>
                        <h4 className="text-sm font-semibold mb-3 text-gray-300">Section Feedback</h4>
                        <div className="space-y-2">
                          {Object.entries(editorReport.detailed_feedback).map(([sec, fb]) => (
                            fb ? (
                              <div key={sec} className="bg-gray-900 rounded-lg p-3">
                                <p className="text-xs font-semibold text-gray-400 mb-1 uppercase">{sec.replace("_", " ")}</p>
                                <p className="text-sm text-gray-300">{fb as string}</p>
                              </div>
                            ) : null
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        )}

        {/* ── Journal Recommendations ── */}
        {journalData && (
          <div className="glass-card overflow-hidden">
            <button
              className="w-full flex items-center justify-between p-5 text-left hover:bg-white/2 transition-colors"
              onClick={() => setExpandedJournals(!expandedJournals)}
            >
              <div className="flex items-center gap-3">
                <Telescope className="w-5 h-5 text-yellow-400" />
                <span className="font-semibold">Journal Recommendations</span>
                <span className="text-xs text-gray-500">— where to submit</span>
              </div>
              {expandedJournals ? <ChevronUp className="w-4 h-4 text-gray-500" /> : <ChevronDown className="w-4 h-4 text-gray-500" />}
            </button>
            <AnimatePresence>
              {expandedJournals && (
                <motion.div initial={{ height: 0 }} animate={{ height: "auto" }} exit={{ height: 0 }} className="overflow-hidden">
                  <div className="p-5 pt-0 border-t border-gray-800 space-y-4">
                    <p className="text-xs text-gray-400 leading-relaxed pt-2">{journalData.advice}</p>
                    <div className="space-y-2">
                      {(journalData.recommendations as any[]).map((j: any, i: number) => (
                        <div key={i} className="flex items-center justify-between gap-4 p-3 bg-gray-900 rounded-lg hover:bg-gray-800 transition-colors">
                          <div className="flex items-start gap-3 flex-1 min-w-0">
                            <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 mt-0.5 ${i === 0 ? "bg-yellow-500 text-black" : i === 1 ? "bg-gray-400 text-black" : "bg-orange-700 text-white"}`}>
                              {i + 1}
                            </div>
                            <div className="min-w-0">
                              <p className="text-sm font-medium text-gray-100 truncate">{j.name}</p>
                              <p className="text-xs text-gray-500">{j.publisher} · ISSN {j.issn}</p>
                            </div>
                          </div>
                          <div className="flex items-center gap-3 flex-shrink-0">
                            <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${j.quartile === "Q1" ? "bg-emerald-500/20 text-emerald-300" : "bg-yellow-500/20 text-yellow-300"}`}>
                              {j.quartile}
                            </span>
                            <div className="text-right">
                              <p className="text-sm font-bold text-blue-300">{j.impact_factor}</p>
                              <p className="text-xs text-gray-600">IF</p>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        )}

        {/* ── Paper preview ── */}
        {/* ── Keywords ── */}
        {isComplete && (project as any).keywords?.length > 0 && (
          <div className="glass-card p-5">
            <h2 className="font-semibold text-sm mb-3 flex items-center gap-2 text-gray-300">
              <BookOpen className="w-4 h-4 text-cyan-400" /> Keywords
            </h2>
            <div className="flex flex-wrap gap-2">
              {((project as any).keywords as string[]).map((kw: string, i: number) => (
                <span key={i} className="px-3 py-1 bg-cyan-500/10 border border-cyan-500/20 rounded-full text-xs text-cyan-300 font-medium">
                  {kw}
                </span>
              ))}
            </div>
          </div>
        )}

        {isComplete && (
          <div className="glass-card overflow-hidden">
            <div className="p-5 border-b border-gray-800">
              <h2 className="font-semibold flex items-center gap-2"><FileText className="w-5 h-5 text-blue-400" /> Generated Paper Preview</h2>
              <p className="text-xs text-gray-500 mt-1">Complete Top-1% structure · Full paper in downloaded .docx with embedded charts</p>
            </div>
            <div className="divide-y divide-gray-800">
              {[
                { key: "abstract", label: "Abstract" },
                { key: "introduction", label: "I. Introduction" },
                { key: "literature_review", label: "II. Literature Review" },
                { key: "methodology", label: "III. Materials & Methods" },
                { key: "results", label: "IV. Results" },
                { key: "discussion", label: "V. Discussion" },
                { key: "conclusion", label: "VI. Conclusion" },
              ].map(({ key, label }) => {
                const text = (project as any)[key] as string | null;
                if (!text) return null;
                const isExp = expandedSection === key;
                const wordCount = text.split(/\s+/).length;
                return (
                  <div key={key}>
                    <button className="w-full flex items-center justify-between px-5 py-3.5 text-left hover:bg-white/2 transition-colors" onClick={() => setExpandedSection(isExp ? null : key)}>
                      <span className="font-medium text-sm text-gray-200">{label}</span>
                      <div className="flex items-center gap-3">
                        <span className="text-xs text-gray-500">{wordCount.toLocaleString()} words</span>
                        {isExp ? <ChevronUp className="w-4 h-4 text-gray-500" /> : <ChevronDown className="w-4 h-4 text-gray-500" />}
                      </div>
                    </button>
                    <AnimatePresence>
                      {isExp && (
                        <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden border-t border-gray-800">
                          <div className="px-6 py-5 max-h-[700px] overflow-y-auto">
                            <ReactMarkdown
                              remarkPlugins={[remarkGfm]}
                              components={{
                                sup: ({ children }) => <sup className="text-blue-400 text-[10px] font-medium">{children}</sup>,
                                h1: ({ children }) => <h1 className="text-lg font-bold text-white mt-5 mb-2 border-b border-gray-700 pb-1">{children}</h1>,
                                h2: ({ children }) => <h2 className="text-base font-bold text-gray-100 mt-4 mb-2">{children}</h2>,
                                h3: ({ children }) => <h3 className="text-sm font-semibold text-gray-200 mt-3 mb-1.5 uppercase tracking-wide">{children}</h3>,
                                p: ({ children }) => <p className="text-sm text-gray-300 leading-7 mb-3 font-serif text-justify">{children}</p>,
                                strong: ({ children }) => <strong className="font-semibold text-gray-100">{children}</strong>,
                                em: ({ children }) => <em className="italic text-gray-200">{children}</em>,
                                ul: ({ children }) => <ul className="list-disc list-outside pl-5 mb-3 space-y-1">{children}</ul>,
                                ol: ({ children }) => <ol className="list-decimal list-outside pl-5 mb-3 space-y-1">{children}</ol>,
                                li: ({ children }) => <li className="text-sm text-gray-300 leading-6">{children}</li>,
                                blockquote: ({ children }) => <blockquote className="border-l-2 border-blue-500 pl-4 my-3 text-gray-400 italic">{children}</blockquote>,
                                code: ({ children }) => <code className="bg-gray-800 text-cyan-300 px-1.5 py-0.5 rounded text-xs font-mono">{children}</code>,
                                table: ({ children }) => <div className="overflow-x-auto my-4"><table className="w-full text-xs border-collapse">{children}</table></div>,
                                th: ({ children }) => <th className="border border-gray-700 bg-gray-800 px-3 py-1.5 text-left text-gray-200 font-semibold">{children}</th>,
                                td: ({ children }) => <td className="border border-gray-800 px-3 py-1.5 text-gray-400">{children}</td>,
                                a: ({ href, children }) => <a href={href} className="text-blue-400 hover:underline" target="_blank" rel="noreferrer">{children}</a>,
                              }}
                            >
                              {preparePaperText(text)}
                            </ReactMarkdown>
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* ── References ── */}
        {isComplete && project.references_data && project.references_data.length > 0 && (
          <div className="glass-card overflow-hidden">
            <button className="w-full flex items-center justify-between p-5 text-left hover:bg-white/2 transition-colors" onClick={() => setExpandedRefs(!expandedRefs)}>
              <div className="flex items-center gap-2">
                <BookOpen className="w-5 h-5 text-cyan-400" />
                <span className="font-semibold">References ({project.references_data.length})</span>
                <span className="text-xs text-gray-500">
                  — {project.references_data.filter((r: Reference) => r.verified).length} verified
                </span>
              </div>
              {expandedRefs ? <ChevronUp className="w-4 h-4 text-gray-500" /> : <ChevronDown className="w-4 h-4 text-gray-500" />}
            </button>
            <AnimatePresence>
              {expandedRefs && (
                <motion.div initial={{ height: 0 }} animate={{ height: "auto" }} exit={{ height: 0 }} className="overflow-hidden border-t border-gray-800">
                  <div className="divide-y divide-gray-900 max-h-[500px] overflow-y-auto">
                    {project.references_data.map((ref: Reference, i: number) => (
                      <div key={i} className="px-5 py-3 flex items-start gap-3">
                        <span className="text-xs text-gray-600 flex-shrink-0 mt-0.5 w-6">[{i + 1}]</span>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm text-gray-200 leading-relaxed">{ref.title}</p>
                          <p className="text-xs text-gray-500 mt-0.5">
                            {[...ref.authors].slice(0, 3).join(", ")}{ref.authors.length > 3 ? " et al." : ""} · {ref.year} · {ref.journal}
                          </p>
                        </div>
                        <div className="flex items-center gap-2 flex-shrink-0">
                          {ref.verified && <CheckCircle className="w-3.5 h-3.5 text-emerald-400" aria-label="Verified" />}
                          {ref.doi && (
                            <a href={`https://doi.org/${ref.doi}`} target="_blank" rel="noreferrer" className="text-blue-400 hover:text-blue-300">
                              <ExternalLink className="w-3.5 h-3.5" />
                            </a>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        )}

        {/* ── Chart Figures ── */}
        {isComplete && (project as any).chart_data?.length > 0 && (
          <div className="glass-card overflow-hidden">
            <div className="p-5 border-b border-gray-800">
              <h2 className="font-semibold flex items-center gap-2">
                <BarChart3 className="w-5 h-5 text-purple-400" />
                Generated Figures ({(project as any).chart_data?.length})
                <span className="text-xs text-gray-500 font-normal">Embedded in downloaded .docx</span>
              </h2>
            </div>
            <div className="p-5 grid grid-cols-1 md:grid-cols-2 gap-6">
              {((project as any).chart_data as any[]).map((ch: any, i: number) => {
                const COLORS = ["#818CF8","#34D399","#F59E0B","#F87171","#38BDF8","#A78BFA"];
                const xKeys = ch.x_data ?? [];
                const chartRows = xKeys.map((x: string, xi: number) => {
                  const row: any = { x };
                  (ch.datasets ?? []).forEach((ds: any) => { row[ds.label ?? `s${xi}`] = ds.data?.[xi] ?? 0; });
                  return row;
                });
                const dsKeys = (ch.datasets ?? []).map((ds: any) => ds.label ?? "Value");
                return (
                  <div key={i} className="bg-gray-900 rounded-xl p-4 border border-gray-800">
                    <p className="text-xs font-bold text-purple-300 uppercase tracking-wide mb-0.5">
                      Figure {i + 1} · {ch.type}
                    </p>
                    <p className="text-sm font-semibold text-gray-100 mb-1">{ch.title}</p>
                    {ch.caption && <p className="text-xs text-gray-500 mb-3 leading-relaxed">{ch.caption}</p>}
                    {chartRows.length > 0 && (
                      <ResponsiveContainer width="100%" height={200}>
                        {ch.type === "line" ? (
                          <LineChart data={chartRows}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#1F2937" />
                            <XAxis dataKey="x" tick={{ fill: "#6B7280", fontSize: 10 }} />
                            <YAxis tick={{ fill: "#6B7280", fontSize: 10 }} label={ch.y_label ? { value: ch.y_label, angle: -90, position: "insideLeft", fill: "#6B7280", fontSize: 10 } : undefined} />
                            <Tooltip contentStyle={{ background: "#111827", border: "1px solid #374151", borderRadius: 8, fontSize: 11 }} />
                            <Legend wrapperStyle={{ fontSize: 11 }} />
                            {dsKeys.map((k: string, ki: number) => (
                              <Line key={k} type="monotone" dataKey={k} stroke={COLORS[ki % COLORS.length]} strokeWidth={2} dot={false} />
                            ))}
                          </LineChart>
                        ) : (
                          <BarChart data={chartRows}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#1F2937" />
                            <XAxis dataKey="x" tick={{ fill: "#6B7280", fontSize: 10 }} />
                            <YAxis tick={{ fill: "#6B7280", fontSize: 10 }} />
                            <Tooltip contentStyle={{ background: "#111827", border: "1px solid #374151", borderRadius: 8, fontSize: 11 }} />
                            <Legend wrapperStyle={{ fontSize: 11 }} />
                            {dsKeys.map((k: string, ki: number) => (
                              <Bar key={k} dataKey={k} fill={COLORS[ki % COLORS.length]} radius={[3, 3, 0, 0]} />
                            ))}
                          </BarChart>
                        )}
                      </ResponsiveContainer>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* ── Tables ── */}
        {isComplete && (project as any).table_data?.length > 0 && (
          <div className="glass-card overflow-hidden">
            <div className="p-5 border-b border-gray-800">
              <h2 className="font-semibold flex items-center gap-2">
                <Info className="w-5 h-5 text-yellow-400" />
                Generated Tables ({(project as any).table_data?.length})
              </h2>
            </div>
            <div className="p-5 space-y-5">
              {((project as any).table_data as any[]).map((tbl: any, i: number) => (
                <div key={i}>
                  <p className="text-sm font-semibold text-gray-200 mb-1">{tbl.title || `Table ${i + 1}`}</p>
                  {tbl.caption && <p className="text-xs text-gray-500 mb-2">{tbl.caption}</p>}
                  {tbl.headers?.length > 0 && (
                    <div className="overflow-x-auto">
                      <table className="w-full text-xs border-collapse">
                        <thead>
                          <tr className="bg-gray-800">
                            {(tbl.headers as string[]).map((h: string, j: number) => (
                              <th key={j} className="px-3 py-2 text-left text-gray-300 font-semibold border border-gray-700">{h}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {(tbl.rows as any[][]).slice(0, 8).map((row: any[], ri: number) => (
                            <tr key={ri} className={ri % 2 === 0 ? "bg-gray-900" : "bg-gray-950"}>
                              {row.map((cell: any, ci: number) => (
                                <td key={ci} className="px-3 py-1.5 text-gray-400 border border-gray-800">{cell}</td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      {tbl.rows?.length > 8 && (
                        <p className="text-xs text-gray-600 mt-1">{tbl.rows.length - 8} more rows in downloaded .docx</p>
                      )}
                    </div>
                  )}
                  {tbl.notes && <p className="text-xs text-gray-600 mt-1 italic">Note: {tbl.notes}</p>}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── Author Contributions / Funding / COI ── */}
        {isComplete && ((project as any).author_contributions || (project as any).funding_disclosure || (project as any).conflicts_of_interest) && (
          <div className="glass-card p-5 space-y-4">
            <h2 className="font-semibold text-sm text-gray-300 flex items-center gap-2">
              <Star className="w-4 h-4 text-yellow-400" /> Paper Metadata
            </h2>
            {(project as any).author_contributions && (
              <div>
                <p className="text-xs font-semibold text-gray-400 mb-1">Author Contributions (CRediT)</p>
                <p className="text-xs text-gray-300 leading-relaxed">{(project as any).author_contributions}</p>
              </div>
            )}
            {(project as any).funding_disclosure && (
              <div>
                <p className="text-xs font-semibold text-gray-400 mb-1">Funding</p>
                <p className="text-xs text-gray-300">{(project as any).funding_disclosure}</p>
              </div>
            )}
            {(project as any).conflicts_of_interest && (
              <div>
                <p className="text-xs font-semibold text-gray-400 mb-1">Declaration of Competing Interest</p>
                <p className="text-xs text-gray-300">{(project as any).conflicts_of_interest}</p>
              </div>
            )}
          </div>
        )}

        {/* ── Download all files ── */}
        {isComplete && (
          <div className="glass-card p-5">
            <h2 className="font-semibold text-sm text-gray-300 mb-1 flex items-center gap-2">
              <Download className="w-4 h-4 text-blue-400" /> Download All Files
            </h2>
            <p className="text-xs text-gray-600 mb-4">Submit-ready formats for every major journal workflow</p>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-3">
              <button onClick={() => handleDownload("docx")}
                className="flex flex-col items-center gap-2 p-4 bg-emerald-600/10 hover:bg-emerald-600/20 border border-emerald-600/30 rounded-xl transition-colors">
                <FileText className="w-6 h-6 text-emerald-400" />
                <span className="text-xs font-semibold text-emerald-300">Full Paper</span>
                <span className="text-xs text-gray-600">.docx · charts embedded</span>
              </button>
              <button onClick={() => handleDownload("cover")}
                className="flex flex-col items-center gap-2 p-4 bg-blue-600/10 hover:bg-blue-600/20 border border-blue-600/30 rounded-xl transition-colors">
                <FileText className="w-6 h-6 text-blue-400" />
                <span className="text-xs font-semibold text-blue-300">Cover Letter</span>
                <span className="text-xs text-gray-600">.docx</span>
              </button>
              <button onClick={() => handleDownload("reviewer")}
                className="flex flex-col items-center gap-2 p-4 bg-purple-600/10 hover:bg-purple-600/20 border border-purple-600/30 rounded-xl transition-colors">
                <Shield className="w-6 h-6 text-purple-400" />
                <span className="text-xs font-semibold text-purple-300">Reviewer Response</span>
                <span className="text-xs text-gray-600">.docx</span>
              </button>
              <button onClick={() => handleDownload("report")}
                className="flex flex-col items-center gap-2 p-4 bg-gray-600/10 hover:bg-gray-600/20 border border-gray-600/30 rounded-xl transition-colors">
                <BarChart3 className="w-6 h-6 text-gray-400" />
                <span className="text-xs font-semibold text-gray-300">Editorial Report</span>
                <span className="text-xs text-gray-600">.docx</span>
              </button>
              {/* LaTeX export — critical for top-journal submission */}
              <button onClick={() => handleDownloadText("latex")}
                className="flex flex-col items-center gap-2 p-4 bg-orange-600/10 hover:bg-orange-600/20 border border-orange-600/30 rounded-xl transition-colors">
                <Code2 className="w-6 h-6 text-orange-400" />
                <span className="text-xs font-semibold text-orange-300">LaTeX Source</span>
                <span className="text-xs text-gray-600">.tex · Nature / IEEE</span>
              </button>
              {/* BibTeX for Zotero / Mendeley */}
              <button onClick={() => handleDownloadText("bibtex")}
                className="flex flex-col items-center gap-2 p-4 bg-cyan-600/10 hover:bg-cyan-600/20 border border-cyan-600/30 rounded-xl transition-colors">
                <BookMarked className="w-6 h-6 text-cyan-400" />
                <span className="text-xs font-semibold text-cyan-300">BibTeX</span>
                <span className="text-xs text-gray-600">.bib · Zotero / Mendeley</span>
              </button>
            </div>
            <p className="text-xs text-gray-700 text-center">LaTeX compatible with Overleaf — paste .tex and .bib directly</p>
          </div>
        )}

        {/* ── Failed state ── */}
        {isFailed && (
          <div className="glass-card p-6 border border-red-800">
            <div className="flex items-center gap-3 mb-3">
              <AlertCircle className="w-6 h-6 text-red-400" />
              <h2 className="font-semibold text-red-300">Pipeline Failed</h2>
            </div>
            <p className="text-gray-400 text-sm mb-4">The pipeline encountered an error. You can restart it from the beginning.</p>
            <button
              onClick={async () => {
                try {
                  await apiClient.post(`/api/v1/research/projects/${id}/start`, {});
                  queryClient.invalidateQueries({ queryKey: ["project", id] });
                  toast.success("Pipeline restarted");
                } catch (e: any) { toast.error(e.message); }
              }}
              className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-500 rounded-lg text-sm font-medium transition-colors"
            >
              <RefreshCw className="w-4 h-4" /> Restart Pipeline
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
