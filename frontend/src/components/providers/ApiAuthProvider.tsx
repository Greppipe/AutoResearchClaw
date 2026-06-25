"use client";

import { useAuth } from "@clerk/nextjs";
import { useEffect } from "react";
import { apiClient } from "@/lib/api";

/** Only rendered when ClerkProvider is in the tree */
function ClerkTokenWirer() {
  const { getToken } = useAuth();
  useEffect(() => {
    apiClient.setTokenGetter(() => getToken());
  }, [getToken]);
  return null;
}

export function ApiAuthProvider({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}

export { ClerkTokenWirer };
