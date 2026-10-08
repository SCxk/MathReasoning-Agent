import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import MathMarkdown, { normalizeMath } from './MathMarkdown';

describe('math formats', () => {
  it('keeps dollar math and normalizes bare boxed results', () => {
    expect(normalizeMath('$x=2$')).toBe('$x=2$');
    expect(normalizeMath('\\boxed{\\frac{1}{2}}')).toBe('$$\n\\boxed{\\frac{1}{2}}\n$$');
  });
  it('handles inline and display LaTeX delimiters', () => {
    expect(normalizeMath('结果 \\(x=2\\)')).toBe('结果 $x=2$');
    expect(normalizeMath('证明：\\[x^2+y^2=z^2\\]')).toContain('$$\nx^2+y^2=z^2\n$$');
  });
  it('does not rewrite code blocks or inline code', () => {
    const code = '```latex\n\\[x=2\\]\n```\n`\\(x\\)`\n外部 \\(y\\)';
    expect(normalizeMath(code)).toBe('```latex\n\\[x=2\\]\n```\n`\\(x\\)`\n外部 $y$');
  });
  it.each([
    '\\boxed{1. $u=4$; 2. $(a,b)$; 3. the bound is $q$}',
    '\\boxed{1. $u=\\frac{4}{7}$; 2. $\\{a,b\\}$}',
    '\\boxed{1. \\(u=4\\); 2. \\(v=5\\)}',
    '\\boxed{1. $u=4$\n\n2. $v=5$}',
  ])('repairs a whole legacy Markdown answer wrapped as math: %s', source => {
    const normalized = normalizeMath(source);
    expect(normalized).not.toContain('\\boxed');
    const html = renderToStaticMarkup(createElement(MathMarkdown, { content: source }));
    expect(html).toContain('class="katex"');
    expect(html).not.toContain('katex-error');
  });
  it.each(['\\boxed{\\frac{4}{7}}', '\\boxed{\\text{Price \\$12}}', '\\boxed{\\text{$x$}}', '\\boxed{\\boxed{4}}'])('keeps valid formula boxes: %s', source => {
    expect(normalizeMath(source)).toContain(source);
    const html = renderToStaticMarkup(createElement(MathMarkdown, { content: source }));
    expect(html).not.toContain('katex-error');
  });
  it('does not remove unbalanced or partial boxes, or rewrite code examples', () => {
    expect(normalizeMath('\\boxed{a $u=4$')).toContain('\\boxed');
    expect(normalizeMath('\\boxed{a $u=4$} trailing')).toContain('\\boxed');
    const code = '```latex\n\\boxed{1. $u=4$}\n```\n`\\boxed{$v$}`';
    expect(normalizeMath(code)).toBe(code);
  });
  it.each(['$\\frac{1}{2}$', '$$\\int_0^1 x^2 dx$$', '\\boxed{2}', '\\(x=2\\)', '\\[x=2\\]'])('renders %s with KaTeX', source => {
    const html = renderToStaticMarkup(createElement(MathMarkdown, { content: source }));
    expect(html).toContain('class="katex"');
    expect(html).toContain('<math');
  });
});
describe('untrusted answer rendering', () => {
  it('does not execute raw HTML or load remote images', () => {
    const html = renderToStaticMarkup(createElement(MathMarkdown, { content: '<script>window.injected=1</script>\n\n![remote](https://private.invalid/track)' }));
    expect(html).not.toContain('<script');
    expect(html).not.toContain('<img');
    expect(html).not.toContain('https://private.invalid');
  });
  it('blocks script links and trusted KaTeX HTML commands', () => {
    const html = renderToStaticMarkup(createElement(MathMarkdown, { content: '[bad](javascript:alert(1))\n\n$\\htmlClass{injected}{x}$' }));
    expect(html).not.toContain('href="javascript:');
    expect(html).not.toContain('class="injected"');
  });
  it('keeps code and GFM tables', () => {
    const html = renderToStaticMarkup(createElement(MathMarkdown, { content: '| x | y |\n|---|---|\n| 1 | 2 |\n\n```python\nx=1\n```' }));
    expect(html).toContain('<table>');
    expect(html).toContain('language-python');
  });
});
