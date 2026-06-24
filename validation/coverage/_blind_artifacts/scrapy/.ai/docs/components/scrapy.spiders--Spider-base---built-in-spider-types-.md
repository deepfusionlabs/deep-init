<!-- DEEPINIT:START -->
<!--
provenance:
 stage: extract (BLIND re-derivation from code only)
 component: scrapy.spiders (Spider base + built-in spider types)
 path: scrapy/spiders/
 run: p5-mirror-blind
 inputs: scrapy/spiders/__init__.py, scrapy/spiders/crawl.py, scrapy/spiders/feed.py, scrapy/spiders/sitemap.py, pyproject.toml, scrapy/signals.py, scrapy/core/scraper.py, scrapy/core/spidermw.py, scrapy/__init__.py, scrapy/http/__init__.py, scrapy/contracts/__init__.py
 date: 2026-06-13
 doc_in_inputs: false
-->

# Component: scrapy.spiders (Spider base + built-in spider types)

## Role

- The user-facing extension-point package: it defines the `Spider` base class that "any spider must subclass" plus the four built-in specializations (`CrawlSpider`, `XMLFeedSpider`, `CSVFeedSpider`, `SitemapSpider`); user spiders supply `name`/`start_urls` and override `parse`, and the package translates those into the request/callback iterators the framework core drives — `scrapy/spiders/__init__.py:31-37`.

## Dependencies (edges)

- → scrapy.http (Request/Response model): imports `Request`, `Response` for `start` request generation and callback signatures — `scrapy/spiders/__init__.py:13`; `crawl.py` additionally imports `HtmlResponse` — `scrapy/spiders/crawl.py:16`; `feed.py` imports `TextResponse` — `scrapy/spiders/feed.py:13`; `sitemap.py` imports `XmlResponse` — `scrapy/spiders/sitemap.py:10`.
- → scrapy signals + middleware base + addons (extensibility core): imports the `signals` module and connects `self.close` to `spider_closed` — `scrapy/spiders/__init__.py:12,80` (target signal sentinel defined at `scrapy/signals.py:13`).
- → scrapy.utils (shared infrastructure): `object_ref` base + `url_is_from_spider` — `scrapy/spiders/__init__.py:14-15`; `collect_asyncgen`, `method_is_overridden`, `global_object_name`, `iterate_spider_output` — `scrapy/spiders/crawl.py:20-23`; `csviter`, `xmliter_lxml`, `iterate_spider_output` — `scrapy/spiders/feed.py:16-17`; `_DecompressionMaxSizeExceeded`, `gunzip`, `gzip_magic_number`, `Sitemap`, `sitemap_urls_from_robots` — `scrapy/spiders/sitemap.py:12-14`.
- → scrapy.crawler (Crawler lifecycle): `from_crawler(crawler)` receives the `Crawler`, stores it, and reads `crawler.settings` — `scrapy/spiders/__init__.py:72-80`; `CrawlSpider.from_crawler` reads `crawler.settings.getbool("CRAWLSPIDER_FOLLOW_LINKS")` — `scrapy/spiders/crawl.py:221-223`; `SitemapSpider.from_crawler` reads `DOWNLOAD_MAXSIZE`/`DOWNLOAD_WARNSIZE` — `scrapy/spiders/sitemap.py:37-44`.
- → scrapy.settings (configuration system): typed `BaseSettings` stored as `self.settings`; `update_settings` calls `settings.setdict(custom_settings, priority="spider")` — `scrapy/spiders/__init__.py:79,150-151`.
- → scrapy.selector + scrapy.linkextractors (extraction): `CrawlSpider` imports `Link`, `LinkExtractor` and builds a module-level `_default_link_extractor = LinkExtractor` — `scrapy/spiders/crawl.py:17-18,60`; `XMLFeedSpider` imports `Selector` and builds `Selector(response, type="xml"|"html")` — `scrapy/spiders/feed.py:14,87,93`.
- → scrapy.exceptions (extensibility core): `ScrapyDeprecationWarning` — `scrapy/spiders/crawl.py:15`; `NotConfigured`, `NotSupported` — `scrapy/spiders/feed.py:12`.
- (intra-component) `crawl.py`, `feed.py`, `sitemap.py` all subclass `Spider` from this same package — `scrapy/spiders/crawl.py:19,98`; `scrapy/spiders/feed.py:15,23,111`; `scrapy/spiders/sitemap.py:11,26`.
- CONSUMED BY scrapy.core (inbound, verified from the consumer side): the scraper uses `self.crawler.spider._parse` as the default callback — `scrapy/core/scraper.py:318`; the spider-middleware runner pulls the start iterator via `self._spider.start` — `scrapy/core/spidermw.py:246`.

## Data

- No persistent/external data store is owned or read by this component. State is in-memory spider instance attributes only: `start_urls` (`scrapy/spiders/__init__.py:43,52`), `CrawlSpider._rules`/`_follow_links` (`scrapy/spiders/crawl.py:100-101,213-218`), `SitemapSpider._cbs`/`_follow` compiled regexes (`scrapy/spiders/sitemap.py:49-54`).
- It only consumes HTTP `Response` bodies passed in by the core (e.g. `response.body`, `response.meta`) — `scrapy/spiders/sitemap.py:71,124,127`; `scrapy/spiders/crawl.py:137,156`.

## Boundary rules

- Public-API boundary: `Spider` (and the built-ins) are re-exported at the top-level `scrapy` package — `from scrapy.spiders import Spider` / `"Spider"` in `__all__` — `scrapy/__init__.py:13,21`; the package's own `__all__` exports the six spider classes — `scrapy/spiders/__init__.py:173-180`.
- Framework callback contract: the core calls the private `_parse` indirection (not `parse` directly); `Spider._parse` delegates to `parse` — `scrapy/spiders/__init__.py:137-138` — and `CrawlSpider`/feed/sitemap subclasses override `_parse` to inject rule/feed/sitemap dispatch — `scrapy/spiders/crawl.py:116-122`; `scrapy/spiders/feed.py:74-99,155-161`. This is the layer seam the scraper binds to at `scrapy/core/scraper.py:318`.
- Layering inversion forbidden by the import set: spiders import the http/settings/utils/selector/linkextractors layers but never import `scrapy.core.*` at runtime (the only core coupling is inbound, from the consumer side) — confirmed by the import lists at `scrapy/spiders/__init__.py:12-28`, `crawl.py:15-34`, `feed.py:12-17`, `sitemap.py:10-21`.
- Lifecycle ownership stays with the Crawler: spiders never construct their own `Crawler`; they only receive it via `from_crawler` and register a teardown signal handler — `scrapy/spiders/__init__.py:72-80`.

## Key facts

- Async-iterator start contract (tech choice): `start` is an `async def` yielding `Request`/items via an `AsyncIterator` (`.. versionadded:: 2.13`); the default reads `start_urls` and yields `Request(url, dont_filter=True)` — `scrapy/spiders/__init__.py:82-135`.
- Circular-import workaround invariant: `Spider.logger` imports `SpiderLoggerAdapter` inside the property body with a `# circular import` note rather than at module top — `scrapy/spiders/__init__.py:54-60`.
- `parse` is undefined-by-default and raises `NotImplementedError` at call time (typed as `CallbackT` only under `TYPE_CHECKING`) — `scrapy/spiders/__init__.py:140-147`.
- Mandatory `name`: construction raises `ValueError("... must have a name")` if neither passed nor class-set — `scrapy/spiders/__init__.py:45-49`.
- `from_crawler` is the canonical factory and wires `_set_crawler`, which connects `close`→`spider_closed`; `close` is a static dispatcher that calls a spider's optional `closed(reason)` hook — `scrapy/spiders/__init__.py:71-80,157-162`.
- CrawlSpider rule engine: `Rule` holds a `LinkExtractor` + callback/errback/process_links/process_request, `_compile` resolves string method-names against the spider, and `_compile_rules` deep-copies each `rule` into `self._rules` so per-instance compilation never mutates the class-level `rules` tuple — `scrapy/spiders/crawl.py:63-95,213-218`.
- CrawlSpider request meta carries `{"rule": rule_index, "link_text": link.text}`, and `_callback`/`_errback` look the rule back up by `response.meta["rule"]` / `failure.request.meta["rule"]` — `scrapy/spiders/crawl.py:132-138,155-168`; `_requests_to_follow` is a no-op unless the response is an `HtmlResponse` and dedups links via a `seen: set[Link]` — `scrapy/spiders/crawl.py:140-153`.
- Deprecation surface: overriding `CrawlSpider._parse_response` warns (use `parse_with_rules`), and the `CRAWLSPIDER_FOLLOW_LINKS` setting is itself deprecated — `scrapy/spiders/crawl.py:106-114,191-204,224-230`.
- XMLFeedSpider supports three iterators selected by the `iterator` attribute ("iternodes" via `xmliter_lxml`, "xml"/"html" via `Selector.xpath(f"//{itertag}")`), raising `NotSupported` otherwise and `NotConfigured` if `parse_node` is undefined — `scrapy/spiders/feed.py:33,74-99`.
- CSVFeedSpider iterates rows via `csviter` with configurable `delimiter`/`quotechar`/`headers`, raising `NotConfigured` if `parse_row` is undefined — `scrapy/spiders/feed.py:120-126,149-159`.
- SitemapSpider security/robustness: `_get_sitemap_body` gunzips bodies under a `max_size` cap (`DOWNLOAD_MAXSIZE`) and silently drops a sitemap on `_DecompressionMaxSizeExceeded`, warning when decompressed size crosses `DOWNLOAD_WARNSIZE` — a zip-bomb guard — `scrapy/spiders/sitemap.py:119-138`.
- SitemapSpider crawl model: `start` seeds `sitemap_urls` with the `_parse_sitemap` callback; `_parse_sitemap` recurses for robots.txt and `sitemapindex`, and matches `urlset` locs against compiled `sitemap_rules` regexes to pick per-URL callbacks — `scrapy/spiders/sitemap.py:56-117`.
<!-- DEEPINIT:END -->
