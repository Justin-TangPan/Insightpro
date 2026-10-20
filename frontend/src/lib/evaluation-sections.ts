export function parseEvaluationSections(text: string) {
  const sections = [...text.matchAll(/【([^】]+)】([^【]*)/g)]
    .map((match) => ({ label: match[1].trim(), content: match[2].trim() }))
    .filter((item) => item.content);
  return sections.length > 1 ? sections : [];
}
