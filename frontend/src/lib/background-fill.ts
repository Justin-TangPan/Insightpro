export function hasReadableGithubSource(value: string) {
  try {
    const url = new URL(value);
    const parts = url.pathname.replace(/\.git$/, "").split("/").filter(Boolean);
    return url.protocol === "https:" && url.hostname === "github.com" && parts.length === 2 && parts.every((part) => /^[\w.-]+$/.test(part));
  } catch {
    return false;
  }
}
