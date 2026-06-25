"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import { UserButton } from "@clerk/nextjs";
import { motion } from "framer-motion";
import {
  Brain, LayoutDashboard, Plus, Settings, HelpCircle,
  BarChart3, FileText, Shield, ChevronRight
} from "lucide-react";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/dashboard/new", label: "New Research", icon: Plus },
  { href: "/admin", label: "Analytics", icon: BarChart3 },
  { href: "/settings", label: "Settings", icon: Settings },
  { href: "/help", label: "Help", icon: HelpCircle },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen bg-gray-950 flex">
      {/* Sidebar */}
      <aside className="w-60 flex-shrink-0 border-r border-gray-800 flex flex-col">
        {/* Logo */}
        <div className="h-16 flex items-center gap-2.5 px-5 border-b border-gray-800">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center flex-shrink-0">
            <Brain className="w-4.5 h-4.5 text-white" />
          </div>
          <span className="font-bold text-sm tracking-tight leading-tight">
            SCI Research<br />
            <span className="text-blue-400 font-normal">Platform</span>
          </span>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {NAV_ITEMS.map((item) => {
            const active = pathname === item.href || (item.href !== "/dashboard" && pathname.startsWith(item.href));
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all group ${
                  active
                    ? "bg-blue-600/20 text-blue-400 border border-blue-600/30"
                    : "text-gray-400 hover:text-gray-200 hover:bg-white/5"
                }`}
              >
                <item.icon className={`w-4 h-4 flex-shrink-0 ${active ? "text-blue-400" : "text-gray-500 group-hover:text-gray-300"}`} />
                {item.label}
              </Link>
            );
          })}
        </nav>

        {/* Pipeline legend */}
        <div className="px-4 py-4 border-t border-gray-800">
          <p className="text-xs text-gray-600 mb-2 font-medium uppercase tracking-wider">Pipeline</p>
          {[
            { color: "bg-blue-500", label: "In Progress" },
            { color: "bg-emerald-500", label: "Completed" },
            { color: "bg-red-500", label: "Failed" },
          ].map((s) => (
            <div key={s.label} className="flex items-center gap-2 text-xs text-gray-500 mb-1">
              <div className={`w-2 h-2 rounded-full ${s.color}`} />
              {s.label}
            </div>
          ))}
        </div>

        {/* User */}
        <div className="px-4 py-4 border-t border-gray-800 flex items-center gap-3">
          <UserButton afterSignOutUrl="/" />
          <span className="text-xs text-gray-500">Account</span>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 min-w-0 overflow-y-auto">
        {children}
      </main>
    </div>
  );
}
