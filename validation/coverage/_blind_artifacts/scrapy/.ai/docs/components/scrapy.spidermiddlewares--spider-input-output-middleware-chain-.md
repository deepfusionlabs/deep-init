<!-- DEEPINIT:START -->
<!--
provenance:
 stage: extract (BLIND re-derivation from code only)
 component: scrapy.spidermiddlewares (spider-input/output middleware chain)
 path: scrapy/spidermiddlewares/
 doc_in_inputs: false
 inputs: scrapy/spidermiddlewares/{base,depth,httperror,referer,start,urllength}.py;
 scrapy/settings/default_settings.py; scrapy/core/spidermw.py;
 scrapy/utils/decorators.py; scrapy/__init__.py; pyproject.toml
 date: 2026-06-13
-->

# scrapy.spidermiddlewares — spider-input/output middleware chain

## Role

- Provides the built-in spider middlewares — the per-class hook handlers that sit between the engine/scraper and the spider, transforming spider input (responses), spider output (requests/items), start seeds, and spider exceptions; the chain is registered by import-path priority in `SPIDER_MIDDLEWARES_BASE` (`scrapy/settings/default_settings.py:552-558`).
- The five shipped middlewares cover: tag start requests (`scrapy/spidermiddlewares/start.py:12`), filter/handle non-2xx HTTP statuses (`scrapy/spidermiddlewares/httperror.py:38`), populate the `Referer` header per W3C policy (`scrapy/spidermiddlewares/referer.py:291`), enforce a maximum URL length (`scrapy/spidermiddlewares/urllength.py:26`), and track/limit crawl depth (`scrapy/spidermiddlewares/depth.py:30`).
- `BaseSpiderMiddleware` is the optional shared base that implements async `process_start`/`process_spider_output(_async)` by delegating to overridable `get_processed_request`/`get_processed_item` per-item hooks (`scrapy/spidermiddlewares/base.py:18-71`).

## Dependencies (edges)

- → `scrapy.http` (Request/Response model): imports `Request`, `Spider` from the `scrapy` top-level (which re-exports `Request` from `scrapy.http`, `scrapy/__init__.py:10`) at `scrapy/spidermiddlewares/base.py:5`; `referer.py` imports `Request, Response` directly from `scrapy.http` (`scrapy/spidermiddlewares/referer.py:15`); start.py uses `scrapy.http` / `scrapy.http.response` under TYPE_CHECKING (`scrapy/spidermiddlewares/start.py:8-9`).
- → `scrapy.spiders` (Spider base): `Spider` imported via the `scrapy` top-level re-export from `scrapy.spiders` (`scrapy/__init__.py:13`), used in `base.py:5` and in hook signatures (`scrapy/spidermiddlewares/base.py:51`).
- → `scrapy.utils` (shared infrastructure): `_warn_spider_arg` decorator from `scrapy.utils.decorators` (`scrapy/spidermiddlewares/base.py:6`, `depth.py:13`, `httperror.py:13`); `load_object` from `scrapy.utils.misc`, `_looks_like_import_path`/`to_unicode` from `scrapy.utils.python`, `strip_url` from `scrapy.utils.url` (`scrapy/spidermiddlewares/referer.py:17-19`).
- → `scrapy.settings` (configuration system): `httperror.py` reads `HTTPERROR_ALLOW_ALL` / `HTTPERROR_ALLOWED_CODES` (`scrapy/spidermiddlewares/httperror.py:42-45`); `depth.py` reads `DEPTH_LIMIT`/`DEPTH_STATS_VERBOSE`/`DEPTH_PRIORITY` (`scrapy/spidermiddlewares/depth.py:48-50`); `urllength.py` reads `URLLENGTH_LIMIT` (`scrapy/spidermiddlewares/urllength.py:34`); `referer.py` reads `REFERER_ENABLED`/`REFERRER_POLICIES`/`REFERRER_POLICY` (`scrapy/spidermiddlewares/referer.py:326,312,319`); `BaseSettings` type import (`scrapy/spidermiddlewares/httperror.py:24`, `referer.py:26`).
- → `scrapy.crawler` (Crawler lifecycle): every `from_crawler(cls, crawler)` factory takes a `Crawler` and reads `crawler.settings` / `crawler.stats` / `crawler.spider` (`scrapy/spidermiddlewares/base.py:41`, `depth.py:46-53`, `httperror.py:48-51`, `urllength.py:33-37`, `referer.py:325-328`); the `Crawler` import is TYPE_CHECKING-only (`scrapy/spidermiddlewares/base.py:14`).
- → `scrapy signals + middleware base + addons` / exceptions: `IgnoreRequest` subclassed as `HttpError` (`scrapy/spidermiddlewares/httperror.py:12,30`); `NotConfigured` raised to disable a middleware (`scrapy/spidermiddlewares/urllength.py:12,36`, `referer.py:14,327`).
- Intra-component: `depth.py`, `urllength.py`, `referer.py`, `start.py` all subclass `BaseSpiderMiddleware` from `scrapy/spidermiddlewares/base.py` (`depth.py:12,30`, `urllength.py:13,26`, `referer.py:16,291`, `start.py:5,12`).
- INVERSION (no compile-time edge out): the chain is driven by `scrapy.core` — `SpiderMiddlewareManager` loads these classes from `SPIDER_MIDDLEWARES` and dispatches their `process_spider_input`/`process_spider_output`/`process_start`/`process_spider_exception` hooks by duck-typing (`scrapy/core/spidermw.py:54-73`); this package is imported by core, it does not import core.

## Data

- Owns no persistence. Reads/writes transient per-request state on `Request.meta` / `Response.meta` dicts: `depth.py` reads+writes `response.meta["depth"]` and `request.meta["depth"]` (`scrapy/spidermiddlewares/depth.py:76-88`); `start.py` sets `request.meta["is_start_request"]` (`scrapy/spidermiddlewares/start.py:30`); `httperror.py` reads `response.meta` keys `handle_httpstatus_all`/`handle_httpstatus_list` (`scrapy/spidermiddlewares/httperror.py:59-63`); `referer.py` reads `request.meta["referrer_policy"]` (`scrapy/spidermiddlewares/referer.py:367`).
- Mutates the in-flight HTTP model: `referer.py` sets the `Referer` request header via `request.headers.setdefault` (`scrapy/spidermiddlewares/referer.py:438`).
- Writes counters to the shared StatsCollector (not owned here): `depth.py` `inc_value`/`max_value` for `request_depth_count/*` and `request_depth_max` (`scrapy/spidermiddlewares/depth.py:79,99-100`); `httperror.py` `httperror/response_ignored_count` (`scrapy/spidermiddlewares/httperror.py:82-84`); `urllength.py` `urllength/request_ignored_count` (`scrapy/spidermiddlewares/urllength.py:52`).

## Boundary rules

- Discovery & ordering is by integer priority on import-path strings in `SPIDER_MIDDLEWARES_BASE` (start=25, httperror=50, referer=700, urllength=800, depth=900), i.e. the package surface is decoupled from the runner — config-string, not a direct import (`scrapy/settings/default_settings.py:553-558`).
- Each middleware is duck-typed: the manager attaches a hook only if `hasattr(mw, "process_spider_input")` etc., so a middleware implements only the hooks it needs (`scrapy/core/spidermw.py:58-71`); `BaseSpiderMiddleware` documents that middlewares without `process_spider_output`/`process_start` need not subclass it (`scrapy/spidermiddlewares/base.py:23-25`).
- Construction goes through the `from_crawler` factory contract; `NotConfigured` raised there disables the middleware (urllength when `URLLENGTH_LIMIT` is falsy `scrapy/spidermiddlewares/urllength.py:35-36`; referer when `REFERER_ENABLED` is false `scrapy/spidermiddlewares/referer.py:326-327`).
- The legacy positional `spider` hook argument is being removed: hooks default `spider=None` and are wrapped in `@_warn_spider_arg` to emit a deprecation warning if a spider is still passed (`scrapy/spidermiddlewares/base.py:49-66`, `httperror.py:53-56,76-78`).
- `referer.py` enforces a security boundary: import-path policy classes from the response `Referrer-Policy` header are forbidden (`allow_import_path=False`), only allowed from trusted settings (`scrapy/spidermiddlewares/referer.py:372,410-424`).

## Key facts

- `BaseSpiderMiddleware` unifies sync and async output processing: it ships `process_spider_output` (sync generator), `process_spider_output_async` (async generator), and `process_start` (async) that all route each emitted object through `_get_processed` → `get_processed_request` for `Request` instances else `get_processed_item` (`scrapy/spidermiddlewares/base.py:44-71`).
- `response is None` is the canonical "start seed vs spider output" discriminator across the base-derived middlewares: depth, start, and referer all special-case `if response is None` to skip per-response processing for start requests (`scrapy/spidermiddlewares/depth.py:84-86`, `start.py:29-30`, `referer.py:433-435`).
- `referer.py` is a near-complete implementation of the W3C Referrer-Policy spec: 8 named policy classes plus a `scrapy-default` variant (no-referrer-when-downgrade extended to also suppress `file://`/`s3://` parents) selected per-request from meta → response header → settings (`scrapy/spidermiddlewares/referer.py:109-288,330-378`).
- `HttpError` is both a middleware and an exception type: `HttpErrorMiddleware.process_spider_input` raises `HttpError` (an `IgnoreRequest` subclass carrying the response) for disallowed statuses, and `process_spider_exception` catches that same type to record stats and swallow it by returning `` (`scrapy/spidermiddlewares/httperror.py:30-35,54-74,80-91`).
- `DepthMiddleware` is the one middleware that overrides `process_spider_output` to inject `_init_depth(response)` before the base per-item loop, and it deliberately bypasses `BaseSpiderMiddleware.__init__` (`pylint: disable=super-init-not-called`) setting attributes itself (`scrapy/spidermiddlewares/depth.py:33-39,56-72`).
- Depth shaping also adjusts scheduling priority: `request.priority -= depth * self.prio` when `DEPTH_PRIORITY` is set, coupling this middleware's output to the scheduler's ordering (`scrapy/spidermiddlewares/depth.py:89-90`).
- The `offsite` middleware referenced in the discovery note is NOT in this package in this tree — it lives at `scrapy/downloadermiddlewares/offsite.py` and is registered under `DOWNLOADER_MIDDLEWARES_BASE` (`scrapy/settings/default_settings.py:317`); omitted from this component to avoid an ungrounded claim.
<!-- DEEPINIT:END -->
