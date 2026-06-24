<!-- DEEPINIT:START -->
<!--
Provenance: DeepInit EXTRACT stage (BLIND re-derivation from code only)
Component: scrapy.core (engine / scheduler / scraper / spider-middleware runner)
Path: scrapy/core/ (engine.py, scheduler.py, scraper.py, spidermw.py, __init__.py)
Inputs: scrapy/core/*.py, pyproject.toml, scrapy/__init__.py, scrapy/signals.py (cross-ref only)
Date: 2026-06-13 | Run: p5-scrapy-blind | doc_in_inputs: false
Every claim cites a file:line opened inside C:/tmp/p5_scrapy_blind.
-->

# scrapy.core (engine / scheduler / scraper / spider-middleware runner)

## Role

The central orchestration sub-package that drives one crawl: `ExecutionEngine` controls the Scheduler, Downloader and Spider, pulling requests, sending them to the downloader, and feeding responses to the scraper. — `scrapy/core/engine.py:1-2` (module docstring "This is the Scrapy engine which controls the Scheduler, Downloader and Spider"), `scrapy/core/__init__.py:1-3`.

- The engine wires the three runtime collaborators together in its constructor: it instantiates the downloader, scheduler class, and scraper. — `scrapy/core/engine.py:137` (`self.downloader = downloader_cls(crawler)`), `scrapy/core/engine.py:134` (`self.scheduler_cls = self._get_scheduler_class(...)`), `scrapy/core/engine.py:149` (`self.scraper = Scraper(crawler)`).
- `BaseScheduler`/`Scheduler` store requests received from the engine and feed them back on demand (`enqueue_request` / `next_request` / `has_pending_requests`). — `scrapy/core/scheduler.py:52-66`, `:101-124`.
- `Scraper` parses downloaded responses, runs them through spider callbacks/middlewares, and routes resulting items to the item pipelines and resulting requests back to the engine. — `scrapy/core/scraper.py:1-2`, `:440-463`.
- `SpiderMiddlewareManager` is the spider-input/output/exception middleware runner. — `scrapy/core/spidermw.py:48-49`.

## Dependencies (edges)

- scrapy.core.downloader — engine imports `Downloader` (type) and instantiates `downloader_cls` resolved from the `DOWNLOADER` setting; calls `self.downloader.fetch(...)`, `.needs_backout`, `.active`, `.close`. — `scrapy/core/engine.py:54` (TYPE import), `:132` (`load_object(self.settings["DOWNLOADER"])`), `:137`, `:495/:497` (`self.downloader.fetch`), `:352`, `:427`, `:622`.
- scrapy.crawler — engine takes a `Crawler`, reads `crawler.settings/.signals/.logformatter/.stats/.spider/.engine`; scheduler/scraper/spidermw built `from_crawler`. — `scrapy/core/engine.py:55` (TYPE import), `:112-116`; `scrapy/core/scraper.py:46` (TYPE import), `:103`, `:358` (`self.crawler.engine`); `scrapy/core/scheduler.py:23` (TYPE import), `:254`.
- scrapy.spiders — `Scheduler` imports `Spider` at runtime; scraper imports `Spider`; engine references `Spider` (TYPE) and calls `spider._parse`. — `scrapy/core/scheduler.py:12` (`from scrapy.spiders import Spider`), `scrapy/core/scraper.py:15` (`from scrapy import Spider, signals`), `scrapy/core/spidermw.py:19`, `scrapy/core/engine.py:59`, `scrapy/core/scraper.py:318` (`self.crawler.spider._parse`).
- scrapy.pipelines — scraper resolves `ItemPipelineManager` from the `ITEM_PROCESSOR` setting and drives `process_item(_async)` / `open_spider(_async)` / `close_spider(_async)`. — `scrapy/core/scraper.py:24` (`from scrapy.pipelines import ItemPipelineManager`), `:108-111`, `:495`, `:497`.
- scrapy.http — engine/scraper/spidermw import `Request`/`Response` and type-dispatch on them. — `scrapy/core/engine.py:31` (`from scrapy.http import Request, Response`), `scrapy/core/scraper.py:23`, `scrapy/core/spidermw.py:21`, `scrapy/core/scheduler.py:25` (TYPE).
- scrapy signals + middleware base — engine/scraper emit signals via `crawler.signals`; `SpiderMiddlewareManager` extends `MiddlewareManager`. — `scrapy/core/engine.py:22` (`from scrapy import signals`), `:185/:237/:366/:441/:510/:556/:569/:645`; `scrapy/core/scraper.py:15`, `:371/:506/:535`; `scrapy/core/spidermw.py:22` (`from scrapy.middleware import MiddlewareManager`), `:48`.
- scrapy.settings — engine/scheduler read configuration via `crawler.settings[...]` / `.getbool` / `.getint`; scheduler reads many `SCHEDULER_*` / `DUPEFILTER_CLASS` keys. — `scrapy/core/engine.py:132`, `:156`; `scrapy/core/scheduler.py:255-264`, `:334`; `scrapy/core/scraper.py:108-109`, `:120`, `:168`; `scrapy/core/spidermw.py:35` (TYPE), `:54`.
- scrapy.utils — heavy use of shared infra: reactor/async glue (`CallLaterOnce`, `AsyncioLoopingCall`/`create_looping_call`, `is_asyncio_available`), defer helpers (`deferred_from_coro`, `maybe_deferred_to_future`, `_schedule_coro`, `parallel*`), `load_object`/`build_from_crawler`, deprecation/log/conf/job helpers. — `scrapy/core/engine.py:32-47`; `scrapy/core/scraper.py:25-41`; `scrapy/core/spidermw.py:23-30`; `scrapy/core/scheduler.py:13-14` (`scrapy.utils.job`, `scrapy.utils.misc`).
- scrapy queues + dupefilter (scheduling support) — `Scheduler` resolves and drives `ScrapyPriorityQueue` (`SCHEDULER_PRIORITY_QUEUE`), disk/memory queue classes, and a `BaseDupeFilter` (`DUPEFILTER_CLASS`). — `scrapy/core/scheduler.py:26` (`from scrapy.pqueues import ScrapyPriorityQueue`, TYPE), `:24` (`BaseDupeFilter`, TYPE), `:255-263`, `:314`, `:374-375`.
- scrapy statscollectors — scheduler increments `scheduler/enqueued*` and `scheduler/dequeued*`; scraper increments `spider_exceptions/*`. — `scrapy/core/scheduler.py:27` (TYPE), `:380-385`, `:399-405`; `scrapy/core/scraper.py:378-381`.
- scrapy.exceptions — control-flow exceptions (`CloseSpider`, `DontCloseSpider`, `IgnoreRequest`, `DropItem`, `_InvalidOutput`, `ScrapyDeprecationWarning`). — `scrapy/core/engine.py:25-30`; `scrapy/core/scraper.py:17-22`; `scrapy/core/spidermw.py:20`.
- scrapy.logformatter — engine/scraper format log messages through `crawler.logformatter`. — `scrapy/core/engine.py:56` (TYPE), `:505`; `scrapy/core/scraper.py:47` (TYPE), `:124`, `:271`, `:363`, `:501`, `:530`.
- (Internal, intra-component) — engine imports `BaseScheduler` and `Scraper`; scraper imports `SpiderMiddlewareManager`. — `scrapy/core/engine.py:23-24`; `scrapy/core/scraper.py:16`.

## Data

- Scheduler job-directory persistence: when `JOBDIR` is set, the scheduler creates a `requests.queue/` directory and reads/writes `active.json` (priority-queue `startprios` state) on open/close. — `scrapy/core/scheduler.py:480-487` (`_dqdir` → `Path(jobdir,"requests.queue")`), `:489-494` (`_read_dqs_state` reads `active.json`), `:496-498` (`_write_dqs_state` writes `active.json`), `:358-362` (`close` dumps disk-queue state).
- In-memory request store: dual priority queues — memory queue `mqs` (always) and optional disk queue `dqs` (only when `dqdir`), built from the configured `ScrapyPriorityQueue`. — `scrapy/core/scheduler.py:349-350`, `:446-478`.
- Scraper in-flight buffer: `Slot` holds a `deque` queue of `(result, request, deferred)` tuples plus an `active` set and `active_size` byte accounting bounded by `max_active_size`. — `scrapy/core/scraper.py:58-99` (`Slot`), `:65-67`, `:98-99` (`needs_backout`).
- Engine in-flight tracking: `_Slot.inprogress` is a `set[Request]` of requests currently being downloaded. — `scrapy/core/engine.py:65-86` (`_Slot.inprogress`, `add_request`/`remove_request`).
- Duplicate-request filtering is delegated to a dupefilter instance (`self.df`), not owned data — `request_seen` gates enqueue. — `scrapy/core/scheduler.py:314`, `:364-376`.

## Boundary rules

- Scheduler-interface contract is enforced structurally: `BaseSchedulerMeta` is a metaclass doing duck-typed `issubclass`/`isinstance` (must have `has_pending_requests`/`enqueue_request`/`next_request`), and the engine rejects a `SCHEDULER` setting whose class is not a `BaseScheduler`. — `scrapy/core/scheduler.py:33-49` (metaclass), `scrapy/core/engine.py:155-162` (`_get_scheduler_class` raises `TypeError`).
- Collaborators are pluggable via settings + `load_object`, never hard-wired: `DOWNLOADER`, `SCHEDULER`, `ITEM_PROCESSOR`, `DUPEFILTER_CLASS`, `SCHEDULER_*_QUEUE`. — `scrapy/core/engine.py:132`, `:156`; `scrapy/core/scraper.py:108-109`; `scrapy/core/scheduler.py:255-263`.
- Backpressure boundary: the engine stops sending requests when `needs_backout` is true, which ORs the downloader's and the scraper-slot's own backout signals. — `scrapy/core/engine.py:341-354`, `scrapy/core/scraper.py:98-99`.
- Async-API migration boundary: every public sync method (`start`/`stop`/`close`/`open_spider`/`close_spider`/`download` on the engine; `open_spider`/`close_spider`/`call_spider`/`start_itemproc` on the scraper; `scrape_response` on spidermw) is deprecated and delegates to an `_async` coroutine variant. — `scrapy/core/engine.py:164-174`, `:205-211`, `:241-247`, `:520-528`, `:585-593`; `scrapy/core/scraper.py:153-161`, `:180-186`, `:295-303`, `:465-478`; `scrapy/core/spidermw.py:182-207`.
- Spider-middleware output-protocol enforcement: a middleware that lacks async spider-output support raises `TypeError`; `process_spider_input` must return `None` or raise, else `_InvalidOutput`. — `scrapy/core/spidermw.py:258-265`, `:88-93`.

## Key facts

- Concurrency substrate is Twisted async glue, with a runtime switch between the Twisted reactor and the asyncio loop: code branches on `is_asyncio_available` and uses `Deferred`/`inlineCallbacks` vs `asyncio.ensure_future`. — `scrapy/core/engine.py:196-201`, `scrapy/core/scraper.py:410-438`; Twisted is the top declared dependency (`Twisted>=21.7.0`). — `pyproject.toml:9-10`.
- Request-processing loop is driven by a debounced `CallLaterOnce(self._start_scheduled_requests)` ("nextcall") plus a 5-second heartbeat `LoopingCall` that re-schedules it, covering the case where the scheduler reports pending requests but returns none. — `scrapy/core/engine.py:103` (`_SLOT_HEARTBEAT_INTERVAL=5.0`), `:538` (`CallLaterOnce`), `:77-79`, `:299-308`.
- Default request order is LIFO/DFO: the default scheduler stores requests in priority queues that, with default settings, behave as a LIFO stack giving depth-first crawl order. — `scrapy/core/scheduler.py:128-164` (docstring), `:387-406` (memory-then-disk pop).
- Disk-queue is preferred over memory on enqueue (serializable requests go to disk; non-serializable fall back to memory and bump `scheduler/unserializable`). — `scrapy/core/scheduler.py:364-385`, `:414-436`.
- Engine ↔ Scraper ↔ Pipelines data flow: downloader output (Request) is re-`crawl`ed; a Response is `enqueue_scrape`d, run through spider middlewares + callback, and emitted items are sent to the item pipelines via `start_itemproc_async`, firing `item_scraped`/`item_dropped`/`item_error` signals. — `scrapy/core/engine.py:398-420`, `scrapy/core/scraper.py:244-262`, `:450-463`, `:480-540`.
- Spider idleness + graceful close: `spider_is_idle` checks scraper-slot idle, downloader inactive, start-iterator exhausted, and scheduler empty; `_spider_idle` honors a `DontCloseSpider` veto from `spider_idle` signal handlers and reads a custom reason from `CloseSpider`. — `scrapy/core/engine.py:422-431`, `:560-583`.
- The spider middleware runner uses a custom `MutableAsyncChain` to interleave callback output with exception-recovery output, and supports four hook points: `process_spider_input` / `process_start` / `process_spider_output` / `process_spider_exception`. — `scrapy/core/spidermw.py:30`, `:57-73`, `:100-180`.
- Close is best-effort and ordered: `close_spider_async` closes slot → downloader → scraper → scheduler → fires `spider_closed` → closes stats → runs the `spider_closed_callback`, each wrapped in its own try/except so one failure does not abort the rest. — `scrapy/core/engine.py:595-687`.
<!-- DEEPINIT:END -->
