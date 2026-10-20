export function radarMarkerPositions(items: { category: string }[], categories: string[]) {
  const counts = new Map<string, number>();
  return items.map(item => {
    const categoryIndex = categories.indexOf(item.category);
    if (categoryIndex < 0) return null;
    const slot = counts.get(item.category) ?? 0;
    counts.set(item.category, slot + 1);
    const angle = -Math.PI / 2 + categoryIndex * 2 * Math.PI / categories.length + (slot % 2 ? 0.14 : -0.14);
    const radius = 72 + Math.floor(slot / 2) * 27;
    return { x: Math.cos(angle) * radius, y: Math.sin(angle) * radius };
  });
}
