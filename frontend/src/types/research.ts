export type PipelineStatus =
  | "pending" | "extracting" | "researching" | "data_intelligence" | "authenticating"
  | "plagiarism_check" | "humanizing" | "auditing" | "editor_review"
  | "generating" | "completed" | "failed";

export interface ResearchProject {
  id: string;
  user_id: string;
  title: string;
  domain: string;
  keywords: string[];
  status: PipelineStatus;
  pipeline_iteration: number;
  editor_score: number | null;
  plagiarism_score: number | null;
  ai_detection_score: number | null;
  trust_score: number | null;
  novelty_score: number | null;
  progress_log: ProgressLogEntry[];
  created_at: string;
  updated_at: string;
}

export interface ResearchProjectDetail extends ResearchProject {
  citation_style: string | null;
  abstract: string | null;
  introduction: string | null;
  literature_review: string | null;
  methodology: string | null;
  results: string | null;
  discussion: string | null;
  conclusion: string | null;
  references_data: Reference[];
  figures_data: Figure[];
  tables_data: Table[];
  chart_data: ChartData[];
  table_data: TableData[];
  methodology_visuals: VisualItem[];
  discussion_visuals: VisualItem[];
  editor_feedback: EditorReport | null;
  output_docx_key: string | null;
  output_cover_letter_key: string | null;
  output_reviewer_key: string | null;
  output_report_key: string | null;
  completed_at: string | null;
}

export interface ProgressLogEntry {
  step: string;
  message: string;
  progress_percent: number;
  iteration: number;
  timestamp: string;
}

export interface PipelineProgressEvent extends ProgressLogEntry {}

export interface Reference {
  id?: string;
  doi?: string;
  title: string;
  authors: string[];
  journal?: string;
  year?: number;
  volume?: string;
  issue?: string;
  pages?: string;
  verified: boolean;
  trust_score?: number;
  citation_count?: number;
  formatted?: string;
}

export interface Figure {
  figure_number: number;
  caption: string;
  description?: string;
}

export interface Table {
  table_number: number;
  caption: string;
  columns?: string[];
  description?: string;
}

export interface ChartDataset {
  label: string;
  data: number[];
}

export interface ChartData {
  type: string;
  section?: string;
  title: string;
  x_label?: string;
  y_label?: string;
  x_data?: string[];
  datasets: ChartDataset[];
  caption?: string;
}

export interface TableData {
  title?: string;
  section?: string;
  caption?: string;
  headers: string[];
  rows: (string | number)[][];
  notes?: string;
}

export interface VisualItem {
  kind: "table" | "chart";
  title?: string;
  caption?: string;
  purpose?: string;
  // table fields
  headers?: string[];
  rows?: (string | number)[][];
  notes?: string;
  // chart fields
  type?: string;
  x_label?: string;
  y_label?: string;
  x_data?: string[];
  datasets?: ChartDataset[];
}

export interface EditorReport {
  overall_score: number;
  novelty_score: number;
  methodology_score: number;
  clarity_score: number;
  literature_score: number;
  results_score: number;
  technical_depth_score: number;
  journal_readiness_score: number;
  acceptance_probability: number;
  strengths: string[];
  weaknesses: string[];
  recommendations: string[];
  modules_to_retry: string[];
  pass_threshold: boolean;
  detailed_feedback?: Record<string, string>;
}
