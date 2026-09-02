import { redirect } from "next/navigation";

export default async function LegacyRequirementCreatePage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const source = await searchParams;
  const target = new URLSearchParams();
  for (const key of ["title", "source_url"])
    if (typeof source[key] === "string") target.set(key, source[key]);
  redirect(`/workbench/solutions/new${target.size ? `?${target}` : ""}`);
}
