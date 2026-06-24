<!--
DeepInit provenance header
stage: blind-mirror-test
repo: scrapy@blind
doc_in_inputs: false
tier: lean (always-loaded)
note: every claim is grounded to a file:line re-derived from CODE ONLY (build manifest + source + layout).
-->

# AGENTS.md — scrapy (blind mirror test)

## Architecture

Scrapy is a single hatchling-built Python package (`pyproject.toml:6` name = "Scrapy"; `pyproject.toml:1-3` build-backend hatchling) exposing one console entry point, `scrapy = "scrapy.cmdline:execute"` (`pyproject.toml:64`). It is an event-driven web-crawling framework whose hub is the `ExecutionEngine` (`scrapy/core/engine.py:1-6` self-describes as "the Scrapy engine which controls the Scheduler, Downloader and Spider"); the engine instantiates and wires a Scheduler (`scrapy/core/engine.py:76`), a Downloader (`scrapy/core/engine.py:137`) and a Scraper (`scrapy/core/engine.py:149`), passing Request/Response objects (`scrapy/core/engine.py:31`) through two pluggable middleware chains — `DownloaderMiddlewareManager` (`scrapy/core/downloader/middleware.py:34`) on the network side and `SpiderMiddlewareManager` (`scrapy/core/spidermw.py:48`) around the user's Spider (`scrapy/spiders/__init__.py:31`) — with scraped Items flowing into item pipelines (`scrapy/pipelines/media.py:58`). All chains share one `MiddlewareManager` ABC (`scrapy/middleware.py:35`), and lifecycle/ownership is held by the Crawler / CrawlerProcess family (`scrapy/crawler.py:57`, `scrapy/crawler.py:720`, `scrapy/crawler.py:796`). Configuration is a priority-aware Settings system (`scrapy/settings/__init__.py:79`, `scrapy/settings/__init__.py:690`) whose `default_settings.py` registers the swappable backends (e.g. per-scheme download handlers, `scrapy/settings/default_settings.py:286-292`).

## Component registry

| Component | Role | Path / anchor |
|-----------|------|---------------|
| scrapy.core (engine / scheduler / scraper / spider-middleware runner) | Central orchestration: ExecutionEngine controls Scheduler, Downloader and Spider, routes responses to the Scraper and items to pipelines | `scrapy/core/` — `scrapy/core/engine.py:1-2` |
| scrapy.core.downloader (downloader + handlers + TLS) | Owns the network-fetch concern: Downloader.fetch runs the middleware chain, throttles per slot, dispatches to per-scheme handlers | `scrapy/core/downloader/` — `scrapy/core/downloader/__init__.py:99` |
| scrapy.core.http2 (HTTP/2 client stack) | Self-contained Twisted HTTP/2 client: pools connections, multiplexes requests onto streams via hyper-h2 | `scrapy/core/http2/` — `scrapy/core/http2/agent.py:155-167` |
| scrapy.crawler (Crawler + Runner/Process lifecycle) | Top-level crawl lifecycle: Crawler wires one spider to settings/engine; Runner/Process own reactor + event-loop startup | `scrapy/crawler.py` — `scrapy/crawler.py:57` |
| scrapy.cmdline + scrapy.commands (CLI) | The `scrapy` console entry point: parse argv, resolve a ScrapyCommand subclass, optionally build a crawler process, dispatch run | `scrapy/commands/` — `scrapy/cmdline.py:169-215`, `scrapy/commands/__init__.py:27` |
| scrapy.spiders (Spider base + built-in spider types) | User-facing extension point: Spider base + CrawlSpider/XMLFeedSpider/CSVFeedSpider/SitemapSpider | `scrapy/spiders/` — `scrapy/spiders/__init__.py:31` |
| scrapy.downloadermiddlewares (request/response middleware chain) | Pluggable downloader middlewares (cookies, redirect, retry, robotstxt, httpcompression, httpproxy, httpcache, offsite,...) | `scrapy/downloadermiddlewares/` — `scrapy/downloadermiddlewares/cookies.py:40` |
| scrapy.spidermiddlewares (spider-input/output middleware chain) | Built-in spider middlewares (start, httperror, referer, urllength, depth) between scraper and spider | `scrapy/spidermiddlewares/` — `scrapy/settings/default_settings.py:552-558`, `scrapy/spidermiddlewares/base.py` |
| scrapy.pipelines (item pipelines incl. media/files/images) | Post-scrape item processing: ItemPipelineManager + MediaPipeline ABC with FilesPipeline/ImagesPipeline | `scrapy/pipelines/` — `scrapy/pipelines/__init__.py:31`, `scrapy/pipelines/media.py:58` |
| scrapy.extensions (lifecycle extensions / feed export / telnet) | Optional signal-driven add-ons (closespider, corestats, throttle, memusage, telnet) + FeedExporter + HTTP-cache | `scrapy/extensions/` — `scrapy/extensions/closespider.py:58-85`, `scrapy/extensions/feedexport.py:91` |
| scrapy.http (Request/Response model + cookies/headers) | The HTTP data model: Request/Response + typed subclasses + Headers/CookieJar | `scrapy/http/` — `scrapy/http/__init__.py:2` |
| scrapy.settings (configuration system) | Priority-aware freezable config: BaseSettings (MutableMapping) + Settings + default registry | `scrapy/settings/` — `scrapy/settings/__init__.py:79`, `scrapy/settings/__init__.py:690` |
| scrapy.utils (shared infrastructure incl. reactor/async glue) | Leaf shared infra: reactor install, Deferred<->coroutine bridge, load_object, conf/log/parsing | `scrapy/utils/` — `scrapy/utils/misc.py:58`, `scrapy/utils/reactor.py:10` |
| scrapy.selector + scrapy.linkextractors (extraction) | Content extraction: Selector/SelectorList over parsel + LxmlLinkExtractor (LinkExtractor) | `scrapy/selector/` — `scrapy/selector/unified.py:39`, `scrapy/linkextractors/lxmlhtml.py:164` |
| scrapy item + loader + exporters (item data layer) | Structured-data layer: Item/Field model + ItemLoader + JSON/XML/CSV/Pickle exporters | `scrapy/item.py` — `scrapy/item.py:57`, `scrapy/loader/__init__.py:20`, `scrapy/exporters.py:39` |
| scrapy queues + dupefilter + spiderloader (scheduling support) | Pluggable scheduler backends: priority queues, disk/memory queues, RFPDupeFilter, SpiderLoader | `scrapy/pqueues.py` — `scrapy/pqueues.py:52`, `scrapy/dupefilters.py:53`, `scrapy/spiderloader.py:51` |
| scrapy.contracts (spider contract testing) | Docstring-driven spider-callback test framework run as unittest cases | `scrapy/contracts/` — `scrapy/contracts/__init__.py:92` |
| scrapy signals + middleware base + addons (extensibility core) | Shared plug-in machinery: MiddlewareManager ABC, PyDispatcher SignalManager, AddonManager | `scrapy/middleware.py` — `scrapy/middleware.py:35`, `scrapy/signalmanager.py:14`, `scrapy/addons.py:18` |

## Technical dependencies

(Selected highest-value edges; full grounded list in `.ai/docs/technical-dependencies.md`.)

- scrapy.core -> scrapy.core.downloader (import + runtime-call: load_object DOWNLOADER,.fetch/.needs_backout/.close) — `scrapy/core/engine.py:132`
- scrapy.core -> scrapy.pipelines (import + runtime-call: load_object ITEM_PROCESSOR, process_item_async) — `scrapy/core/scraper.py:24`
- scrapy.core -> scrapy.http (import + isinstance type-dispatch) — `scrapy/core/engine.py:31`
- scrapy.core -> scrapy queues + dupefilter + spiderloader (ScrapyPriorityQueue, BaseDupeFilter) — `scrapy/core/scheduler.py:26`
- scrapy.core.downloader -> scrapy.core.http2 (import) — `scrapy/core/downloader/handlers/http2.py:9`
- scrapy.core.http2 -> scrapy.core.downloader (import: TLS context-factory helper) — `scrapy/core/http2/agent.py:17`
- scrapy.crawler -> scrapy.core (import + runtime-call) — `scrapy/crawler.py:17`
- scrapy.cmdline + scrapy.commands -> scrapy.crawler (import + runtime-instantiation) — `scrapy/cmdline.py:13`, `scrapy/cmdline.py:206-213`
- scrapy.cmdline + scrapy.commands -> scrapy.contracts (ContractsManager) — `scrapy/commands/check.py:11`, `scrapy/commands/check.py:79`
- scrapy.downloadermiddlewares -> scrapy.core.downloader (manager runs the hooks) — `scrapy/core/downloader/middleware.py:44`
- scrapy.downloadermiddlewares -> scrapy.core (engine.download_async for robots.txt) — `scrapy/downloadermiddlewares/robotstxt.py:100`
- scrapy.downloadermiddlewares -> scrapy.spidermiddlewares (RefererMiddleware for redirect Referer) — `scrapy/downloadermiddlewares/redirect.py:12`
- scrapy.spidermiddlewares -> scrapy.core (INVERSION — SpiderMiddlewareManager loads these by import-path; no compile-time edge out) — `scrapy/core/spidermw.py:54-73`
- scrapy.pipelines -> scrapy signals + middleware base + addons (MiddlewareManager subclass) — `scrapy/pipelines/__init__.py:16`, `scrapy/pipelines/__init__.py:31`
- scrapy.pipelines -> scrapy.core (engine.download_async for media) — `scrapy/pipelines/media.py:212`
- scrapy.extensions -> scrapy.crawler (sole injected dep) — `scrapy/extensions/feedexport.py:43`, `scrapy/extensions/telnet.py:32`
- scrapy.extensions -> scrapy.core.downloader (throttle reads+mutates slots) — `scrapy/extensions/throttle.py:13`
- scrapy.spiders -> scrapy.http (import) — `scrapy/spiders/__init__.py:13`
- scrapy.spiders -> scrapy.selector + scrapy.linkextractors (LinkExtractor/Selector) — `scrapy/spiders/crawl.py:17-18`
- scrapy.utils -> scrapy.core (runtime-call: ExecutionEngine internals via get_engine_status) — `scrapy/utils/engine.py:10`, `scrapy/utils/engine.py:15-30`
- scrapy.settings -> scrapy.* (default-registry-refs as import-string literals, NOT compile-time imports) — `scrapy/settings/default_settings.py:307` ff.
- scrapy queues + dupefilter + spiderloader -> scrapy.core.downloader (crawler.engine.downloader slots) — `scrapy/pqueues.py:262`
- scrapy.http -> scrapy.selector (lazy import to break cycle) — `scrapy/http/response/text.py:150`

## Critical to know

- **Twisted is the async substrate; runtime switch to asyncio.** The engine branches on `is_asyncio_available` between the Twisted reactor (Deferred/inlineCallbacks) and the asyncio loop (`asyncio.ensure_future`) — `scrapy/core/engine.py:196-201`; Twisted is the top declared dependency `Twisted>=21.7.0` — `pyproject.toml:9-10`. The default Twisted reactor is `twisted.internet.asyncioreactor.AsyncioSelectorReactor` — `scrapy/settings/default_settings.py:580`.
- **Scheduler interface is enforced structurally, not by inheritance.** `BaseSchedulerMeta` duck-types issubclass/isinstance (must have has_pending_requests/enqueue_request/next_request) and the engine raises TypeError if SCHEDULER is not a BaseScheduler — `scrapy/core/scheduler.py:33-49`, `scrapy/core/engine.py:155-162`.
- **Collaborators are pluggable via settings + load_object, never hard-wired** (DOWNLOADER, SCHEDULER, ITEM_PROCESSOR, DUPEFILTER_CLASS, SCHEDULER_*_QUEUE) — `scrapy/core/engine.py:132`. `build_from_crawler` prefers `objcls.from_crawler(crawler,...)` else `__init__` — `scrapy/utils/misc.py:195-218`.
- **HTTPS certificate verification is OFF by default.** `_ScrapyClientContextFactory` is non-peer-verifying, `DOWNLOAD_VERIFY_CERTIFICATES` defaults False, and `_ScrapyClientTLSOptions` deliberately catches VerificationError/CertificateError/ValueError to warn-not-fail — `scrapy/core/downloader/contextfactory.py:42-43`, `scrapy/core/downloader/contextfactory.py:76`, `scrapy/core/downloader/tls.py:71-110`, `scrapy/settings/default_settings.py:305`.
- **The settings priority ladder is the layering invariant.** `SETTINGS_PRIORITIES = {default:0, command:10, addon:15, project:20, spider:30, cmdline:40}`; a set only takes effect if the incoming priority >= the stored priority, and `freeze` makes settings immutable — `scrapy/settings/__init__.py:31`, `scrapy/settings/__init__.py:69`, `scrapy/settings/__init__.py:608`.
- **The `_BASE` settings convention drives every chain order.** Framework component lists live in `*_BASE` settings, user overrides in the un-suffixed twin; integer priorities (NOT import order) order the chains — e.g. DOWNLOADER_MIDDLEWARES_BASE Offsite=50/RobotsTxt=100/Retry=550/Redirect=600/Cookies=700/HttpProxy=750/HttpCache=900 — `scrapy/settings/default_settings.py:317-330`, `scrapy/settings/__init__.py:319`.
- **One reactor per process; module-level reactor import is lint-banned.** Only the first crawler installs the reactor; `twisted.internet.reactor` is imported lazily inside functions because importing it installs the global reactor; reactor-enabled vs reactorless are mutually exclusive (RuntimeError) — `scrapy/crawler.py:756-761`, `pyproject.toml:407-413`, `scrapy/crawler.py:139-142`, `scrapy/utils/reactorless.py:33-47`.
- **Dual API surface by design.** Deferred-based `CrawlerRunner`/`CrawlerProcess` (`scrapy/crawler.py:397`, `scrapy/crawler.py:720`) parallel coroutine-based `AsyncCrawlerRunner`/`AsyncCrawlerProcess` (`scrapy/crawler.py:494`, `scrapy/crawler.py:796`); many public sync methods are deprecated shims delegating to `_async` variants — `scrapy/core/engine.py:164-174`.
- **Spider middlewares never import the core runner — inversion of control.** `SpiderMiddlewareManager` loads them by import-path from settings and dispatches their hooks; the only core coupling is inbound — `scrapy/core/spidermw.py:54-73`, `scrapy/spiders/__init__.py:12-28`.
- **No bundled datastore; persistence is pluggable backends.** Feed export and httpcache use file/ftp/s3 backends; there is no fixed DB — `scrapy/settings/default_settings.py:378-381`. (See `.ai/docs/data-layer.md`.)
- **Redirect strips cross-origin credentials.** Cookie dropped unless same-host + no scheme downgrade; Authorization dropped on any scheme/host/port change; proxy creds stripped on scheme change — `scrapy/downloadermiddlewares/redirect.py:132-174`.
- **License & runtime floor: BSD-3-Clause, requires-python >=3.10** — `pyproject.toml:49`, `pyproject.toml:52`.
