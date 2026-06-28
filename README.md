# Text Web Browser

A tiny, no-frills text web browser. It fetches a web page, strips out all the
HTML markup (and non-content like `<script>`, `<style>`, and `<head>`/meta), and
shows you just the readable words. Links stay usable: they're highlighted and
clickable in the text, numbered with a `[n]` marker, and listed in full at the
bottom of the page. Click a link to follow it, and use **Back** to return.

It's a small desktop app built entirely on the Python **standard library** —
nothing to `pip install`.

## Requirements

- Python 3.7+
- Tkinter (bundled with most Python installs; on some Linux distros install it
  with e.g. `sudo apt install python3-tk`)

## Run it

```sh
python3 textbrowser.py                 # opens with an empty URL bar
python3 textbrowser.py example.com     # opens straight to a page
python3 textbrowser.py https://news.ycombinator.com
```

Then:

- Type a URL in the bar and press **Enter** or click **Go**.
  (A bare host like `example.com` is assumed to be `https://`.)
- Click any highlighted link in the text to follow it.
- Click **← Back** to return to the previous page.

## How it works

- **Fetch:** `urllib.request` (handles HTTPS) with a browser-like `User-Agent`.
- **Strip:** an `html.parser.HTMLParser` subclass drops script/style/head
  content, collapses whitespace, and adds spacing around block elements so the
  text stays readable.
- **Links:** every `<a href>` is resolved to an absolute URL, numbered, and
  rendered as a clickable run; the full list is appended at the bottom.
- **Display:** a read-only Tkinter `Text` widget with a URL bar and Back button.

## Limitations

It's intentionally minimal — no JavaScript, no CSS/layout, no images, no forms.
Pages that render entirely via JavaScript will show little or no text.
