import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export function MarkdownMessage({ children }: { children: string }) {
  return (
    <div className="prose prose-sm max-w-none break-words prose-headings:mb-2 prose-headings:mt-5 prose-p:my-2 prose-pre:overflow-x-auto prose-pre:rounded-xl prose-pre:bg-[var(--color-code)] prose-pre:text-[var(--color-code-ink)] prose-code:before:content-none prose-code:after:content-none prose-a:text-primary prose-table:block prose-table:overflow-x-auto">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: (props) => <a {...props} target="_blank" rel="noreferrer" />,
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
