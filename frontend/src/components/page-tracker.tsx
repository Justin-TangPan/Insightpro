"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";
import { trackPage } from "@/utils/track";

export function PageTracker() {
  const pathname = usePathname();

  useEffect(() => {
    trackPage(pathname);
  }, [pathname]);

  return null;
}
