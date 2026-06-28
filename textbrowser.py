#!/usr/bin/env python3
"""A minimal text web browser.

Fetches a web page, strips all HTML markup (and non-content like <script>,
<style>, <head>), and shows just the readable words. Links are marked
visually, made clickable, and numbered with a reference list at the bottom.

Standard library only -- no third-party dependencies.

Usage:
    python3 textbrowser.py [url]
"""

import sys
import ssl
import urllib.request
import urllib.error
from urllib.parse import urljoin, urlsplit
from html.parser import HTMLParser

import tkinter as tk
from tkinter import ttk, font as tkfont


USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) TextBrowser/1.0 Safari/537.36"
)

# Tags whose entire contents we drop -- they are never readable page text.
SKIP_TAGS = {"script", "style", "head", "noscript", "title", "template"}

# Block-level tags that should be separated by blank lines for readability.
BLOCK_TAGS = {
    "p", "div", "section", "article", "header", "footer", "nav", "main",
    "aside", "ul", "ol", "table", "tr", "blockquote", "pre", "form",
    "figure", "figcaption", "hr",
    "h1", "h2", "h3", "h4", "h5", "h6",
}


class LinkExtractor(HTMLParser):
    """Turn HTML into a list of segments plus an ordered list of links.

    Each segment is one of:
        ("text", str)
        ("link", {"text": str, "url": str, "number": int})

    ``links`` is the ordered list of {"number", "url", "text"} dicts used to
    build the reference list shown at the bottom of the page.
    """

    def __init__(self, base_url=""):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.segments = []      # list of ("text"|"link", value)
        self.links = []         # ordered link reference list
        self._skip_depth = 0    # >0 while inside a SKIP_TAGS element
        self._link_href = None  # current <a> href, or None
        self._link_text = []    # buffered anchor text pieces

    # -- helpers ---------------------------------------------------------
    def _emit_text(self, text):
        if not text:
            return
        if self.segments and self.segments[-1][0] == "text":
            self.segments[-1] = ("text", self.segments[-1][1] + text)
        else:
            self.segments.append(("text", text))

    def _emit_break(self, blank=False):
        """Append a newline (or blank line) to the running text."""
        sep = "\n\n" if blank else "\n"
        if self.segments and self.segments[-1][0] == "text":
            cur = self.segments[-1][1]
            # Avoid piling up more than two consecutive newlines.
            trailing = len(cur) - len(cur.rstrip("\n"))
            need = 2 if blank else 1
            if trailing < need:
                self.segments[-1] = ("text", cur + "\n" * (need - trailing))
        else:
            self.segments.append(("text", sep))

    # -- HTMLParser hooks -----------------------------------------------
    def handle_starttag(self, tag, attrs):
        if tag in SKIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return

        if tag == "br":
            self._emit_break(blank=False)
            return
        if tag == "li":
            self._emit_break(blank=False)
            self._emit_text("• ")  # bullet
            return
        if tag in BLOCK_TAGS:
            self._emit_break(blank=True)
            return
        if tag == "a":
            href = dict(attrs).get("href")
            if href and not href.startswith(("javascript:", "#")):
                self._link_href = urljoin(self.base_url, href)
                self._link_text = []

    def handle_endtag(self, tag):
        if tag in SKIP_TAGS:
            if self._skip_depth:
                self._skip_depth -= 1
            return
        if self._skip_depth:
            return

        if tag == "a" and self._link_href is not None:
            text = " ".join("".join(self._link_text).split())
            if text:
                number = len(self.links) + 1
                self.links.append(
                    {"number": number, "url": self._link_href, "text": text}
                )
                self.segments.append(
                    ("link", {"text": text, "url": self._link_href,
                              "number": number})
                )
            self._link_href = None
            self._link_text = []
            return
        if tag in BLOCK_TAGS:
            self._emit_break(blank=True)

    def handle_data(self, data):
        if self._skip_depth:
            return
        # Collapse runs of whitespace into single spaces.
        collapsed = " ".join(data.split())
        if not collapsed:
            # Whitespace-only data: keep a single separating space.
            if data:
                self._maybe_space()
            return
        # Keep a leading/trailing space if the original had surrounding space.
        if data[:1].isspace():
            collapsed = " " + collapsed
        if data[-1:].isspace():
            collapsed = collapsed + " "

        if self._link_href is not None:
            self._link_text.append(collapsed)
        else:
            self._emit_text(collapsed)

    def _maybe_space(self):
        if self._link_href is not None:
            if self._link_text and not self._link_text[-1].endswith(" "):
                self._link_text.append(" ")
        elif self.segments and self.segments[-1][0] == "text":
            cur = self.segments[-1][1]
            if cur and not cur.endswith((" ", "\n")):
                self.segments[-1] = ("text", cur + " ")


def parse_html(html, base_url=""):
    """Parse *html* and return (segments, links)."""
    p = LinkExtractor(base_url=base_url)
    p.feed(html)
    p.close()
    return p.segments, p.links


def fetch(url):
    """Fetch *url* and return (html_text, final_url).

    Raises a RuntimeError with a human-readable message on failure.
    """
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=20, context=ctx) as resp:
            final_url = resp.geturl()
            ctype = resp.headers.get_content_type()
            charset = resp.headers.get_content_charset() or "utf-8"
            raw = resp.read()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP error {e.code}: {e.reason}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not reach site: {e.reason}") from e
    except Exception as e:  # noqa: BLE001 - surface anything else readably
        raise RuntimeError(f"Failed to load page: {e}") from e

    if ctype and not (ctype.startswith("text/") or ctype.endswith("xml")):
        raise RuntimeError(f"Unsupported content type: {ctype}")

    try:
        return raw.decode(charset, errors="replace"), final_url
    except LookupError:
        return raw.decode("utf-8", errors="replace"), final_url


def normalize_url(url):
    """Add a scheme if the user typed a bare host/path."""
    url = url.strip()
    if not url:
        return url
    if not urlsplit(url).scheme:
        url = "https://" + url
    return url


class TextBrowser(tk.Tk):
    def __init__(self, start_url=None):
        super().__init__()
        self.title("Text Web Browser")
        self.geometry("820x640")

        self.history = []        # stack of previously loaded URLs
        self.current_url = None

        self._build_widgets()

        if start_url:
            self.url_var.set(start_url)
            self.load(normalize_url(start_url))
        else:
            self._show_message(
                "Enter a URL above and press Go (or Enter) to start browsing."
            )

    # -- UI construction -------------------------------------------------
    def _build_widgets(self):
        bar = ttk.Frame(self, padding=(8, 6))
        bar.pack(side=tk.TOP, fill=tk.X)

        self.back_btn = ttk.Button(bar, text="← Back", width=8,
                                   command=self.go_back, state=tk.DISABLED)
        self.back_btn.pack(side=tk.LEFT)

        self.url_var = tk.StringVar()
        entry = ttk.Entry(bar, textvariable=self.url_var)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)
        entry.bind("<Return>", lambda _e: self.go())
        self.entry = entry

        ttk.Button(bar, text="Go", width=6, command=self.go).pack(side=tk.LEFT)

        wrap = ttk.Frame(self)
        wrap.pack(side=tk.BOTH, expand=True)

        base = tkfont.nametofont("TkTextFont")
        self.text = tk.Text(
            wrap, wrap=tk.WORD, padx=14, pady=12, spacing3=2,
            font=(base.actual("family"), 12), cursor="arrow",
            background="#fafafa", foreground="#1a1a1a",
        )
        scroll = ttk.Scrollbar(wrap, command=self.text.yview)
        self.text.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Styling for link runs.
        link_font = tkfont.Font(
            family=base.actual("family"), size=12, underline=True
        )
        self.text.tag_configure(
            "link", foreground="#1565c0", font=link_font
        )
        self.text.tag_configure(
            "ref", foreground="#1565c0", font=link_font
        )
        self.text.tag_configure("status", foreground="#888888")
        self.text.configure(state=tk.DISABLED)

    # -- navigation ------------------------------------------------------
    def go(self):
        url = normalize_url(self.url_var.get())
        if url:
            self.load(url)

    def go_back(self):
        if self.history:
            prev = self.history.pop()
            self.back_btn.configure(
                state=(tk.NORMAL if self.history else tk.DISABLED)
            )
            self._load(prev, record_history=False)

    def navigate(self, url):
        """Follow a link, remembering the current page for Back."""
        if self.current_url:
            self.history.append(self.current_url)
            self.back_btn.configure(state=tk.NORMAL)
        self._load(url, record_history=False)

    def load(self, url):
        """Load a URL typed/entered by the user (also recorded in history)."""
        if self.current_url and self.current_url != url:
            self.history.append(self.current_url)
            self.back_btn.configure(state=tk.NORMAL)
        self._load(url, record_history=False)

    def _load(self, url, record_history=True):
        self.url_var.set(url)
        self._show_message(f"Loading {url} ...")
        self.update_idletasks()
        try:
            html, final_url = fetch(url)
        except RuntimeError as e:
            self._show_message(str(e), status=True)
            self.current_url = url
            return
        self.current_url = final_url
        self.url_var.set(final_url)
        segments, links = parse_html(html, base_url=final_url)
        self._render(segments, links)

    # -- rendering -------------------------------------------------------
    def _show_message(self, msg, status=False):
        self.text.configure(state=tk.NORMAL)
        self.text.delete("1.0", tk.END)
        self.text.insert(tk.END, msg, ("status",) if status else ())
        self.text.configure(state=tk.DISABLED)

    def _render(self, segments, links):
        self.text.configure(state=tk.NORMAL)
        self.text.delete("1.0", tk.END)

        for kind, value in segments:
            if kind == "text":
                self.text.insert(tk.END, value)
            else:  # link
                self._insert_link(value["text"], value["url"])
                self.text.insert(tk.END, f" [{value['number']}]")

        if links:
            self.text.insert(tk.END, "\n\n")
            self.text.insert(tk.END, "─" * 40 + "\n", ("status",))
            self.text.insert(tk.END, "Links\n", ("status",))
            for link in links:
                self.text.insert(tk.END, f"[{link['number']}] ")
                self._insert_link(link["url"], link["url"], tag="ref")
                self.text.insert(tk.END, "\n")

        self.text.configure(state=tk.DISABLED)
        self.text.yview_moveto(0.0)

    def _insert_link(self, label, url, tag="link"):
        """Insert *label* as a clickable run pointing at *url*."""
        unique = f"{tag}-{len(self.text.tag_names())}-{abs(hash((label, url)))}"
        self.text.insert(tk.END, label, (tag, unique))
        self.text.tag_bind(unique, "<Button-1>",
                           lambda _e, u=url: self.navigate(u))
        self.text.tag_bind(unique, "<Enter>",
                           lambda _e: self.text.configure(cursor="hand2"))
        self.text.tag_bind(unique, "<Leave>",
                           lambda _e: self.text.configure(cursor="arrow"))


def main():
    start = sys.argv[1] if len(sys.argv) > 1 else None
    if start:
        start = normalize_url(start)
    app = TextBrowser(start_url=start)
    app.mainloop()


if __name__ == "__main__":
    main()
