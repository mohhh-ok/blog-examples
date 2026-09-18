// markdown の見出しを木にする。コードフェンス内の "# " は見出しとして扱わない。
export type Node = {
  id: string;
  title: string;
  level: number; // 0 = root
  text: string; // この見出し直下の本文（子見出しの本文は含まない）
  children: Node[];
  url?: string;
};

export function parseMarkdownTree(markdown: string): Node {
  const root: Node = { id: "root", title: "(root)", level: 0, text: "", children: [] };
  const stack: Node[] = [root];
  let inFence = false;
  let seq = 0;
  for (const line of markdown.split("\n")) {
    if (/^\s*(```|~~~)/.test(line)) inFence = !inFence;
    const m = !inFence && /^(#{1,4})\s+(.+?)\s*$/.exec(line);
    if (!m) {
      stack[stack.length - 1]!.text += line + "\n";
      continue;
    }
    const level = m[1]!.length;
    const node: Node = { id: `n${++seq}`, title: m[2]!, level, text: "", children: [] };
    while (stack[stack.length - 1]!.level >= level) stack.pop();
    stack[stack.length - 1]!.children.push(node);
    stack.push(node);
  }
  return root;
}

// 本文からコード・空行・markdown 記法を落として先頭 n 文字を取る（Choice の criteria 用）
export function excerpt(node: Node, chars: number): string {
  const plain = node.text
    .replace(/```[\s\S]*?```/g, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/[`*_>|]/g, "")
    .replace(/\s+/g, " ")
    .trim();
  return plain.slice(0, chars);
}

export function subtreeText(node: Node): string {
  return node.text + node.children.map(subtreeText).join("\n");
}

export function countNodes(node: Node): number {
  return 1 + node.children.reduce((s, c) => s + countNodes(c), 0);
}
