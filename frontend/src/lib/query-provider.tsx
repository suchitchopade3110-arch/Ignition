"use client"

import { ReactNode, useState } from "react"
import { QueryClientProvider } from "@tanstack/react-query"
import { getQueryClient } from "./query-client"

export function QueryProvider({ children }: { children: ReactNode }) {
  // Ensure queryClient is retained across client re-renders
  const [queryClient] = useState(() => getQueryClient())

  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  )
}
