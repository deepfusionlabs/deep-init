<!--
DeepInit provenance header
stage: blind-mirror-test
repo: scrapy@blind
doc_in_inputs: false
tier: deep (.ai/docs, on-demand)
note: re-derived from CODE ONLY (pyproject.toml + scrapy/ package layout). Every claim cites a file:line.
-->

# Architecture — scrapy (blind re-derivation)

## Overview

Scrapy is a single hatchling-built Python package (`pyproject.toml:6` name = "Scrapy"; `pyproject.toml:1-3` build-backend hatchling) exposing exactly one console entry point, `scrapy = "scrapy.cmdline:execute"` (`pyproject.toml:63-64`). It is an event-driven web-crawling framework.

The hub is the `ExecutionEngine`, which `scrapy/core/engine.py:1-6` self-describes as "the Scrapy engine which controls the Scheduler, Downloader and Spider". Its constructor wires three runtime collaborators: `self.scheduler_cls` (`scrapy/core/engine.py:134`), `self.downloader` (`scrapy/core/engine.py:137`) and `self.scraper = Scraper(crawler)` (`scrapy/core/engine.py:149`); the Scraper in turn builds the `SpiderMiddlewareManager.from_crawler` and the `ItemPipelineManager` (`scrapy/core/scraper.py:105-111`).

Request/Response objects (`scrapy/core/engine.py:31`) flow through two pluggable middleware chains: the `DownloaderMiddlewareManager` on the network side (`scrapy/core/downloader/middleware.py:34`) and the `SpiderMiddlewareManager` around the user's Spider (`scrapy/core/spidermw.py:48`, `scrapy/spiders/__init__.py:31`). Scraped Items flow into item pipelines (`scrapy/pipelines/media.py:58`). All middleware chains share one `MiddlewareManager` ABC (`scrapy/middleware.py:35`), which is subclassed inward by DownloaderMiddlewareManager (`scrapy/core/downloader/middleware.py:34`), SpiderMiddlewareManager (`scrapy/core/spidermw.py:48`), ExtensionManager (`scrapy/extension.py:18`) and ItemPipelineManager (`scrapy/pipelines/__init__.py:31`).

Lifecycle and ownership are held by the Crawler / CrawlerProcess family (`scrapy/crawler.py:57`, `scrapy/crawler.py:720`, `scrapy/crawler.py:796`); the CLI is the outermost orchestration layer entered via `scrapy.cmdline:execute` (`scrapy/cmdline.py:169-215`). Configuration is a priority-aware Settings system (`scrapy/settings/__init__.py:79`, `scrapy/settings/__init__.py:690`) whose `default_settings.py` registers the swappable backends as import-string literals (e.g. per-scheme download handlers at `scrapy/settings/default_settings.py:286-292`).

## Data-flow spine (engine ↔ scraper ↔ pipelines)

- A downloader-output Request is re-`crawl`-ed; a Response is `enqueue_scrape`'d, run through spider middlewares + the spider callback, and emitted items are sent to item pipelines via `start_itemproc_async`, firing item_scraped/item_dropped/item_error signals — `scrapy/core/engine.py:398-420`, `scrapy/core/scraper.py:480-540`.
- The request-processing loop is driven by a debounced `CallLaterOnce(self._start_scheduled_requests)` ("nextcall") plus a 5s heartbeat LoopingCall that re-schedules it (covering the case where the scheduler reports pending requests but returns none) — `scrapy/core/engine.py:103`, `scrapy/core/engine.py:538`, `scrapy/core/engine.py:299-308`.
- Backpressure: the engine stops sending when `needs_backout` is true, ORing downloader and scraper-slot backout signals — `scrapy/core/engine.py:341-354`.
- Graceful close is best-effort and ordered: slot -> downloader -> scraper -> scheduler -> fires spider_closed -> closes stats -> runs spider_closed_callback, each wrapped in its own try/except — `scrapy/core/engine.py:595-687`.

## Component decomposition rationale

The package layout (the `scrapy/` tree + build manifest) groups by concern; each component below is justified by code anchors, not prose docs.

1. **scrapy.core (engine / scheduler / scraper / spider-middleware runner)** — the central orchestration sub-package. ExecutionEngine wires Scheduler/Downloader/Scraper (`scrapy/core/engine.py:1-2`, `:76`, `:137`, `:149`); contains engine.py, scheduler.py (BaseScheduler/Scheduler), scraper.py (Scraper), spidermw.py (SpiderMiddlewareManager at `scrapy/core/spidermw.py:48`).

2. **scrapy.core.downloader (downloader + handlers + TLS)** — a distinct nested package owning the network-fetch concern: Downloader (`scrapy/core/downloader/__init__.py:99`), DownloaderMiddlewareManager (`scrapy/core/downloader/middleware.py:34`), contextfactory.py/tls.py, and a per-scheme handler registry under handlers/ wired by DOWNLOAD_HANDLERS_BASE (`scrapy/settings/default_settings.py:286-292`).

3. **scrapy.core.http2 (HTTP/2 client stack)** — a self-contained transport sub-package (agent.py/protocol.py/stream.py) implementing the HTTP/2 agent/protocol/stream, separate from the http11 handler; entry point `H2Agent.request` at `scrapy/core/http2/agent.py:155-167`.

4. **scrapy.crawler (Crawler + Runner/Process lifecycle)** — the top-level lifecycle module: Crawler (`scrapy/crawler.py:57`), CrawlerRunnerBase (`scrapy/crawler.py:344`), CrawlerRunner (`scrapy/crawler.py:397`), AsyncCrawlerRunner (`scrapy/crawler.py:494`), CrawlerProcess (`scrapy/crawler.py:720`), AsyncCrawlerProcess (`scrapy/crawler.py:796`).

5. **scrapy.cmdline + scrapy.commands (CLI)** — the sole declared console entry point (`pyproject.toml:63-64`). cmdline.py dispatches to one command class per module in commands/; ScrapyCommand base at `scrapy/commands/__init__.py:27`. Command discovery is convention-based (one Command class per module, named by the module's last path segment) — `scrapy/cmdline.py:49`, `:54-60`.

6. **scrapy.spiders (Spider base + built-in spider types)** — the user-facing extension point: Spider base (`scrapy/spiders/__init__.py:31`) plus CrawlSpider (crawl.py), feed/XML spiders (feed.py), SitemapSpider (sitemap.py). No-downward-coupling: spiders import http/settings/utils/selector/linkextractors but never import scrapy.core.* at runtime; the only core coupling is inbound — `scrapy/spiders/__init__.py:12-28`, `scrapy/core/scraper.py:318`.

7. **scrapy.downloadermiddlewares (request/response middleware chain)** — a pluggable middleware package (cookies, redirect, retry, robotstxt, httpcompression, httpproxy, httpcache, useragent, offsite,...) run by the DownloaderMiddlewareManager; the package `__init__.py` is empty so each module is an independently-loadable component — `scrapy/downloadermiddlewares/cookies.py:40`, `scrapy/downloadermiddlewares/retry.py:141`.

8. **scrapy.spidermiddlewares (spider-input/output middleware chain)** — the parallel middleware package around the spider (start, httperror, referer, urllength, depth) executed by SpiderMiddlewareManager; registered by import-path priority in SPIDER_MIDDLEWARES_BASE — `scrapy/settings/default_settings.py:552-558`, `scrapy/spidermiddlewares/base.py`.

9. **scrapy.pipelines (item pipelines incl. media/files/images)** — the post-scrape item-processing package: an ordered ItemPipelineManager (a MiddlewareManager subclass, `scrapy/pipelines/__init__.py:31`) plus MediaPipeline ABC (`scrapy/pipelines/media.py:58`) with FilesPipeline (files.py) and ImagesPipeline (images.py).

10. **scrapy.extensions (lifecycle extensions / feed export / telnet)** — optional signal-driven add-ons loaded by ExtensionManager (which lives OUTSIDE this dir at `scrapy/extension.py:18`): closespider, corestats, logstats, throttle, memusage, telnet, plus FeedExporter with file/ftp/s3 storage backends and the HTTP-cache policy/storage. The package `__init__.py` is empty — `scrapy/extensions/closespider.py:58-85`, `scrapy/extensions/feedexport.py:91`.

11. **scrapy.http (Request/Response model + cookies/headers)** — the core data-model package ("Module containing all HTTP related classes", `scrapy/http/__init__.py:2`): request/ (Request, FormRequest, JsonRequest, XmlRpcRequest), response/ (Response, TextResponse, HtmlResponse, XmlResponse, JsonResponse), plus headers.py and cookies.py. A leaf data layer imported BY the engine/downloader/middlewares — `scrapy/core/engine.py:31`.

12. **scrapy.settings (configuration system)** — the priority-aware configuration subsystem: BaseSettings (MutableMapping) and Settings, with the full default registry in default_settings.py — `scrapy/settings/__init__.py:79`, `scrapy/settings/__init__.py:690`, `scrapy/settings/default_settings.py:286`.

13. **scrapy.utils (shared infrastructure incl. reactor/async glue)** — the largest support package binding the async model together: reactor.py (Twisted/asyncio reactor install), defer.py (Deferred<->coroutine bridge), asyncio.py, plus misc/load_object, conf, log, iterators, url. Corroboration that it is a depended-upon leaf: scrapy.core.engine imports 7 distinct utils modules — `scrapy/core/engine.py:32-47`, `scrapy/utils/misc.py:58`, `scrapy/utils/reactor.py:10`.

14. **scrapy.selector + scrapy.linkextractors (extraction)** — the content-extraction layer: Selector/SelectorList wrapping parsel (`scrapy/selector/unified.py:39`) and the link-extraction package (LxmlLinkExtractor exported as LinkExtractor in `scrapy/linkextractors/lxmlhtml.py:164`) used by CrawlSpider rules.

15. **scrapy item + loader + exporters (item data layer)** — the structured-output trio: Item/Field model (`scrapy/item.py:57`, `:24`), ItemLoader (`scrapy/loader/__init__.py:20`, extends itemloaders) and serialization exporters (`scrapy/exporters.py:39`).

16. **scrapy queues + dupefilter + spiderloader (scheduling support)** — the scheduler's pluggable backends: priority queues (`scrapy/pqueues.py:52`, `:277` DownloaderAwarePriorityQueue), disk/memory request queues (squeues.py), the RFPDupeFilter (`scrapy/dupefilters.py:53`) and the SpiderLoader (`scrapy/spiderloader.py:51`) that discovers spiders.

17. **scrapy.contracts (spider contract testing)** — a self-contained spider-callback testing subsystem (ContractsManager + Contract base at `scrapy/contracts/__init__.py:92`, `:24`, default.py contracts) driven by the `scrapy check` command.

18. **scrapy signals + middleware base + addons (extensibility core)** — the shared plug-in machinery every chain reuses: MiddlewareManager ABC (`scrapy/middleware.py:35`) subclassed by Downloader/Spider/Extension/Pipeline managers, the PyDispatcher-backed SignalManager (`scrapy/signalmanager.py:14`) and AddonManager (`scrapy/addons.py:18`).

## Cross-cutting structural observations

- **Settings as the decoupling layer.** Coupling from scrapy.settings to other components is overwhelmingly via runtime import-string literals in default_settings.py (resolved by consumers' `load_object`, not imported here); the settings module itself has only two compile-time scrapy imports (scrapy.utils, scrapy.exceptions) — `scrapy/settings/__init__.py:14`, `scrapy/settings/__init__.py:12`, `scrapy/settings/default_settings.py:307`.
- **Inversion of control on the spider-middleware side.** scrapy.spidermiddlewares classes are loaded by import-path by scrapy.core (SpiderMiddlewareManager) and never import the core runner — `scrapy/core/spidermw.py:54-73`.
- **Cycle avoidance via lazy imports.** scrapy.http defers `from scrapy.selector import Selector` with an explicit "# circular import" note (`scrapy/http/response/text.py:149-150`); Spider.logger imports SpiderLoggerAdapter inside the property body (`scrapy/spiders/__init__.py:54-60`); scrapy.pipelines.files imports ImagesPipeline lazily inside `__init__` (`scrapy/pipelines/files.py:472`).
