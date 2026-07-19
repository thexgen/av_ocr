import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { Components } from 'react-markdown'

const components: Components = {
  h1: ({ children }) => (
    <h1 className="mb-2 mt-1 text-base font-bold tracking-tight text-white first:mt-0">
      {children}
    </h1>
  ),
  h2: ({ children }) => (
    <h2 className="mb-1.5 mt-2 text-sm font-semibold tracking-tight text-cyan-100 first:mt-0">
      {children}
    </h2>
  ),
  h3: ({ children }) => (
    <h3 className="mb-1 mt-2 text-sm font-semibold text-slate-100 first:mt-0">
      {children}
    </h3>
  ),
  p: ({ children }) => (
    <p className="mb-2 text-sm leading-relaxed text-slate-200 last:mb-0">
      {children}
    </p>
  ),
  strong: ({ children }) => (
    <strong className="font-semibold text-white">{children}</strong>
  ),
  em: ({ children }) => <em className="italic text-slate-300">{children}</em>,
  ul: ({ children }) => (
    <ul className="mb-2 list-disc space-y-1 pl-4 text-sm text-slate-200 last:mb-0">
      {children}
    </ul>
  ),
  ol: ({ children }) => (
    <ol className="mb-2 list-decimal space-y-1 pl-4 text-sm text-slate-200 last:mb-0">
      {children}
    </ol>
  ),
  li: ({ children }) => <li className="leading-relaxed marker:text-cyan-400/70">{children}</li>,
  a: ({ href, children }) => (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="text-cyan-300 underline decoration-cyan-400/40 underline-offset-2 hover:text-cyan-200"
    >
      {children}
    </a>
  ),
  code: ({ className, children }) => {
    const isBlock = Boolean(className?.includes('language-'))
    if (isBlock) {
      return (
        <code className="font-mono text-[12px] leading-relaxed text-cyan-100">
          {children}
        </code>
      )
    }
    return (
      <code className="rounded bg-white/10 px-1 py-0.5 font-mono text-[12px] text-cyan-200">
        {children}
      </code>
    )
  },
  pre: ({ children }) => (
    <pre className="mb-2 overflow-x-auto rounded-lg border border-white/10 bg-navy-950/60 p-2.5 last:mb-0">
      {children}
    </pre>
  ),
  blockquote: ({ children }) => (
    <blockquote className="mb-2 border-l-2 border-cyan-400/40 pl-3 text-slate-300 italic last:mb-0">
      {children}
    </blockquote>
  ),
  table: ({ children }) => (
    <div className="jessy-md-table mb-2 overflow-x-auto last:mb-0">
      <table className="w-full min-w-[240px] border-collapse text-left text-[12px]">
        {children}
      </table>
    </div>
  ),
  thead: ({ children }) => (
    <thead className="border-b border-cyan-400/25 bg-white/[0.04] text-cyan-100">
      {children}
    </thead>
  ),
  th: ({ children }) => (
    <th className="px-2.5 py-1.5 font-semibold whitespace-nowrap">{children}</th>
  ),
  td: ({ children }) => (
    <td className="border-t border-white/5 px-2.5 py-1.5 text-slate-300">
      {children}
    </td>
  ),
  tr: ({ children }) => (
    <tr className="even:bg-white/[0.02]">{children}</tr>
  ),
  hr: () => <hr className="my-3 border-white/10" />,
}

export function MarkdownContent({ content }: { content: string }) {
  if (!content.trim()) return null

  return (
    <div className="jessy-md">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {content}
      </ReactMarkdown>
    </div>
  )
}
