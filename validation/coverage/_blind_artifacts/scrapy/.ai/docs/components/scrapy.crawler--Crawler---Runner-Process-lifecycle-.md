<!-- DEEPINIT provenance: stage=EXTRACT component="scrapy.crawler (Crawler + Runner/Process lifecycle)" inputs=[scrapy/crawler.py, pyproject.toml] mode=BLIND (code-only) date=2026-06-13 -->

# scrapy.crawler (Crawler + Runner/Process lifecycle)

Source: `C:/tmp/p5_scrapy_blind/scrapy/crawler.py`

## Role

Owns the top-level crawl lifecycle: a `Crawler` wires one spider class to its
settings, addons, signals, extensions, stats, and a single `ExecutionEngine`,
then drives open/start/stop; the Runner/Process subclasses manage a *set* of
crawlers and own reactor / asyncio-event-loop startup and shutdown-signal
handling — `scrapy/crawler.py:57` (class `Crawler`), `scrapy/crawler.py:191`
(`self.engine = self._create_engine`), `scrapy/crawler.py:766` & `:864`
(`CrawlerProcess.start` / `AsyncCrawlerProcess.start` run the reactor/loop).

## Dependencies (edges)

- imports the Spider base — `from scrapy import Spider` (`scrapy/crawler.py:15`); `Crawler.__init__(spidercls: type[Spider],...)` rejects instances (`scrapy/crawler.py:64-65`) and calls `spidercls.update_settings` / `spidercls.from_crawler` (`scrapy/crawler.py:72`, `:231`) → edge to `scrapy.spiders`.
- imports + instantiates the addon manager — `from scrapy.addons import AddonManager` (`scrapy/crawler.py:16`), `self.addons = AddonManager(self)` (`scrapy/crawler.py:75`), `AddonManager.load_pre_crawler_settings(settings)` (`scrapy/crawler.py:348`) → edge to `scrapy.addons`.
- imports + constructs the execution engine — `from scrapy.core.engine import ExecutionEngine` (`scrapy/crawler.py:17`), `return ExecutionEngine(self, lambda _: self.stop_async)` (`scrapy/crawler.py:234`) → edge to `scrapy.core` (engine).
- reaches transitively into the downloader/scraper sub-stacks via the engine object — `self.engine.downloader.middleware.middlewares` (`scrapy/crawler.py:289`), `self.engine.scraper.itemproc.middlewares` (`scrapy/crawler.py:324`), `self.engine.scraper.spidermw.middlewares` (`scrapy/crawler.py:341`) → runtime edges to `scrapy.core.downloader`, `scrapy.pipelines`, `scrapy.spidermiddlewares`, `scrapy.downloadermiddlewares` (the registries those managers hold).
- imports the extension manager — `from scrapy.extension import ExtensionManager` (`scrapy/crawler.py:19`), `self.extensions = ExtensionManager.from_crawler(self)` (`scrapy/crawler.py:146`) → edge to `scrapy.extensions` / extension core.
- imports the settings system — `from scrapy.settings import SETTINGS_PRIORITIES, Settings, overridden_settings` (`scrapy/crawler.py:20`), `settings.copy` / `freeze` / `getbool` (`scrapy/crawler.py:71`, `:147`, `:109`) → edge to `scrapy.settings`.
- imports the signal manager — `from scrapy.signalmanager import SignalManager` (`scrapy/crawler.py:21`), `self.signals = SignalManager(self)` (`scrapy/crawler.py:76`) → edge to signals core.
- imports the spider loader protocol + factory — `from scrapy.spiderloader import SpiderLoaderProtocol, get_spider_loader` (`scrapy/crawler.py:22`), `self.spider_loader = get_spider_loader(settings)` (`scrapy/crawler.py:350`), `self.spider_loader.load(spidercls)` (`scrapy/crawler.py:384`, `:758`) → edge to `scrapy.spiderloader` (scheduling/loader support).
- imports shared infra/reactor glue from `scrapy.utils` — `scrapy.utils.defer.deferred_from_coro` (`:23`), `scrapy.utils.log` (`:24-30`), `scrapy.utils.misc.{build_from_crawler, load_object}` (`:31`), `scrapy.utils.ossignal.{install_shutdown_handlers, signal_names}` (`:32`), `scrapy.utils.reactor.*` (`:33-41`), `scrapy.utils.reactorless.install_reactor_import_hook` (`:42`) → edge to `scrapy.utils`.
- imports the deprecation-warning class — `from scrapy.exceptions import ScrapyDeprecationWarning` (`scrapy/crawler.py:18`), used to deprecate `Crawler.stop`/`DNS_RESOLVER` (`scrapy/crawler.py:239-243`, `:670-675`) → edge to `scrapy.exceptions`.
- loads pluggable components by dotted path at runtime (late binding, not static imports) — `load_object(self.settings["STATS_CLASS"])` (`:99`), `["LOG_FORMATTER"]` (`:101`), `["REQUEST_FINGERPRINTER_CLASS"]` (`:104-105`), `["DNS_RESOLVER"]`/`["TWISTED_DNS_RESOLVER"]` resolver (`:687`) → dynamic edges to `scrapy.statscollectors`, `scrapy.logformatter`, `scrapy.utils.request` (fingerprinter), and the DNS resolver in `scrapy.resolver`.
- depends on Twisted as the async substrate — `from twisted.internet.defer import Deferred, DeferredList, inlineCallbacks` (`scrapy/crawler.py:13`) and lazy `from twisted.internet import reactor` (`scrapy/crawler.py:123`, `:635`, `:664`, `:713`, `:783`, `:1042`); manifest pins `Twisted>=21.7.0` (`pyproject.toml:10`) → external edge.

## Data

- Owns no persistence / DB. State is in-memory only: `self._crawlers: set[Crawler]` (`scrapy/crawler.py:351`) the live crawler registry, `self._active` the in-flight Deferred set (`scrapy/crawler.py:419`) or asyncio.Task set (`scrapy/crawler.py:519`), and `self.bootstrap_failed` flag (`scrapy/crawler.py:352`).
- Per-crawler component handles held in memory: `extensions/stats/logformatter/request_fingerprinter/spider/engine` all initialized to `None` then late-bound (`scrapy/crawler.py:82-87`).
- Reads configuration values from the `Settings` object (a key/value store, not a data store it owns): e.g. `STATS_CLASS`/`LOG_FORMATTER`/`REQUEST_FINGERPRINTER_CLASS` (`scrapy/crawler.py:99-105`), `TWISTED_REACTOR`/`ASYNCIO_EVENT_LOOP` (`scrapy/crawler.py:112-113`), `REACTOR_THREADPOOL_MAXSIZE` (`scrapy/crawler.py:694`).

## Boundary rules

- One reactor per process: `CrawlerProcess._create_crawler` sets `init_reactor` only for the FIRST crawler via `self._initialized_reactor` (`scrapy/crawler.py:756-761`); the reactor install must happen after settings merge but before any `twisted.internet.reactor` import (`scrapy/crawler.py:114-123`, comment `:116-117`).
- Reactor-enabled vs reactorless are mutually-exclusive regimes, hard-enforced: with `TWISTED_REACTOR_ENABLED=False` an installed reactor raises `RuntimeError` (`scrapy/crawler.py:139-142`, `:565-568`, `:843-846`); `CrawlerRunner` refuses `TWISTED_REACTOR_ENABLED=False` entirely (`scrapy/crawler.py:415-418`).
- `AsyncCrawlerRunner`/`AsyncCrawlerProcess` require the asyncio reactor specifically when reactor-enabled — `verify_installed_reactor(_asyncio_reactor_path)` / explicit `AsyncioSelectorReactor` check (`scrapy/crawler.py:559-564`, `:853`).
- `crawl`/`crawl_async` are once-only per Crawler instance — guarded by `self.crawling` and `self._started` raising `RuntimeError` (`scrapy/crawler.py:179-185`, `:209-215`).
- The `get_downloader_middleware`/`get_extension`/`get_item_pipeline`/`get_spider_middleware` accessors are gated on the engine/extensions existing and must only be called after engine creation (e.g. `scrapy/crawler.py:284-289`, `:319-324`, `:336-341`) — a temporal boundary on cross-component reach.
- Module-level import of `twisted.internet.reactor` is banned by lint (`pyproject.toml:407-413`), which is why this file imports the reactor lazily inside functions (`scrapy/crawler.py:635`, `:664`, `:713`, `:783`, `:1042`).
- Layering: this is the top of the runtime stack — it depends *down* on engine/settings/spiders/utils and is itself entered from the CLI (`scrapy = "scrapy.cmdline:execute"`, `pyproject.toml:64`); it does not import the CLI or commands.

## Key facts

- Dual API surface by design: Deferred-based `CrawlerRunner`/`CrawlerProcess` (`scrapy/crawler.py:397`, `:720`) vs coroutine-based `AsyncCrawlerRunner`/`AsyncCrawlerProcess` (`scrapy/crawler.py:494`, `:796`); `Crawler.crawl` (inlineCallbacks, `:171`) and `Crawler.crawl_async` (async, `:200`, "versionadded 2.14") are parallel implementations of the same lifecycle.
- The Process classes use cooperative multiple inheritance: `CrawlerProcess(CrawlerProcessBase, CrawlerRunner)` (`scrapy/crawler.py:720`) and `AsyncCrawlerProcess(CrawlerProcessBase, AsyncCrawlerRunner)` (`scrapy/crawler.py:796`), both rooted at `CrawlerRunnerBase(ABC)` (`scrapy/crawler.py:344`) — `crawl`, `start`, `_stop_dfd` are `@abstractmethod`s (`:387`, `:628`, `:701`).
- Two-phase signal shutdown: first SIGINT/SIGTERM → graceful stop (`_signal_shutdown` → `_graceful_stop_reactor`, `scrapy/crawler.py:634-639`, `:705-710`); a second signal forces an unclean kill (`_signal_kill`, `:641-646`); reactorless path mirrors this with `_signal_shutdown_reactorless`/`_signal_kill_reactorless` (`:1007`, `:1031`).
- `Crawler.stop` is deprecated in favor of `stop_async` (`scrapy/crawler.py:239-244`); the DNS_RESOLVER setting is deprecated in favor of TWISTED_DNS_RESOLVER (`scrapy/crawler.py:670-685`).
- `_apply_reactorless_default_settings` swaps the default HTTP/HTTPS download handlers to `HttpxDownloadHandler` and disables telnet + FTP when running without a Twisted reactor (`scrapy/crawler.py:154-166`).
- `AsyncCrawlerProcess._start_asyncio` deliberately re-implements a slice of `asyncio.runners.Runner` rather than calling `asyncio.run`, because `crawl` returns a Task that needs the loop created in `__init__` (`scrapy/crawler.py:891-997`, comment `:894-897`); `ASYNCIO_EVENT_LOOP` cannot be overridden by add-ons/spiders under this class (`scrapy/crawler.py:839-841`).
- Settings are frozen after `_apply_settings` (`scrapy/crawler.py:147`); `_apply_settings` is idempotent-guarded by `if self.settings.frozen: return` (`scrapy/crawler.py:95-96`).
- Components are pluggable via dotted-path settings resolved by `load_object` + `build_from_crawler` (`scrapy/crawler.py:31`, `:99-107`), the canonical Scrapy extensibility mechanism.
