import { cloneElement, ReactElement, useId } from "react";

export function Tooltip({ label, children }: { label: string; children: ReactElement<{ "aria-describedby"?: string }> }) {
  const id = useId();
  const describedBy = [children.props["aria-describedby"], id].filter(Boolean).join(" ");
  return <span className="ui-tooltip">{cloneElement(children, { "aria-describedby": describedBy })}<span id={id} role="tooltip" className="ui-tooltip-content">{label}</span></span>;
}
