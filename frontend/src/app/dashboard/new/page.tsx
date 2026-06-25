"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useForm, Controller, useFieldArray } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useDropzone } from "react-dropzone";
import { motion, AnimatePresence } from "framer-motion";
import { useMutation } from "@tanstack/react-query";
import toast from "react-hot-toast";
import {
  Upload, X, FileText, ChevronRight, ChevronLeft, Loader2,
  Plus, Trash2, FlaskConical, Users, BookOpen, Settings2,
  Brain, Microscope, CheckCircle2, AlertCircle,
} from "lucide-react";
import { apiClient } from "@/lib/api";

// ─── Schema ──────────────────────────────────────────────────────────────────

const authorSchema = z.object({
  name: z.string().min(2, "Required"),
  affiliation: z.string().min(2, "Required"),
  contribution: z.string().optional(),
});

const schema = z.object({
  // Step 1 — Research Identity
  title: z.string().min(10, "Minimum 10 characters").max(500),
  domain: z.string().min(3, "Required"),
  study_type: z.enum(["experimental","review","survey","meta_analysis","theoretical","clinical_trial","computational","mixed"]),
  keywords: z.string().min(5, "Enter at least 6 keywords (comma-separated)"),

  // Step 2 — Research Problem
  problem_statement: z.string().min(80, "Minimum 80 characters — be specific"),
  research_gap: z.string().min(50, "Describe the gap in existing literature"),
  hypothesis: z.string().min(30, "State your hypothesis or research question"),
  novel_contribution: z.string().min(50, "What makes this work unique?"),
  objectives: z.string().min(50, "List 3-5 specific research objectives"),
  scope: z.string().optional(),

  // Step 3 — Authors & Ethics
  author_name: z.string().min(2, "Lead author name required"),
  author_affiliation: z.string().min(3, "Institution required"),
  all_authors: z.array(authorSchema).optional(),
  funding_source: z.string().optional(),
  conflicts_of_interest_input: z.string().optional(),
  ethics_statement_input: z.string().optional(),

  // Step 4 — Methodology
  methodology_description: z.string().min(80, "Describe your research design and methodology"),
  dataset_description: z.string().min(30, "Describe your dataset or study subjects"),
  analysis_methods: z.string().min(30, "List statistical/analytical methods"),
  tools_used: z.string().optional(),
  expected_findings: z.string().min(30, "List your expected key findings"),
  research_significance: z.string().min(30, "Why does this research matter?"),

  // Step 5 — Paper Settings
  journal_type: z.enum(["sci","scopus","web_of_science","ieee","nature","elsevier","springer","plos","mdpi","frontiers"]),
  citation_style: z.enum(["ieee","apa","mla","chicago","harvard","vancouver","nature","acs"]),
  preferred_word_count: z.number().min(3000).max(20000),
  writing_tone: z.enum(["academic","technical","review","clinical","engineering"]),
  additional_instructions: z.string().max(2000).optional(),
});

type FormData = z.infer<typeof schema>;

// ─── Step metadata ────────────────────────────────────────────────────────────

const STEPS = [
  { label: "Research Identity",  icon: Brain,         color: "blue" },
  { label: "Research Problem",   icon: FlaskConical,  color: "purple" },
  { label: "Authors & Ethics",   icon: Users,         color: "green" },
  { label: "Methodology & Data", icon: Microscope,    color: "orange" },
  { label: "Paper Settings",     icon: Settings2,     color: "cyan" },
  { label: "Upload & Launch",    icon: Upload,        color: "emerald" },
];

const DOMAINS = [
  "Artificial Intelligence & Machine Learning","Computer Science","Electrical Engineering",
  "Biomedical Engineering","Medicine & Clinical Research","Biology & Life Sciences",
  "Chemistry & Chemical Engineering","Physics","Materials Science","Environmental Science",
  "Mathematics & Statistics","Psychology & Neuroscience","Economics & Finance",
  "Management & Business","Education","Civil & Structural Engineering",
  "Mechanical Engineering","Aerospace Engineering","Nanotechnology",
  "Agriculture & Food Science","Public Health & Epidemiology","Pharmacology",
];

const STUDY_TYPES = [
  { value: "experimental",    label: "Experimental Study",        desc: "Lab/field experiments with controlled variables" },
  { value: "review",          label: "Literature Review",         desc: "Systematic or narrative review of existing work" },
  { value: "survey",          label: "Survey / Observational",    desc: "Questionnaires, cohort, case-control studies" },
  { value: "meta_analysis",   label: "Meta-Analysis",             desc: "Statistical synthesis of multiple studies" },
  { value: "theoretical",     label: "Theoretical / Modelling",   desc: "Mathematical models, proofs, simulations" },
  { value: "clinical_trial",  label: "Clinical Trial",            desc: "Randomised controlled trials, drug/device trials" },
  { value: "computational",   label: "Computational / Simulation","desc": "Simulation, ML experiments, algorithm benchmarks" },
  { value: "mixed",           label: "Mixed Methods",             desc: "Combination of quantitative and qualitative" },
];

// ─── Helper components ────────────────────────────────────────────────────────

function Field({ label, hint, error, children, required }: {
  label: string; hint?: string; error?: string; children: React.ReactNode; required?: boolean;
}) {
  return (
    <div className="space-y-1.5">
      <label className="flex items-center gap-1 text-sm font-medium text-gray-200">
        {label}
        {required && <span className="text-red-400 text-xs">*</span>}
      </label>
      {hint && <p className="text-xs text-gray-500 -mt-0.5">{hint}</p>}
      {children}
      {error && (
        <p className="flex items-center gap-1 text-xs text-red-400 mt-0.5">
          <AlertCircle className="w-3 h-3" />{error}
        </p>
      )}
    </div>
  );
}

const inputCls = "w-full bg-gray-900/80 border border-gray-700 rounded-lg px-4 py-2.5 text-sm text-gray-100 placeholder:text-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500 transition-all";
const textareaCls = `${inputCls} resize-none leading-relaxed`;

// ─── Main page ────────────────────────────────────────────────────────────────

export default function NewProjectPage() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);

  const {
    register, control, handleSubmit,
    formState: { errors }, trigger, watch,
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      journal_type: "sci",
      citation_style: "ieee",
      preferred_word_count: 8000,
      writing_tone: "academic",
      study_type: "experimental",
      all_authors: [],
    },
  });

  const { fields: authorFields, append: appendAuthor, remove: removeAuthor } = useFieldArray({
    control,
    name: "all_authors",
  });

  const createProject = useMutation({
    mutationFn: async (data: FormData) => {
      const payload = {
        ...data,
        keywords: data.keywords.split(",").map((k) => k.trim()).filter(Boolean),
      };
      return apiClient.post<{ id: string }>("/api/v1/research/projects", payload);
    },
    onError: () => toast.error("Failed to create project"),
  });

  const uploadFiles = useMutation({
    mutationFn: async (projectId: string) => {
      if (!uploadedFiles.length) return;
      const formData = new FormData();
      uploadedFiles.forEach((f) => formData.append("files", f));
      return apiClient.postForm(`/api/v1/research/projects/${projectId}/files`, formData);
    },
  });

  const startPipeline = useMutation({
    mutationFn: async (projectId: string) =>
      apiClient.post(`/api/v1/research/projects/${projectId}/start`, {}),
    onSuccess: (_, projectId) => {
      toast.success("Pipeline launched!");
      router.push(`/dashboard/projects/${projectId}`);
    },
    onError: () => toast.error("Failed to start pipeline"),
  });

  const onDrop = useCallback((accepted: File[]) => {
    setUploadedFiles((prev) => [...prev, ...accepted].slice(0, 20));
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
      "application/msword": [".doc"],
      "application/vnd.openxmlformats-officedocument.presentationml.presentation": [".pptx"],
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
      "text/csv": [".csv"],
      "image/*": [".png", ".jpg", ".jpeg", ".tiff", ".bmp"],
    },
    maxSize: 50 * 1024 * 1024,
  });

  const STEP_FIELDS: Record<number, (keyof FormData)[]> = {
    0: ["title", "domain", "study_type", "keywords"],
    1: ["problem_statement", "research_gap", "hypothesis", "novel_contribution", "objectives"],
    2: ["author_name", "author_affiliation"],
    3: ["methodology_description", "dataset_description", "analysis_methods", "expected_findings", "research_significance"],
    4: ["journal_type", "citation_style", "preferred_word_count", "writing_tone"],
  };

  const nextStep = async () => {
    if (STEP_FIELDS[step]) {
      const valid = await trigger(STEP_FIELDS[step] as any);
      if (!valid) return;
    }
    setStep((s) => s + 1);
  };

  const onSubmit = async (data: FormData) => {
    const project = await createProject.mutateAsync(data);
    await uploadFiles.mutateAsync(project.id);
    await startPipeline.mutateAsync(project.id);
  };

  const isSubmitting = createProject.isPending || uploadFiles.isPending || startPipeline.isPending;
  const watchedStudyType = watch("study_type");

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 pb-16">
      {/* Header */}
      <div className="border-b border-gray-800 bg-gray-950/80 backdrop-blur sticky top-0 z-10">
        <div className="max-w-3xl mx-auto px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-white">New Research Project</h1>
            <p className="text-xs text-gray-500 mt-0.5">Top-1% SCI paper generation · {STEPS[step].label}</p>
          </div>
          <div className="text-sm font-medium text-gray-400">
            Step {step + 1} of {STEPS.length}
          </div>
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-6 pt-8">
        {/* Step indicator */}
        <div className="flex items-center gap-0 mb-10 overflow-x-auto pb-2">
          {STEPS.map(({ label, icon: Icon }, i) => (
            <div key={label} className="flex items-center flex-shrink-0">
              <button
                type="button"
                onClick={() => i < step && setStep(i)}
                className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-all ${
                  i === step ? "bg-blue-600/20 text-blue-400" :
                  i < step ? "text-emerald-400 cursor-pointer hover:bg-emerald-400/5" :
                  "text-gray-600 cursor-default"
                }`}
              >
                <div className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 border-2 text-xs font-bold transition-colors ${
                  i < step ? "bg-emerald-600 border-emerald-600 text-white" :
                  i === step ? "border-blue-400 text-blue-400" :
                  "border-gray-700 text-gray-600"
                }`}>
                  {i < step ? <CheckCircle2 className="w-4 h-4" /> : <Icon className="w-3.5 h-3.5" />}
                </div>
                <span className="text-xs font-medium hidden sm:block">{label}</span>
              </button>
              {i < STEPS.length - 1 && (
                <div className={`w-6 h-0.5 mx-1 flex-shrink-0 ${i < step ? "bg-emerald-600" : "bg-gray-800"}`} />
              )}
            </div>
          ))}
        </div>

        <form onSubmit={handleSubmit(onSubmit)}>
          <AnimatePresence mode="wait">

            {/* ── Step 1: Research Identity ─────────────────────────────── */}
            {step === 0 && (
              <motion.div key="s0" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -16 }} className="space-y-6">
                <StepHeader icon={Brain} title="Research Identity" desc="Define what your paper is about and what kind of study it is." />

                <Field label="Paper Title" required hint="Be specific and descriptive — include your key variables or method" error={errors.title?.message}>
                  <input {...register("title")} placeholder="e.g., Transformer-Based Deep Learning for Early Detection of Diabetic Retinopathy: A Multi-Centre Validation Study" className={inputCls} />
                </Field>

                <div className="grid grid-cols-2 gap-4">
                  <Field label="Research Domain" required error={errors.domain?.message}>
                    <select {...register("domain")} className={inputCls}>
                      <option value="">Select domain...</option>
                      {DOMAINS.map((d) => <option key={d} value={d}>{d}</option>)}
                    </select>
                  </Field>
                  <Field label="Study Type" required hint="Choose the primary study design" error={errors.study_type?.message}>
                    <select {...register("study_type")} className={inputCls}>
                      {STUDY_TYPES.map((t) => (
                        <option key={t.value} value={t.value}>{t.label}</option>
                      ))}
                    </select>
                  </Field>
                </div>

                {watchedStudyType && (
                  <div className="text-xs text-blue-300 bg-blue-500/10 rounded-lg px-3 py-2 border border-blue-500/20">
                    {STUDY_TYPES.find(t => t.value === watchedStudyType)?.desc}
                  </div>
                )}

                <Field label="Keywords" required hint="6-8 specific, searchable terms. Use MeSH or IEEE Thesaurus terms where possible." error={errors.keywords?.message}>
                  <input {...register("keywords")} placeholder="deep learning, transformer, diabetic retinopathy, medical imaging, fundus photography, early detection, CNN, clinical validation" className={inputCls} />
                  <p className="text-xs text-gray-600 mt-1">Separate with commas · More specific = better indexing</p>
                </Field>
              </motion.div>
            )}

            {/* ── Step 2: Research Problem ──────────────────────────────── */}
            {step === 1 && (
              <motion.div key="s1" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -16 }} className="space-y-5">
                <StepHeader icon={FlaskConical} title="Research Problem" desc="Define the scientific problem, gap, and your contribution. This drives the entire paper." />

                <Field label="Problem Statement" required hint="What problem does this research address? Why does it exist?" error={errors.problem_statement?.message}>
                  <textarea {...register("problem_statement")} rows={4} placeholder="Diabetic retinopathy affects 103 million people globally yet is diagnosed late due to limited access to ophthalmologists. Current AI screening tools have inadequate sensitivity (72-81%) for early-stage detection and lack validation across diverse ethnic groups, leading to preventable blindness in low-resource settings." className={textareaCls} />
                </Field>

                <Field label="Research Gap" required hint="What is MISSING in current literature that your work fills?" error={errors.research_gap?.message}>
                  <textarea {...register("research_gap")} rows={3} placeholder="While several CNN-based approaches exist, no study has: (1) validated performance across Asian, African, and Caucasian cohorts simultaneously, (2) achieved >95% sensitivity at early grade 1-2 detection, or (3) demonstrated real-world deployment feasibility in resource-limited settings." className={textareaCls} />
                </Field>

                <Field label="Hypothesis / Research Question" required hint="State your primary testable hypothesis or main research question" error={errors.hypothesis?.message}>
                  <textarea {...register("hypothesis")} rows={3} placeholder="We hypothesise that a Vision Transformer (ViT) fine-tuned on a multi-ethnic fundus dataset will achieve ≥95% sensitivity and ≥92% specificity for early-stage (Grade 1-2) diabetic retinopathy detection, significantly outperforming existing CNN baselines (p < 0.05) across all demographic subgroups." className={textareaCls} />
                </Field>

                <Field label="Novel Contribution" required hint="What is genuinely new? What does this paper add that no other paper has?" error={errors.novel_contribution?.message}>
                  <textarea {...register("novel_contribution")} rows={3} placeholder="(1) First ViT model validated across 5 ethnic cohorts (n=12,450). (2) Novel multi-scale attention mechanism improving early-stage lesion localisation. (3) Edge-deployment optimisation achieving <200ms inference on low-cost hardware. (4) Open-source clinical decision support toolkit." className={textareaCls} />
                </Field>

                <Field label="Research Objectives" required hint="List 3-5 specific, measurable objectives (numbered or comma-separated)" error={errors.objectives?.message}>
                  <textarea {...register("objectives")} rows={3} placeholder="1. Develop and train a ViT-Large model on 12,450 multi-ethnic fundus images. 2. Validate sensitivity/specificity against ophthalmologist ground truth. 3. Compare performance against ResNet-50, EfficientNet-B4, and DenseNet-121 baselines. 4. Assess demographic subgroup performance equity. 5. Benchmark inference speed for edge deployment." className={textareaCls} />
                </Field>

                <Field label="Scope & Limitations" hint="Optional: define boundaries and acknowledged limitations" error={errors.scope?.message}>
                  <textarea {...register("scope")} rows={2} placeholder="Study limited to fundus photography; does not address OCT imaging. Model trained on Grade 1-4 DR only; does not classify diabetic macular oedema independently." className={textareaCls} />
                </Field>
              </motion.div>
            )}

            {/* ── Step 3: Authors & Ethics ──────────────────────────────── */}
            {step === 2 && (
              <motion.div key="s2" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -16 }} className="space-y-5">
                <StepHeader icon={Users} title="Authors & Ethics" desc="Author information, funding disclosure, and ethical declarations — mandatory for top-tier journals." />

                <div className="grid grid-cols-2 gap-4">
                  <Field label="Lead Author Name" required error={errors.author_name?.message}>
                    <input {...register("author_name")} placeholder="Dr. Sarah M. Johnson" className={inputCls} />
                  </Field>
                  <Field label="Lead Author Affiliation" required error={errors.author_affiliation?.message}>
                    <input {...register("author_affiliation")} placeholder="Harvard Medical School, Boston, MA, USA" className={inputCls} />
                  </Field>
                </div>

                {/* Co-authors */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <label className="text-sm font-medium text-gray-200">Co-Authors</label>
                    <button
                      type="button"
                      onClick={() => appendAuthor({ name: "", affiliation: "", contribution: "" })}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-lg transition-colors"
                    >
                      <Plus className="w-3 h-3" /> Add Co-Author
                    </button>
                  </div>
                  {authorFields.map((field, i) => (
                    <div key={field.id} className="bg-gray-900/50 border border-gray-800 rounded-lg p-4 space-y-3">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs text-gray-500 font-medium">Co-Author {i + 1}</span>
                        <button type="button" onClick={() => removeAuthor(i)} className="text-gray-600 hover:text-red-400 transition-colors">
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                      <div className="grid grid-cols-2 gap-3">
                        <input {...register(`all_authors.${i}.name`)} placeholder="Full Name" className={inputCls} />
                        <input {...register(`all_authors.${i}.affiliation`)} placeholder="Institution" className={inputCls} />
                      </div>
                      <input {...register(`all_authors.${i}.contribution`)} placeholder="Contribution (e.g., Data curation, Formal analysis)" className={inputCls} />
                    </div>
                  ))}
                </div>

                <Field label="Funding Source" hint="Grant number + funding agency, or leave blank for 'no funding'" error={errors.funding_source?.message}>
                  <input {...register("funding_source")} placeholder="NIH R01 EY034567 (National Institutes of Health, USA) / No specific funding received" className={inputCls} />
                </Field>

                <Field label="Conflicts of Interest" hint="Any financial, personal, or professional relationships that may bias the work" error={errors.conflicts_of_interest_input?.message}>
                  <input {...register("conflicts_of_interest_input")} placeholder="None / Dr. Johnson is a consultant for EyeAI Inc. (unrelated to this study)" className={inputCls} />
                </Field>

                <Field label="Ethics / IRB Statement" hint="For human/animal studies; for computational work leave blank" error={errors.ethics_statement_input?.message}>
                  <textarea {...register("ethics_statement_input")} rows={2} placeholder="Study approved by Harvard IRB (Protocol #2024-0234). All patients provided written informed consent. Data anonymised prior to analysis." className={textareaCls} />
                </Field>
              </motion.div>
            )}

            {/* ── Step 4: Methodology & Data ────────────────────────────── */}
            {step === 3 && (
              <motion.div key="s3" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -16 }} className="space-y-5">
                <StepHeader icon={Microscope} title="Methodology & Data" desc="Detailed enough that another lab can replicate your study. This drives the Materials & Methods section." />

                <Field label="Research Design & Methodology" required hint="Step-by-step approach: how did you collect data / run experiments / develop your method?" error={errors.methodology_description?.message}>
                  <textarea {...register("methodology_description")} rows={5} placeholder="We collected fundus images from 5 clinical centres across UK, India, Nigeria, China, and Brazil (2019-2023). Images graded by 3 independent ophthalmologists using ETDRS classification. Model architecture: ViT-Large/16 (pretrained ImageNet-21k, fine-tuned). Training: 80/10/10 split, batch size 32, AdamW optimiser (lr=1e-4, weight decay=0.01), 50 epochs with cosine annealing. Augmentation: horizontal/vertical flip, rotation ±30°, colour jitter. Uncertainty quantification via Monte Carlo Dropout (T=50)." className={textareaCls} />
                </Field>

                <div className="grid grid-cols-2 gap-4">
                  <Field label="Dataset / Study Subjects" required error={errors.dataset_description?.message}>
                    <textarea {...register("dataset_description")} rows={3} placeholder="12,450 fundus images from 6,225 patients (mean age 54.3±11.2 years; 48% female). 3,100 Grade 0 (normal), 2,890 Grade 1-2 (early DR), 4,120 Grade 3-4 (advanced DR), 2,340 Grade 5 (proliferative). Multi-ethnic cohort: 2,490/cohort." className={textareaCls} />
                  </Field>
                  <Field label="Analysis Methods & Statistical Tests" required error={errors.analysis_methods?.message}>
                    <textarea {...register("analysis_methods")} rows={3} placeholder="Primary metrics: sensitivity, specificity, AUC-ROC, F1-score. Statistical comparison: DeLong test for AUC comparison. Subgroup analysis: sex, age decile, ethnicity. Calibration: Expected Calibration Error (ECE). Significance threshold: p < 0.05." className={textareaCls} />
                  </Field>
                </div>

                <Field label="Software & Tools" hint="List key software, programming languages, libraries, hardware" error={errors.tools_used?.message}>
                  <input {...register("tools_used")} placeholder="Python 3.10, PyTorch 2.1, timm 0.9.7, scikit-learn 1.3, NVIDIA A100 80GB × 4, MONAI 1.3" className={inputCls} />
                </Field>

                <Field label="Expected Key Findings" required hint="What results do you anticipate? Be specific with estimated values if possible." error={errors.expected_findings?.message}>
                  <textarea {...register("expected_findings")} rows={3} placeholder="1. ViT model achieves AUC 0.97 (95% CI: 0.96-0.98) for early DR detection vs. ResNet-50 AUC 0.89 (p<0.001). 2. Consistent performance across all 5 ethnic groups (AUC range 0.95-0.98). 3. Inference time 143ms on edge hardware — clinically deployable." className={textareaCls} />
                </Field>

                <Field label="Research Significance & Impact" required hint="Why does this matter? What changes if your hypothesis is confirmed?" error={errors.research_significance?.message}>
                  <textarea {...register("research_significance")} rows={3} placeholder="Successful validation would enable affordable DR screening in resource-limited settings, potentially preventing 1.4M cases of preventable blindness annually. Demonstrates that transformer-based AI can match ophthalmologist performance at a fraction of the cost." className={textareaCls} />
                </Field>
              </motion.div>
            )}

            {/* ── Step 5: Paper Settings ────────────────────────────────── */}
            {step === 4 && (
              <motion.div key="s4" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -16 }} className="space-y-5">
                <StepHeader icon={Settings2} title="Paper Settings" desc="Configure journal targets, citation style, and output preferences." />

                <div className="grid grid-cols-2 gap-4">
                  <Field label="Target Journal Type" required error={errors.journal_type?.message}>
                    <select {...register("journal_type")} className={inputCls}>
                      {[
                        ["sci", "SCI Indexed"],
                        ["scopus", "Scopus"],
                        ["web_of_science", "Web of Science"],
                        ["ieee", "IEEE Transactions"],
                        ["nature", "Nature Portfolio"],
                        ["elsevier", "Elsevier"],
                        ["springer", "Springer"],
                        ["plos", "PLOS ONE"],
                        ["mdpi", "MDPI"],
                        ["frontiers", "Frontiers"],
                      ].map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                    </select>
                  </Field>
                  <Field label="Citation Style" required error={errors.citation_style?.message}>
                    <select {...register("citation_style")} className={inputCls}>
                      {["ieee","apa","mla","chicago","harvard","vancouver","nature","acs"].map((c) => (
                        <option key={c} value={c}>{c.toUpperCase()}</option>
                      ))}
                    </select>
                  </Field>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <Field label="Target Word Count" hint="3,000–20,000 words" error={errors.preferred_word_count?.message}>
                    <Controller
                      name="preferred_word_count"
                      control={control}
                      render={({ field }) => (
                        <div className="space-y-2">
                          <input
                            type="range" min={3000} max={20000} step={500}
                            value={field.value}
                            onChange={(e) => field.onChange(parseInt(e.target.value))}
                            className="w-full accent-blue-500"
                          />
                          <div className="flex justify-between text-xs text-gray-500">
                            <span>3,000</span>
                            <span className="text-blue-400 font-semibold">{field.value.toLocaleString()} words</span>
                            <span>20,000</span>
                          </div>
                        </div>
                      )}
                    />
                  </Field>
                  <Field label="Writing Tone" required error={errors.writing_tone?.message}>
                    <select {...register("writing_tone")} className={inputCls}>
                      {[["academic","Academic (General SCI)"],["technical","Technical (Engineering)"],["review","Review Article"],["clinical","Clinical / Medical"],["engineering","Applied Engineering"]].map(([v, l]) => (
                        <option key={v} value={v}>{l}</option>
                      ))}
                    </select>
                  </Field>
                </div>

                <Field label="Additional Instructions" hint="Anything specific: particular theories to emphasise, sections to expand, competitor papers to address" error={errors.additional_instructions?.message}>
                  <textarea {...register("additional_instructions")} rows={4} placeholder="Please specifically address the comparison with Google DeepMind's ARDA system. Emphasise the multi-ethnic validation as the key differentiator. Methodology section should include a detailed ablation study description." className={textareaCls} />
                </Field>

                {/* Quality badges */}
                <div className="grid grid-cols-3 gap-3 pt-2">
                  {[
                    ["11 Literature Sources", "Semantic Scholar · CrossRef · arXiv · PubMed · OpenAlex + more"],
                    ["9-Module AI Pipeline", "Extraction → Research → Auth → Plagiarism → Humanize → Audit → Editor → DocGen"],
                    ["Full Top-1% Structure", "Abstract · Methods · Results · Discussion + Author Credits · Funding · COI · Supplementary"],
                  ].map(([title, desc]) => (
                    <div key={title as string} className="bg-blue-500/5 border border-blue-500/20 rounded-lg p-3">
                      <div className="text-xs font-semibold text-blue-300 mb-1">{title}</div>
                      <div className="text-xs text-gray-500 leading-relaxed">{desc}</div>
                    </div>
                  ))}
                </div>
              </motion.div>
            )}

            {/* ── Step 6: Upload & Launch ───────────────────────────────── */}
            {step === 5 && (
              <motion.div key="s5" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -16 }} className="space-y-6">
                <StepHeader icon={Upload} title="Upload Materials & Launch" desc="Upload your research files — raw data, existing drafts, images, datasets. The AI will extract and use all content." />

                <div
                  {...getRootProps()}
                  className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-all ${
                    isDragActive
                      ? "border-blue-400 bg-blue-400/5 scale-[1.01]"
                      : "border-gray-700 hover:border-gray-500 hover:bg-white/[0.02]"
                  }`}
                >
                  <input {...getInputProps()} />
                  <Upload className={`w-10 h-10 mx-auto mb-3 ${isDragActive ? "text-blue-400" : "text-gray-600"}`} />
                  <p className="text-sm font-medium mb-1">{isDragActive ? "Drop files here" : "Drag & drop your research materials"}</p>
                  <p className="text-xs text-gray-500 leading-relaxed">
                    PDF papers · DOCX drafts · PPTX presentations · XLSX/CSV datasets · PNG/JPG figures<br />
                    Up to 50MB each · Max 20 files · AI reads and extracts all content
                  </p>
                </div>

                {uploadedFiles.length > 0 && (
                  <div className="space-y-2">
                    <p className="text-xs font-medium text-gray-400">{uploadedFiles.length} file{uploadedFiles.length !== 1 ? "s" : ""} ready</p>
                    {uploadedFiles.map((file, i) => (
                      <div key={i} className="flex items-center gap-3 p-3 bg-gray-900 border border-gray-800 rounded-lg">
                        <FileText className="w-4 h-4 text-blue-400 flex-shrink-0" />
                        <span className="text-sm text-gray-300 flex-1 truncate">{file.name}</span>
                        <span className="text-xs text-gray-600">{(file.size / 1024 / 1024).toFixed(1)} MB</span>
                        <button type="button" onClick={() => setUploadedFiles((p) => p.filter((_, j) => j !== i))}
                          className="text-gray-600 hover:text-red-400 transition-colors">
                          <X className="w-4 h-4" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}

                {/* Summary card */}
                <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-5 space-y-3">
                  <p className="text-sm font-semibold text-gray-200">Pipeline Summary</p>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    {[
                      ["Paper Title", watch("title")?.substring(0, 60) + "..."],
                      ["Domain", watch("domain")],
                      ["Study Type", STUDY_TYPES.find(t => t.value === watch("study_type"))?.label],
                      ["Lead Author", watch("author_name")],
                      ["Target Journal", watch("journal_type")?.toUpperCase().replace("_", " ")],
                      ["Citation Style", watch("citation_style")?.toUpperCase()],
                      ["Word Count", `${watch("preferred_word_count")?.toLocaleString()} words`],
                      ["Files", `${uploadedFiles.length} file${uploadedFiles.length !== 1 ? "s" : ""} uploaded`],
                    ].map(([k, v]) => (
                      <div key={k as string} className="flex gap-2">
                        <span className="text-gray-600 flex-shrink-0">{k}:</span>
                        <span className="text-gray-300 truncate">{v || "—"}</span>
                      </div>
                    ))}
                  </div>
                  <div className="text-xs text-gray-500 pt-1 border-t border-gray-800">
                    Estimated generation time: 8–25 minutes · The pipeline retries until Editor Score ≥ 9.0/10
                  </div>
                </div>
              </motion.div>
            )}

          </AnimatePresence>

          {/* Navigation */}
          <div className="flex items-center justify-between mt-10 pt-6 border-t border-gray-800">
            <button
              type="button"
              onClick={() => setStep((s) => s - 1)}
              disabled={step === 0}
              className="flex items-center gap-2 px-5 py-2.5 border border-gray-700 rounded-lg text-sm font-medium disabled:opacity-30 hover:border-gray-500 transition-colors"
            >
              <ChevronLeft className="w-4 h-4" /> Back
            </button>

            {step < STEPS.length - 1 ? (
              <button
                type="button"
                onClick={nextStep}
                className="flex items-center gap-2 px-6 py-2.5 bg-blue-600 hover:bg-blue-500 rounded-lg text-sm font-semibold transition-colors"
              >
                Continue <ChevronRight className="w-4 h-4" />
              </button>
            ) : (
              <button
                type="submit"
                disabled={isSubmitting}
                className="flex items-center gap-2 px-8 py-2.5 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 rounded-lg text-sm font-semibold transition-all disabled:opacity-50 shadow-lg shadow-blue-900/30"
              >
                {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Brain className="w-4 h-4" />}
                {isSubmitting ? "Launching Pipeline..." : "Launch AI Pipeline"}
              </button>
            )}
          </div>
        </form>
      </div>
    </div>
  );
}

function StepHeader({ icon: Icon, title, desc }: { icon: any; title: string; desc: string }) {
  return (
    <div className="flex items-start gap-3 pb-4 border-b border-gray-800 mb-2">
      <div className="w-9 h-9 rounded-lg bg-blue-600/15 border border-blue-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
        <Icon className="w-4.5 h-4.5 text-blue-400" />
      </div>
      <div>
        <h2 className="font-semibold text-white text-lg">{title}</h2>
        <p className="text-sm text-gray-500 mt-0.5">{desc}</p>
      </div>
    </div>
  );
}
