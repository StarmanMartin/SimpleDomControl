/**
 * Small Markdown renderer for the answers of the AI assistant.
 *
 * The text comes from a language model and may repeat page content, so it is untrusted: the renderer only creates
 * elements and text nodes (never ``innerHTML``). HTML in the text stays visible as text, and links are only created
 * for http(s), mailto and same-site paths.
 *
 * Supported: fenced code blocks, headings, lists (nested by indentation), blockquotes, GFM tables, horizontal rules,
 * paragraphs with line breaks; inline code, bold, italic, strikethrough, links and bare URLs. Incomplete syntax (e.g.
 * while an answer is still streaming) is shown as plain text.
 */

const FENCE_RE = /^\s{0,3}(`{3,}|~{3,})\s*([\w+#.-]*)\s*$/;
const HEADING_RE = /^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$/;
const HR_RE = /^\s{0,3}([-*_])(\s*\1){2,}\s*$/;
const QUOTE_RE = /^\s{0,3}>\s?/;
const LIST_RE = /^(\s*)([-*+]|\d{1,9}[.)])\s+(.*)$/;
const TABLE_SEPARATOR_RE = /^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?\s*$/;

// Inline syntax, tried at every position; at the same position the first alternative wins (bold before italic).
// Underscores only count at word boundaries, so names like sdc_user_nav stay intact.
// Content of an emphasis: starts and ends with a non-space character (a single character is enough)
const EMPHASIS = String.raw`(\S(?:.*?\S)?)`;
const INLINE_RE = new RegExp([
    /(`+)(.+?)\1(?!`)/.source,                                   // 1, 2: code
    /\[([^\]]+)\]\(\s*([^()\s]*(?:\([^()\s]*\)[^()\s]*)*)\s*\)/.source,  // 3, 4: link
    /(https?:\/\/[^\s<>]*[^\s<>.,;:!?)\]'"*_~`])/.source,          // 5: bare URL
    String.raw`\*\*${EMPHASIS}\*\*`,                              // 6: bold
    String.raw`(?<!\w)__${EMPHASIS}__(?!\w)`,                      // 7: bold
    String.raw`~~${EMPHASIS}~~`,                                  // 8: strikethrough
    // Italic content must not end with "*", so "*a **b** c*" is italic around bold
    String.raw`\*(?!\*)([^\s*](?:.*?[^\s*])?)\*(?!\*)`,             // 9: italic
    String.raw`(?<!\w)_(?!_)${EMPHASIS}_(?!\w)`,                   // 10: italic
].join('|'), 'g');


/**
 * @param {string} text Markdown
 * @returns {DocumentFragment}
 */
export function renderMarkdown(text) {
    const lines = String(text ?? '').replace(/\r\n?/g, '\n').split('\n');
    const fragment = document.createDocumentFragment();
    let i = 0;
    while (i < lines.length) {
        const line = lines[i];
        if (!line.trim()) {
            i++;
            continue;
        }
        let m;
        if ((m = line.match(FENCE_RE))) {
            const code = [];
            const fence = m[1];
            i++;
            // An unclosed fence (still streaming) takes the rest of the text
            while (i < lines.length && !lines[i].trim().startsWith(fence)) {
                code.push(lines[i++]);
            }
            i++;
            fragment.append(codeBlock(code.join('\n'), m[2]));
        } else if ((m = line.match(HEADING_RE))) {
            const heading = el('div', `ai-md-heading ai-md-h${m[1].length}`);
            appendInline(heading, m[2]);
            fragment.append(heading);
            i++;
        } else if (HR_RE.test(line)) {
            // Before lists: "* * *" is a rule, not a list item
            fragment.append(el('hr'));
            i++;
        } else if (isTableStart(lines, i)) {
            i = table(lines, i, fragment);
        } else if (QUOTE_RE.test(line)) {
            const quoted = [];
            while (i < lines.length && QUOTE_RE.test(lines[i])) {
                quoted.push(lines[i++].replace(QUOTE_RE, ''));
            }
            const quote = el('blockquote');
            quote.append(renderMarkdown(quoted.join('\n')));
            fragment.append(quote);
        } else if (LIST_RE.test(line)) {
            i = list(lines, i, fragment);
        } else {
            const paragraph = el('p');
            let first = true;
            while (i < lines.length && lines[i].trim() && (first || !isBlockStart(lines, i))) {
                if (!first) {
                    paragraph.append(el('br'));
                }
                appendInline(paragraph, lines[i++].trim());
                first = false;
            }
            fragment.append(paragraph);
        }
    }
    return fragment;
}

function el(tag, className = null) {
    const element = document.createElement(tag);
    if (className) {
        element.className = className;
    }
    return element;
}

function indentOf(line) {
    return line.match(/^\s*/)[0].replace(/\t/g, '    ').length;
}

function isTableStart(lines, i) {
    return lines[i].includes('|') && i + 1 < lines.length && lines[i + 1].includes('-')
        && TABLE_SEPARATOR_RE.test(lines[i + 1]);
}

function isBlockStart(lines, i) {
    const line = lines[i];
    return FENCE_RE.test(line) || HEADING_RE.test(line) || HR_RE.test(line) || QUOTE_RE.test(line)
        || LIST_RE.test(line) || isTableStart(lines, i);
}

function codeBlock(code, language) {
    const pre = el('pre', 'ai-md-code');
    const element = el('code');
    if (language) {
        element.dataset.language = language;
    }
    element.textContent = code;
    pre.append(element);
    return pre;
}

/** Parses the list starting at ``lines[i]``; deeper indented lines form nested blocks of the previous item. */
function list(lines, i, fragment) {
    const first = lines[i].match(LIST_RE);
    const base = indentOf(first[1]);
    const ordered = /\d/.test(first[2]);
    const element = el(ordered ? 'ol' : 'ul');
    if (ordered && parseInt(first[2], 10) !== 1) {
        element.start = parseInt(first[2], 10);
    }
    let item = null;
    while (i < lines.length) {
        const line = lines[i];
        if (!line.trim()) {
            // A blank line only continues the list if more of it follows
            const next = lines.slice(i + 1).find((l) => l.trim());
            if (next !== undefined && indentOf(next) >= base && (LIST_RE.test(next) || indentOf(next) > base)) {
                i++;
                continue;
            }
            break;
        }
        const m = line.match(LIST_RE);
        const indent = indentOf(line);
        if (m && indent <= base + 1 && /\d/.test(m[2]) === ordered) {
            item = el('li');
            appendInline(item, m[3]);
            element.append(item);
            i++;
        } else if (item && indent > base + 1) {
            const nested = [];
            while (i < lines.length && (!lines[i].trim() || indentOf(lines[i]) > base + 1)) {
                nested.push(lines[i++]);
            }
            const minIndent = Math.min(...nested.filter((l) => l.trim()).map(indentOf));
            item.append(renderMarkdown(nested.map((l) => l.replace(/\t/g, '    ').slice(minIndent)).join('\n')));
        } else if (item && !m && indent > base) {
            item.append(el('br'));
            appendInline(item, line.trim());
            i++;
        } else {
            break;
        }
    }
    fragment.append(element);
    return i;
}

function tableCells(line) {
    let row = line.trim();
    if (row.startsWith('|')) row = row.slice(1);
    if (row.endsWith('|') && !row.endsWith('\\|')) row = row.slice(0, -1);
    return row.split(/(?<!\\)\|/).map((cell) => cell.trim().replace(/\\\|/g, '|'));
}

function table(lines, i, fragment) {
    const header = tableCells(lines[i]);
    const align = tableCells(lines[i + 1]).map((c) =>
        c.startsWith(':') && c.endsWith(':') ? 'center' : (c.endsWith(':') ? 'right' : (c.startsWith(':') ? 'left' : '')));
    const wrapper = el('div', 'ai-md-table');
    const element = el('table');
    const thead = el('thead');
    const tbody = el('tbody');
    const row = (cells, tag) => {
        const tr = el('tr');
        header.forEach((_, col) => {
            const cell = el(tag);
            if (align[col]) {
                cell.style.textAlign = align[col];
            }
            appendInline(cell, cells[col] ?? '');
            tr.append(cell);
        });
        return tr;
    };
    thead.append(row(header, 'th'));
    i += 2;
    while (i < lines.length && lines[i].trim() && lines[i].includes('|')) {
        tbody.append(row(tableCells(lines[i++]), 'td'));
    }
    element.append(thead, tbody);
    wrapper.append(element);
    fragment.append(wrapper);
    return i;
}

/** Same-site paths and http(s)/mailto URLs; null for everything else (e.g. javascript:). */
function safeHref(url) {
    if (/^(https?:|mailto:)/i.test(url)) {
        return url;
    }
    if (url.startsWith('/') && !url.startsWith('//')) {
        return url;
    }
    return null;
}

function link(href, content) {
    const a = el('a');
    a.href = href;
    a.rel = 'noopener noreferrer';
    let external = false;
    try {
        external = new URL(href, window.location.href).origin !== window.location.origin;
    } catch (e) {
        external = true;
    }
    if (external) {
        a.target = '_blank';
    } else if (href.startsWith('/~')) {
        // SDC paths are opened by the sdc-navigator without reloading the page (see the assistant controller)
        a.classList.add('ai-md-nav');
    }
    if (typeof content === 'string') {
        appendInline(a, content);
    } else {
        a.append(content);
    }
    return a;
}

/** Appends ``text`` with inline Markdown to ``parent``. */
export function appendInline(parent, text) {
    let last = 0;
    // matchAll works on a copy of the regex, so the recursive calls below don't disturb this loop
    for (const m of text.matchAll(INLINE_RE)) {
        parent.append(document.createTextNode(text.slice(last, m.index)));
        last = m.index + m[0].length;
        if (m[2] !== undefined) {
            const code = el('code');
            code.textContent = m[2].trim() || m[2];
            parent.append(code);
        } else if (m[3] !== undefined) {
            const href = safeHref(m[4] || '');
            parent.append(href ? link(href, m[3]) : document.createTextNode(m[0]));
        } else if (m[5] !== undefined) {
            parent.append(link(m[5], document.createTextNode(m[5])));
        } else {
            const [tag, inner] = m[6] !== undefined || m[7] !== undefined ? ['strong', m[6] ?? m[7]]
                : (m[8] !== undefined ? ['del', m[8]] : ['em', m[9] ?? m[10]]);
            const element = el(tag);
            appendInline(element, inner);
            parent.append(element);
        }
    }
    parent.append(document.createTextNode(text.slice(last)));
}
