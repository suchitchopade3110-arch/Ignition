import { Metadata } from "next"
import Link from "next/link"
import Image from "next/image"

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
        <Image 
          src="/logo.svg" 
          alt="Ignition Logo" 
          width={180} 
          height={180} 
          className="object-contain"
          priority
        />
        <h2 className="mt-2 text-center text-3xl font-bold tracking-tight text-foreground">
          Ignition
        </h2>
        <p className="mt-2 text-center text-sm text-muted-foreground">
          Autonomous Multi-Agent AI Code Review Platform
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md relative z-10">
        <div className="bg-card py-8 px-4 shadow-xl border border-border sm:rounded-xl sm:px-10">
          <div className="space-y-6">
            <div>
              <Link
                href="/dashboard"
                className="w-full flex justify-center items-center gap-2 py-2.5 px-4 border border-border rounded-lg shadow-sm bg-background text-sm font-medium text-foreground hover:bg-secondary transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary focus:ring-offset-background"
              >
                <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path fillRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clipRule="evenodd" />
                </svg>
                Continue with GitHub
              </Link>
            </div>

            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-border" />
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-2 bg-card text-muted-foreground">
                  Enterprise SSO
                </span>
              </div>
            </div>

            <div>
              <button
                type="button"
                disabled
                className="w-full flex justify-center py-2.5 px-4 border border-transparent rounded-lg shadow-sm text-sm font-medium text-primary-foreground bg-primary/80 hover:bg-primary cursor-not-allowed opacity-50 transition-colors"
              >
                Sign in with SAML
              </button>
            </div>
          </div>
          
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
