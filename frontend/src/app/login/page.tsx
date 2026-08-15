import { Metadata } from "next"
import Image from "next/image"
import { Suspense } from "react"
import { LoginForm } from "@/components/auth/login-form"

export const metadata: Metadata = {
  title: "Login | Ignition",
  description: "Login to Ignition AI Code Review Platform",
}

export default function LoginPage() {
  return (
    <div className="min-h-screen flex flex-col justify-center py-12 sm:px-6 lg:px-8 bg-background bg-ignition-pattern relative overflow-hidden">
      {/* Subtle background glow effect */}
      <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] rounded-full bg-primary/5 blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] rounded-full bg-primary/5 blur-[120px] pointer-events-none" />

      <div className="sm:mx-auto sm:w-full sm:max-w-md relative z-10 flex flex-col items-center">
        <h1 className="sr-only">Ignition - Autonomous Multi-Agent AI Code Review Platform</h1>
        <Image 
          src="/logo.png" 
          alt="Ignition" 
          width={240} 
          height={160} 
          className="h-32 w-auto object-contain"
          priority
        />
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md relative z-10">
        <div className="bg-card/70 backdrop-blur-lg py-8 px-4 shadow-xl shadow-black/40 border border-white/[0.08] sm:rounded-xl sm:px-10">
          <Suspense fallback={<div className="h-40 flex items-center justify-center text-xs text-muted-foreground">Loading sign-in options...</div>}>
            <LoginForm />
          </Suspense>
          
          <div className="mt-6 text-center">
            <p className="text-xs text-muted-foreground">
              By signing in, you agree to our Terms of Service and Privacy Policy.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
