"use client";

import { ButtonHTMLAttributes, MouseEvent, ReactNode, useRef, useState } from "react";
import { runOnce } from "@/lib/ui-actions";

type Props = Omit<ButtonHTMLAttributes<HTMLButtonElement>, "onClick"> & {
  onClick?: (event: MouseEvent<HTMLButtonElement>) => void | Promise<void>;
  pendingLabel?: ReactNode;
};

export function ActionButton({ children, className = "", disabled, onClick, pendingLabel, ...props }: Props) {
  const lock = useRef(false);
  const [pending, setPending] = useState(false);
  const handleClick = (event: MouseEvent<HTMLButtonElement>) => void runOnce(lock, async () => {
    setPending(true);
    try { await onClick?.(event); }
    finally { setPending(false); }
  });

  return <button {...props} disabled={disabled || pending} aria-busy={pending || undefined} onClick={handleClick} className={`ui-action-button ${className}`}>{pending ? pendingLabel || children : children}</button>;
}
