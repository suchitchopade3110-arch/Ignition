import ReactMarkdown, { type Components } from "react-markdown"

interface MarkdownPreviewProps {
  content?: string
}

// Audit P1-4: this text is written by a model from a pull request's
// content, so it is never injected as HTML. react-markdown builds React
// elements (React escapes the text) and skips raw HTML; images are dropped
// too, so a comment can't make the dashboard load a remote URL.
const components: Components = {
  h1: ({ children }) => <h3 className="text-base sm:text-lg font-semibold mt-4 mb-2 text-foreground break-words">{children}</h3>,
  h2: ({ children }) => <h2 className="text-base sm:text-lg font-semibold mt-4 mb-2 text-foreground break-words">{children}</h2>,
  h3: ({ children }) => <h3 className="text-base sm:text-lg font-semibold mt-4 mb-2 text-foreground break-words">{children}</h3>,
  h4: ({ children }) => <h4 className="text-sm sm:text-base font-semibold mt-3 mb-1.5 text-foreground break-words">{children}</h4>,
  p: ({ children }) => <p className="mb-2 text-foreground/90 break-words leading-relaxed">{children}</p>,
  ul: ({ children }) => <ul className="mb-2 space-y-1">{children}</ul>,
  li: ({ children }) => <li className="ml-4 list-disc text-foreground/90 break-words">{children}</li>,
  strong: ({ children }) => <strong className="text-foreground font-semibold">{children}</strong>,
  blockquote: ({ children }) => <blockquote className="border-l-2 border-warning pl-3 my-2 text-foreground/90">{children}</blockquote>,
  code: ({ children }) => <code className="rounded bg-secondary/40 px-1 py-0.5 font-mono text-xs">{children}</code>,
  hr: () => <hr className="my-4 border-border" />,
  a: ({ children, href }) => (
    <a href={href} className="underline" target="_blank" rel="noopener noreferrer nofollow">
      {children}
    </a>
  ),
}

export function MarkdownPreview({ content }: MarkdownPreviewProps) {
  if (!content) return null

  return (
    <div className="rounded-xl border border-border bg-card overflow-hidden shadow-xs w-full max-w-full min-w-0">
      <div className="flex items-center gap-2 px-4 py-3 bg-secondary/30 border-b border-border min-h-[44px]">
        <svg className="h-4 w-4 text-muted-foreground shrink-0" fill="currentColor" viewBox="0 0 24 24">
          <path
            fillRule="evenodd"
            d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
            clipRule="evenodd"
          />
        </svg>
        <span className="text-sm font-medium text-foreground">GitHub Comment Preview</span>
      </div>
      <div className="p-6 text-sm text-foreground bg-[#0d1117] overflow-x-auto max-w-full min-w-0">
        <div className="max-w-none space-y-1">
          <ReactMarkdown skipHtml disallowedElements={["img"]} unwrapDisallowed components={components}>
            {content}
          </ReactMarkdown>
        </div>
      </div>
    </div>
  )
}
