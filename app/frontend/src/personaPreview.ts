export function personaPreview(content: string, limit = 72): string {
  const normalized = content
    .replace(/^\s*(?:人物資料|Character information)\s*[:：]\s*/u, "")
    .replace(/\s+/gu, " ")
    .trim();
  const characters = Array.from(normalized);
  if (characters.length <= limit) return normalized;
  return `${characters.slice(0, limit).join("")}...`;
}
