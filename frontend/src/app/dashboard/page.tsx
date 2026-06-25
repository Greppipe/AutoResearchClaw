"use client";

import { useUser } from "@clerk/nextjs";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import Link from "next/link";
import { Plus, FileText, Clock, CheckCircle, AlertCircle, BarChart3, Loader2 } from "lucide-react";
import { format } from "date-fns";
import { apiClient } from "@/lib/api";
import { ResearchProject } from "@/types/research";

const STATUS_CONFIG: Record<string, { label: string; color: string; icon: typeof CheckCircle }> = {
  pending: { label: "Pending", color: "text-gray-400", icon: Clock },
  extracting: { label: "Extracting", color: "text-blue-400", icon: Loader2 },
  researching: { label: "Researching", color: "text-purple-400", icon: Loader2 },
  authenticating: { label: "Authenticating", color: "text-yellow-400", icon: Loader2 },
  plagiarism_check: { label: "Plagiarism Scan", color: "text-orange-400", icon: Loader2 },
  humanizing: { label: "Humanizing", color: "text-pink-400", icon: Loader2 },
  auditing: { label: "Auditing", color: "text-cyan-400", icon: Loader2 },
  editor_review: { label: "Editor Review", color: "text-indigo-400", icon: Loader2 },
  generating: { label: "Generating", color: "text-green-400", icon: Loader2 },
  completed: { label: "Completed", color: "text-emerald-400", icon: CheckCircle },
  failed: { label: "Failed", color: "text-red-400", icon: AlertCircle },
};

export default function DashboardPage() {
  const { user } = useUser();

  const { data, isLoading, error } = useQuery({
    queryKey: ["projects"],
    queryFn: () => apiClient.get<{ items: ResearchProject[]; total: number }>("/api/v1/research/projects"),
    refetchInterval: 5000,
  });

  const projects = data?.items ?? [];
  const stats = {
    total: data?.total ?? 0,
    completed: projects.filter((p) => p.status === "completed").length,
    inProgress: projects.filter((p) => !["pending", "completed", "failed"].includes(p.status)).length,
    avgScore: projects.reduce((acc, p) => acc + (p.editor_score ?? 0), 0) / Math.max(projects.filter((p) => p.editor_score).length, 1),
  };

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold">Research Dashboard</h1>
            <p className="text-gray-400 mt-1">Welcome back, {user?.firstName ?? "Researcher"}</p>
          </div>
          <Link
            href="/dashboard/new"
            className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-500 rounded-xl text-sm font-medium transition-colors"
          >
            <Plus className="w-4 h-4" />
            New Research
          </Link>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {[
            { label: "Total Projects", value: stats.total, icon: FileText, color: "blue" },
            { label: "Completed", value: stats.completed, icon: CheckCircle, color: "emerald" },
            { label: "In Progress", value: stats.inProgress, icon: Loader2, color: "purple" },
            { label: "Avg Editor Score", value: stats.avgScore.toFixed(1) + "/10", icon: BarChart3, color: "yellow" },
          ].map((stat) => (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="glass-card p-5"
            >
              <div className={`text-${stat.color}-400 mb-2`}>
                <stat.icon className="w-5 h-5" />
              </div>
              <div className="text-2xl font-bold">{stat.value}</div>
              <div className="text-xs text-gray-500 mt-0.5">{stat.label}</div>
            </motion.div>
          ))}
        </div>

        {/* Projects List */}
        <div className="glass-card overflow-hidden">
          <div className="p-5 border-b border-gray-800">
            <h2 className="font-semibold text-lg">Research Projects</h2>
          </div>

          {isLoading ? (
            <div className="flex items-center justify-center py-20">
              <Loader2 className="w-8 h-8 animate-spin text-blue-400" />
            </div>
          ) : projects.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-gray-500">
              <FileText className="w-12 h-12 mb-4 opacity-30" />
              <p className="text-lg font-medium mb-2">No projects yet</p>
              <p className="text-sm">Create your first research project to get started</p>
              <Link href="/dashboard/new" className="mt-6 px-5 py-2 bg-blue-600 rounded-lg text-sm font-medium text-white hover:bg-blue-500 transition-colors">
                Create Project
              </Link>
            </div>
          ) : (
            <div className="divide-y divide-gray-800">
              {projects.map((project) => {
                const statusConf = STATUS_CONFIG[project.status] ?? STATUS_CONFIG.pending;
                const StatusIcon = statusConf.icon;
                return (
                  <motion.div
                    key={project.id}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="p-5 hover:bg-white/2 transition-colors"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <Link
                          href={`/dashboard/projects/${project.id}`}
                          className="font-medium text-white hover:text-blue-400 transition-colors line-clamp-1"
                        >
                          {project.title}
                        </Link>
                        <div className="flex items-center gap-4 mt-1.5 text-xs text-gray-500">
                          <span>{project.domain}</span>
                          <span>{format(new Date(project.created_at), "MMM d, yyyy")}</span>
                          {project.editor_score != null && (
                            <span className="text-yellow-400 font-medium">Score: {project.editor_score.toFixed(1)}/10</span>
                          )}
                          {project.plagiarism_score != null && (
                            <span>Plagiarism: {project.plagiarism_score.toFixed(1)}%</span>
                          )}
                        </div>
                      </div>
                      <div className={`flex items-center gap-1.5 text-xs font-medium ${statusConf.color} whitespace-nowrap`}>
                        <StatusIcon className={`w-3.5 h-3.5 ${project.status !== "completed" && project.status !== "failed" && project.status !== "pending" ? "animate-spin" : ""}`} />
                        {statusConf.label}
                      </div>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
