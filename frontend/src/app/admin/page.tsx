"use client";

import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { useUser } from "@clerk/nextjs";
import { BarChart3, Users, CheckCircle, AlertCircle, Loader2, FileText, TrendingUp, Brain, Shield } from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line, PieChart, Pie, Cell, Legend
} from "recharts";
import { apiClient } from "@/lib/api";

interface SystemStats {
  total_projects: number;
  completed_projects: number;
  failed_projects: number;
  in_progress_projects: number;
  total_users: number;
  avg_editor_score: number;
  avg_plagiarism_score: number;
  avg_ai_detection_score: number;
  avg_pipeline_iterations: number;
  total_files_uploaded: number;
  projects_today: number;
  projects_this_week: number;
}

interface DomainStat { domain: string; count: number; avg_score: number; }

const COLORS = ["#3b82f6", "#8b5cf6", "#06b6d4", "#10b981", "#f59e0b", "#ef4444", "#ec4899", "#14b8a6"];

export default function AdminDashboard() {
  const { user } = useUser();

  const { data: stats, isLoading } = useQuery({
    queryKey: ["admin-stats"],
    queryFn: () => apiClient.get<SystemStats>("/api/v1/admin/stats"),
    refetchInterval: 30000,
  });

  const { data: domainStats } = useQuery({
    queryKey: ["admin-domain-stats"],
    queryFn: () => apiClient.get<DomainStat[]>("/api/v1/admin/domain-stats"),
  });

  if (isLoading || !stats) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-blue-400" />
      </div>
    );
  }

  const pipelineStatusData = [
    { name: "Completed", value: stats.completed_projects, color: "#10b981" },
    { name: "In Progress", value: stats.in_progress_projects, color: "#3b82f6" },
    { name: "Failed", value: stats.failed_projects, color: "#ef4444" },
    { name: "Pending", value: stats.total_projects - stats.completed_projects - stats.failed_projects - stats.in_progress_projects, color: "#6b7280" },
  ].filter((d) => d.value > 0);

  const metricsData = [
    { name: "Editor Score", value: stats.avg_editor_score, max: 10, color: "#8b5cf6" },
    { name: "Plagiarism %", value: stats.avg_plagiarism_score, max: 100, color: "#ef4444", inverted: true },
    { name: "AI Detection %", value: stats.avg_ai_detection_score, max: 100, color: "#f59e0b", inverted: true },
    { name: "Pipeline Iter.", value: stats.avg_pipeline_iterations, max: 10, color: "#06b6d4" },
  ];

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold">Admin Dashboard</h1>
          <p className="text-gray-400 mt-1">System-wide analytics and monitoring</p>
        </div>

        {/* Top Stats */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {[
            { label: "Total Projects", value: stats.total_projects, icon: FileText, color: "blue" },
            { label: "Total Users", value: stats.total_users, icon: Users, color: "purple" },
            { label: "Files Uploaded", value: stats.total_files_uploaded, icon: FileText, color: "cyan" },
            { label: "Completed", value: `${((stats.completed_projects / Math.max(stats.total_projects, 1)) * 100).toFixed(0)}%`, icon: CheckCircle, color: "emerald" },
          ].map((stat, i) => (
            <motion.div key={stat.label} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }} className="glass-card p-5">
              <div className={`text-${stat.color}-400 mb-2`}><stat.icon className="w-5 h-5" /></div>
              <div className="text-2xl font-bold">{stat.value}</div>
              <div className="text-xs text-gray-500 mt-0.5">{stat.label}</div>
            </motion.div>
          ))}
        </div>

        {/* Activity Cards */}
        <div className="grid grid-cols-2 gap-4 mb-8">
          <div className="glass-card p-5">
            <h3 className="text-sm text-gray-400 mb-1">Projects Today</h3>
            <div className="text-3xl font-bold text-blue-400">{stats.projects_today}</div>
          </div>
          <div className="glass-card p-5">
            <h3 className="text-sm text-gray-400 mb-1">Projects This Week</h3>
            <div className="text-3xl font-bold text-purple-400">{stats.projects_this_week}</div>
          </div>
        </div>

        {/* Charts Row */}
        <div className="grid lg:grid-cols-2 gap-6 mb-8">
          {/* Pipeline Status Pie */}
          <div className="glass-card p-6">
            <h2 className="font-semibold mb-5">Pipeline Status Distribution</h2>
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie data={pipelineStatusData} cx="50%" cy="50%" outerRadius={90} dataKey="value" label={({ name, value }) => `${name}: ${value}`}>
                  {pipelineStatusData.map((entry, index) => (
                    <Cell key={index} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ background: "#111827", border: "1px solid #374151", borderRadius: "8px" }} />
              </PieChart>
            </ResponsiveContainer>
          </div>

          {/* Avg Quality Metrics */}
          <div className="glass-card p-6">
            <h2 className="font-semibold mb-5">Average Quality Metrics</h2>
            <div className="space-y-4">
              {metricsData.map((metric) => (
                <div key={metric.name}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-gray-400">{metric.name}</span>
                    <span className={`font-medium`} style={{ color: metric.color }}>{metric.value.toFixed(2)}</span>
                  </div>
                  <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{
                        width: `${(metric.value / metric.max) * 100}%`,
                        background: metric.color,
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Domain Breakdown */}
        {domainStats && domainStats.length > 0 && (
          <div className="glass-card p-6">
            <h2 className="font-semibold mb-5">Top Research Domains</h2>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={domainStats.slice(0, 10)} margin={{ top: 5, right: 20, left: 0, bottom: 60 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                <XAxis dataKey="domain" tick={{ fill: "#6b7280", fontSize: 11 }} angle={-35} textAnchor="end" />
                <YAxis tick={{ fill: "#6b7280", fontSize: 11 }} />
                <Tooltip contentStyle={{ background: "#111827", border: "1px solid #374151", borderRadius: "8px" }} />
                <Bar dataKey="count" name="Projects" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                <Bar dataKey="avg_score" name="Avg Score" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
                <Legend wrapperStyle={{ color: "#9ca3af", paddingTop: "20px" }} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </div>
  );
}
