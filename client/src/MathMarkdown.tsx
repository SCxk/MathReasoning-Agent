import { memo, useMemo } from 'react';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import remarkParse from 'remark-parse';
import rehypeKatex from 'rehype-katex';
import { unified } from 'unified';
import { visit } from 'unist-util-visit';
import katex from 'katex';

const mathOptions = { trust: false, strict: 'ignore' as const, maxExpand: 1000, maxSize: 20 };

function boxedContent(source: string): string | null {
  const opening = /^\\boxed\s*\{/.exec(source);
  if (!opening) return null;
  let depth = 1;
  for (let index = opening[0].length; index < source.length; index++) {
    if (source[index] === '\\') { index++; continue; }
    if (source[index] === '{') depth++;
    if (source[index] === '}' && --depth === 0) {
      return index === source.length - 1 ? source.slice(opening[0].length, index) : null;
    }
  }
  return null;
}

function normalizeDelimiters(source: string): string {
  const tree = unified().use(remarkParse).parse(source);
  const protectedRanges: [number, number][] = [];
  visit(tree, node => {
    if (['code', 'inlineCode', 'html'].includes(node.type)
        && node.position?.start.offset !== undefined && node.position.end.offset !== undefined) {
      protectedRanges.push([node.position.start.offset, node.position.end.offset]);
    }
  });
  const convert = (text: string) => text.replace(/\\\[([\s\S]*?)\\\]/g, (_, math: string) => `\n$$\n${math}\n$$\n`)
    .replace(/\\\(([^\n]*?)\\\)/g, (_, math: string) => `$${math}$`);
  let offset = 0, output = '';
  for (const [start, end] of protectedRanges.sort((a, b) => a[0] - b[0])) {
    if (start < offset) continue;
    output += convert(source.slice(offset, start)) + source.slice(start, end);
    offset = end;
  }
  return output + convert(source.slice(offset));
}

export function normalizeMath(source: string): string {
  const body = boxedContent(source.trim());
  if (body !== null) {
    try {
      katex.renderToString(source.trim(), { ...mathOptions, throwOnError: true });
      return `$$\n${source.trim()}\n$$`;
    } catch {
      // Invalid legacy boxes may contain Markdown rather than a single formula.
    }
    const normalizedBody = normalizeDelimiters(body);
    const tree = unified().use(remarkParse).use(remarkMath).parse(normalizedBody);
    let containsMath = false;
    visit(tree, node => { if (node.type === 'math' || node.type === 'inlineMath') containsMath = true; });
    // Older answers wrapped an entire Markdown summary in a math-only box.
    if (containsMath) return normalizedBody;
    return `$$\n${source.trim()}\n$$`;
  }
  return normalizeDelimiters(source);
}

export default memo(function MathMarkdown({ content }: { content: string }) {
  const normalized = useMemo(() => normalizeMath(content), [content]);
  return <div className="markdown">
    <Markdown remarkPlugins={[remarkGfm, remarkMath]}
      rehypePlugins={[[rehypeKatex, { ...mathOptions, throwOnError: false }]]}
      skipHtml components={{
        a: props => <a href={props.href} target="_blank" rel="noopener noreferrer">{props.children}</a>,
        img: props => <span className="muted">{props.alt || '图片'}</span>,
      }}>{normalized}</Markdown>
  </div>;
});
