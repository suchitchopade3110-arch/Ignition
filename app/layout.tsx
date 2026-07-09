import type { Metadata } from "next"
import { Inter } from "next/font/google"
import "./globals.css"

const inter = Inter({ subsets: ["latin"] })

export const metadata: Metadata = {
  title: "Ignition | Autonomous Multi-Agent AI Code Review",
  description: "Enterprise-grade Autonomous Multi-Agent AI Code Review Platform",
}

import { Toaster } from "@/components/toaster"

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" className="dark" style={{ colorScheme: "dark" }}>
      <body className={`${inter.className} min-h-screen antialiased bg-background text-foreground`}>
        {children}
        <Toaster />
      </body>
    </html>
  )
}
