interface MarkdownPreviewProps {
  content?: string
}

export function MarkdownPreview({ content }: MarkdownPreviewProps) {
  if (!content) return null

  // For Phase 2, a simplified markdown renderer.
  // In a real scenario, use react-markdown with remark-gfm.
  const renderSimpleMarkdown = (text: string) => {
    return text.split('\n').map((line, i) => {
      if (line.startsWith('### ')) {
        return <h3 key={i} className="text-lg font-semibold mt-4 mb-2">{line.substring(4)}</h3>
      }
      if (line.startsWith('#### ')) {
        return <h4 key={i} className="text-base font-semibold mt-4 mb-2">{line.substring(5)}</h4>
      }
      if (line.startsWith('⚠️ ')) {
        const strongReplaced = line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        return <p key={i} className="mb-2" dangerouslySetInnerHTML={{ __html: strongReplaced }} />
      }
      if (line.startsWith('* ')) {
        const strongReplaced = line.substring(2).replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        return <li key={i} className="ml-4 list-disc mb-1" dangerouslySetInnerHTML={{ __html: strongReplaced }} />
      }
      if (line.startsWith('---')) {
        return <hr key={i} className="my-4 border-border" />
      }
      const italicReplaced = line.replace(/\*(.*?)\*/g, '<em>$1</em>')
      return <p key={i} dangerouslySetInnerHTML={{ __html: italicReplaced }} className="mb-1" />
    })
  }

  return (
    <div className="rounded-xl border border-border bg-card overflow-hidden shadow-sm">
      <div className="flex items-center gap-2 px-4 py-3 bg-secondary/30 border-b border-border">
        <svg className="h-4 w-4 text-muted-foreground" fill="currentColor" viewBox="0 0 24 24">
          <path fillRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clipRule="evenodd" />
        </svg>
        <span className="text-sm font-medium text-foreground">GitHub Comment Preview</span>
      </div>
      <div className="p-6 text-sm text-foreground bg-[#0d1117]">
        {/* Simulating GitHub's dark mode background and typography */}
        <div className="max-w-none">
          {renderSimpleMarkdown(content)}
        </div>
      </div>
    </div>
  )
}
