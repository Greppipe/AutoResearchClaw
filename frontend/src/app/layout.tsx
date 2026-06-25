import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { ClerkProvider } from "@clerk/nextjs";
import { Toaster } from "react-hot-toast";
import { QueryProvider } from "@/components/providers/QueryProvider";
import { ClerkTokenWirer } from "@/components/providers/ApiAuthProvider";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "SCI Research Platform — AI-Powered Scientific Publishing",
  description: "Generate SCI/Scopus/WoS journal-ready papers from raw research inputs using 9-agent AI.",
  keywords: ["scientific publishing", "AI research", "paper generation", "SCI journal"],
};

const clerkKey = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY?.startsWith("pk_")
  ? process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
  : undefined;

const body = (inner: React.ReactNode) => (
  <html lang="en" className="dark">
    <body className={`${inter.className} bg-gray-950 text-gray-100 antialiased`}>
      <QueryProvider>
        {clerkKey && <ClerkTokenWirer />}
        {inner}
        <Toaster
          position="top-right"
          toastOptions={{
            style: { background: "#1f2937", color: "#f3f4f6", border: "1px solid #374151" },
            success: { duration: 4000 },
            error: { duration: 6000 },
          }}
        />
      </QueryProvider>
    </body>
  </html>
);

export default function RootLayout({ children }: { children: React.ReactNode }) {
  if (!clerkKey) return body(children);

  return (
    <ClerkProvider
      publishableKey={clerkKey}
      appearance={{
        variables: { colorPrimary: "#3b82f6", colorBackground: "#030712", colorText: "#f3f4f6" },
      }}
    >
      {body(children)}
    </ClerkProvider>
  );
}
