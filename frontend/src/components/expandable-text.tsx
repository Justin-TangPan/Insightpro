"use client";

import { useState } from "react";

interface ExpandableTextProps {
  children: string;
  lines: 1 | 2 | 3;
  className?: string;
  en: boolean;
}

export function ExpandableText({ children, lines, className = "", en }: ExpandableTextProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <>
      <p className={`${className} ${expanded ? "" : { 1: "line-clamp-1", 2: "line-clamp-2", 3: "line-clamp-3" }[lines]}`}>
        {children}
      </p>
      {children && (
        <button
          type="button"
          aria-expanded={expanded}
          onClick={() => setExpanded((value) => !value)}
          className="mt-1 min-h-10 text-xs font-medium text-primary hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
        >
          {expanded ? (en ? "Show less" : "收起") : (en ? "Show more" : "展开")}
        </button>
      )}
    </>
  );
}
