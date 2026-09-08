"""Read explicitly marked article bodies before generic page extraction."""
from html.parser import HTMLParser


class _ArticleBody(HTMLParser):
    """Keep prose in an article body; omit scripts, menus and related-link lists."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.parts = []
        self.found = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        marked = ('articleBody' in attrs.get('itemprop', '').split()
                  or 'bodytext' in attrs.get('class', '').split())
        active = marked or any(row[1] for row in self.stack)
        furniture = bool(set(attrs.get('class', '').split()) &
                         {'toplist', 'related-posts', 'advertisement', 'ad-container'})
        if marked:
            self.found = True
        if tag in ('p', 'h2', 'h3', 'h4', 'li', 'br') and active:
            self.parts.append('\n')
        if tag not in ('area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input',
                       'link', 'meta', 'param', 'source', 'track', 'wbr'):
            self.stack.append((tag, active, furniture))

    def handle_endtag(self, tag):
        if tag in ('p', 'h2', 'h3', 'h4', 'li'):
            self.parts.append('\n')
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        if not self.stack or not self.stack[-1][1]:
            return
        tags = {row[0] for row in self.stack}
        if any(row[2] for row in self.stack) or tags & {'script', 'style', 'nav', 'aside', 'header', 'footer'}:
            return
        if tags & {'p', 'h2', 'h3', 'h4', 'blockquote', 'pre', 'li'}:
            self.parts.append(data)


def tekst_z_html(body: str) -> str:
    """Prefer publisher-marked prose, including an empty/unavailable body.

    A generic extractor can return thousands of menu characters while ignoring
    the actual article. An empty marked body must reach the fetch failure path,
    rather than being silently replaced with unrelated page furniture.
    """
    import trafilatura
    parser = _ArticleBody()
    parser.feed(body)
    if parser.found:
        lines = [' '.join(line.split()) for line in ''.join(parser.parts).splitlines()]
        return '\n'.join(line for line in lines if line)
    return trafilatura.extract(body, include_comments=False) or ''
