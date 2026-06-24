<!-- DEEPINIT:START -->
<!--
Provenance:
 stage: EXTRACT (BLIND re-derivation from code only)
 component: scrapy.selector + scrapy.linkextractors (extraction)
 paths: scrapy/selector/, scrapy/linkextractors/, scrapy/link.py
 inputs: scrapy/selector/{__init__,unified}.py, scrapy/linkextractors/{__init__,lxmlhtml}.py, scrapy/link.py, pyproject.toml
 date: 2026-06-13
-->

# Component: scrapy.selector + scrapy.linkextractors (extraction)

The content-extraction layer: it wraps the third-party `parsel` selector engine
to query response bodies (XPath/CSS) and provides link extractors that walk a
parsed HTML/XML document and emit filtered, normalized `Link` objects.

## Role

- Wraps `parsel.Selector` into Scrapy's `Selector`/`SelectorList`, auto-inferring the selector type (`html`/`xml`/`json`) from the response class and seeding the `base_url` so relative XPath/CSS queries resolve correctly — `scrapy/selector/unified.py:39`.
- Provides `LxmlLinkExtractor` (exported as `LinkExtractor`), which extracts, normalizes-to-absolute, filters (allow/deny regex, domains, extensions, text), and de-duplicates anchor links from a response into `Link` objects — `scrapy/linkextractors/lxmlhtml.py:164` and `scrapy/linkextractors/__init__.py:128`.

## Dependencies (edges)

Outgoing edges to OTHER components in this system:

- → **scrapy.http (Request/Response model)**: `Selector.__init__` branches on `XmlResponse`/`HtmlResponse`/`TextResponse` to pick the selector type and to build a synthetic response from raw text — `scrapy/selector/unified.py:11` (`from scrapy.http import HtmlResponse, TextResponse, XmlResponse`), used at `scrapy/selector/unified.py:23` and `scrapy/selector/unified.py:28`.
- → **scrapy.http (Request/Response model)**: the link extractor consumes `TextResponse` — reads `.selector`, `.url`, `.encoding` and calls `response.xpath(...)` — `scrapy/linkextractors/lxmlhtml.py:141`, `scrapy/linkextractors/lxmlhtml.py:144`, `scrapy/linkextractors/lxmlhtml.py:274`.
- → **scrapy.utils (shared infrastructure)**: `to_bytes` (text→response encoding) and `unique` (link de-dup) from `scrapy.utils.python` — `scrapy/selector/unified.py:12`, `scrapy/linkextractors/lxmlhtml.py:23`.
- → **scrapy.utils (shared infrastructure)**: `get_base_url` from `scrapy.utils.response` — `scrapy/selector/unified.py:13` and `scrapy/linkextractors/lxmlhtml.py:24`.
- → **scrapy.utils (shared infrastructure)**: `object_ref` (the trackref live-instance tracking base class) from `scrapy.utils.trackref` — `scrapy/selector/unified.py:14`.
- → **scrapy.utils (shared infrastructure)**: `arg_to_iter` + `rel_has_nofollow` from `scrapy.utils.misc` — `scrapy/linkextractors/lxmlhtml.py:22`.
- → **scrapy.utils (shared infrastructure)**: `url_has_any_extension` + `url_is_from_any_domain` from `scrapy.utils.url` — `scrapy/linkextractors/lxmlhtml.py:25`.
- → **scrapy item + loader + exporters / scrapy.link (item data layer adjacent — Link model)**: the link extractor constructs and returns `scrapy.link.Link` objects — `scrapy/linkextractors/lxmlhtml.py:20` (`from scrapy.link import Link`), constructed at `scrapy/linkextractors/lxmlhtml.py:133`.
- → external runtime libraries (NOT internal components, recorded for completeness): `parsel` (selector engine, the technology this layer wraps) — `scrapy/selector/unified.py:9`; `lxml.etree` — `scrapy/linkextractors/lxmlhtml.py:15`; `parsel.csstranslator.HTMLTranslator` (CSS→XPath) — `scrapy/linkextractors/lxmlhtml.py:16`; `w3lib.html`/`w3lib.url` (whitespace strip, URL canonicalization/safety) — `scrapy/linkextractors/lxmlhtml.py:17` and `scrapy/linkextractors/lxmlhtml.py:18`. All four are declared dependencies in `pyproject.toml:16` (lxml), `pyproject.toml:18` (parsel), `pyproject.toml:24` (w3lib).

Note (inbound, not an outgoing edge): this component is consumed by **scrapy.spiders** — `CrawlSpider` imports `LinkExtractor` and calls `rule.link_extractor.extract_links(response)` — `scrapy/spiders/crawl.py:18` and `scrapy/spiders/crawl.py:147`; and `Selector` is re-exported at the package top level — `scrapy/__init__.py:12`.

## Data

- No persistence / data-stores owned or read. The layer is purely in-memory and stateless across calls: it parses response bodies into in-memory `Selector` trees and returns lists of `Link` value objects — `scrapy/linkextractors/lxmlhtml.py:139` (returns `list[Link]`). No file, queue, or DB access appears in any of the component's source files.

## Boundary rules

- Selector type is inferred, not assumed: `_st` maps response class → type string (`xml` for `XmlResponse`, else `html`), and an explicit `type=` forces it with no detection — `scrapy/selector/unified.py:21`.
- `response` and `text` are mutually exclusive inputs: passing both raises `ValueError` — `scrapy/selector/unified.py:82`.
- Link normalization order is fixed: strip HTML5 whitespace → `urljoin(base_url,...)` → `process_attr` → `safe_url_string` → `urljoin(response_url,...)`, with bogus links skipped (`ValueError` → `continue`) rather than raising — `scrapy/linkextractors/lxmlhtml.py:113`-`scrapy/linkextractors/lxmlhtml.py:138`.
- Link admission gate (`_link_allowed`) applies the full filter chain in order: valid-scheme → allow_res → deny_res → allow_domains → deny_domains → deny_extensions → restrict_text — `scrapy/linkextractors/lxmlhtml.py:217`.
- Only a fixed set of URL schemes is followable: `{http, https, file, ftp}` — `scrapy/linkextractors/__init__.py:124`.
- A large default extension blocklist (`IGNORED_EXTENSIONS`) is applied unless overridden by `deny_extensions` — `scrapy/linkextractors/__init__.py:18` and `scrapy/linkextractors/lxmlhtml.py:204`.

## Key facts

- `Selector` and `SelectorList` subclass BOTH the parsel class and `object_ref` (so live selector instances are tracked by `scrapy.utils.trackref`) — `scrapy/selector/unified.py:32` and `scrapy/selector/unified.py:39`.
- `Selector` declares `__slots__ = ["response"]` and keeps a back-reference to the originating response — `scrapy/selector/unified.py:71` and `scrapy/selector/unified.py:96`.
- Public link-extractor API is an alias: `LxmlLinkExtractor` is exported as `LinkExtractor` — `scrapy/linkextractors/__init__.py:128`; the lxml.html implementation is the only/default extractor (`__all__` exposes only `IGNORED_EXTENSIONS` and `LinkExtractor`) — `scrapy/linkextractors/__init__.py:130`.
- Two-layer extractor design: `LxmlLinkExtractor` (filtering/config façade) delegates DOM walking to an inner `LxmlParserLinkExtractor` (`self.link_extractor`) — `scrapy/linkextractors/lxmlhtml.py:185`; the parser iterates the lxml document tree via `document.iter(etree.Element)` reaching it through `selector.root` (the "hacky way to get the underlying lxml parsed document") — `scrapy/linkextractors/lxmlhtml.py:95` and `scrapy/linkextractors/lxmlhtml.py:113`.
- `canonicalize=True` reverses the parser's `link_key`: when canonicalize is OFF the extractor canonicalizes the de-dup key (`canonicalized=not canonicalize`) so default behavior still de-dups on canonical URL — `scrapy/linkextractors/lxmlhtml.py:191` and `scrapy/linkextractors/lxmlhtml.py:86`.
- `restrict_css` is converted to XPath at construction via parsel's `HTMLTranslator` and merged into `restrict_xpaths` — `scrapy/linkextractors/lxmlhtml.py:200`; the translator is a class-level singleton — `scrapy/linkextractors/lxmlhtml.py:165`.
- Default scanned tags/attrs are `("a", "area")` / `("href",)` and `unique=True` by default — `scrapy/linkextractors/lxmlhtml.py:174` and `scrapy/linkextractors/lxmlhtml.py:177`.
- `Link` is a slotted value object (`__slots__ = ["fragment","nofollow","text","url"]`) with value-based `__eq__`/`__hash__`, and its constructor type-checks that `url` is `str` — `scrapy/link.py:27`, `scrapy/link.py:40`, `scrapy/link.py:32`.
- XHTML-namespaced tag names are normalized to their local name before tag matching (`_nons`) — `scrapy/linkextractors/lxmlhtml.py:42` used at `scrapy/linkextractors/lxmlhtml.py:96`.
- De-duplication happens twice (per-document inside the parser and once globally across all restrict_xpaths sub-documents) when `unique` is set — `scrapy/linkextractors/lxmlhtml.py:282`.
<!-- DEEPINIT:END -->
