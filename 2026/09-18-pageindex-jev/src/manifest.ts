// 目録（manifest）の仕様と、ページを目録作成用の入力テキストにする関数。
import type { Node } from "./tree";

export const MANIFEST_SPEC = `You index technical documentation for a retrieval router. The router reads only your manifests to decide whether the answer to a user's question is inside a page or section, so a manifest must be an exhaustive inventory, not a prose summary. Prefer coverage over brevity; never add anything that is not in the text.

For the page as a whole and for each [[SECTION i: heading]] block, write a manifest as terse bullet lines covering:
- topics and tasks covered
- every named identifier: functions, methods, options, config keys, CLI flags, environment variables, types, error messages (verbatim)
- concrete values: defaults, limits, versions, numbers, file paths
- caveats, platform/runtime conditions, "not supported" statements
- 3 to 6 questions this text answers, phrased as a user would ask

Page manifest: 80-200 words. Section manifest: 60-200 words depending on the section's size.`;

export const subtreeText = (n: Node): string => n.text + n.children.map((c) => `\n\n### ${c.title}\n${subtreeText(c)}`).join("");

export function pageDocument(page: Node): { text: string; sections: Node[] } {
  const sections = page.children.filter((c) => c.level === 2);
  let text = `# ${page.title}\n${page.text.trim()}\n`;
  sections.forEach((s, i) => (text += `\n\n[[SECTION ${i}: ${s.title}]]\n${subtreeText(s).trim()}\n`));
  return { text, sections };
}
