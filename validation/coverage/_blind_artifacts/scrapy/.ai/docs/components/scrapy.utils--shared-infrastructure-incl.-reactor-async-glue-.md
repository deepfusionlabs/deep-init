<!-- DEEPINIT:START -->
<!--
provenance:
 stage: extract (BLIND re-derivation from code only)
 component: scrapy.utils (shared infrastructure incl. reactor/async glue)
 path: scrapy/utils/
 inputs: scrapy/utils/*.py + pyproject.toml + scrapy/core/engine.py (import block)
 date: 2026-06-13
 doc_in_inputs: false
-->

# scrapy.utils — shared infrastructure (incl. reactor/async glue)

## Role

- Leaf-level support package that supplies the framework-wide primitives every other component reuses: the Twisted-reactor/asyncio install + interop layer, the Deferred<->coroutine/Future bridge, dynamic object loading, config/log/version helpers, and assorted parsing/datatype utilities — e.g. `load_object` resolves an absolute dotted path to a class/function/instance, the canonical plugin-loading primitive. `scrapy/utils/misc.py:58` (`def load_object`), `scrapy/utils/reactor.py:114` (`def install_reactor`), `scrapy/utils/defer.py:391` (`def deferred_from_coro`).

## Dependencies (edges)

- → **scrapy.settings (configuration system)**: imports the settings classes used by config/log/version helpers — `from scrapy.settings import BaseSettings`, `from scrapy.settings import Settings`, and `from scrapy.settings.default_settings import LOG_VERSIONS`. `scrapy/utils/conf.py:12`, `scrapy/utils/log.py:15`, `scrapy/utils/versions.py:9`.
- → **scrapy.http (Request/Response model + cookies/headers)**: iterators/serialize/response/gz/httpobj helpers import the HTTP model — `from scrapy.http import Response, TextResponse` and `from scrapy.http import Request, Response`. `scrapy/utils/iterators.py:13`, `scrapy/utils/serialize.py:9`, `scrapy/utils/response.py:23` (TYPE_CHECKING), `scrapy/utils/gz.py:11` (TYPE_CHECKING), `scrapy/utils/httpobj.py:10` (TYPE_CHECKING); `datatypes.py` also lazy-imports `scrapy.http.headers.Headers` inside `CaselessDict.__new__` at `scrapy/utils/datatypes.py:36`.
- → **scrapy item + loader + exporters (item data layer)**: `misc.py` imports the Item base at module level — `from scrapy.item import Item` (used by `arg_to_iter`'s single-value set). `scrapy/utils/misc.py:19`, `scrapy/utils/misc.py:30`.
- → **scrapy.selector + scrapy.linkextractors (extraction)**: the XML/CSV iterator helpers import the Selector — `from scrapy.selector import Selector`. `scrapy/utils/iterators.py:14`.
- → **scrapy.spiders (Spider base + built-in spider types)**: `spider.py` imports the Spider base — `from scrapy.spiders import Spider`; `request.py` imports `from scrapy import Request, Spider`. `scrapy/utils/spider.py:7`, `scrapy/utils/request.py:16`.
- → **scrapy queues + dupefilter + spiderloader (scheduling support)**: `spider.py` references the spider-loader protocol — `from scrapy.spiderloader import SpiderLoaderProtocol` (TYPE_CHECKING). `scrapy/utils/spider.py:18`.
- → **scrapy.crawler (Crawler + Runner/Process lifecycle)**: `test.py` imports the runner classes at module level — `from scrapy.crawler import AsyncCrawlerRunner, CrawlerRunner, CrawlerRunnerBase`; multiple helpers type-hint `Crawler` (e.g. `build_from_crawler`). `scrapy/utils/test.py:16`, `scrapy/utils/misc.py:27` (TYPE_CHECKING), `scrapy/utils/log.py:21` (TYPE_CHECKING), `scrapy/utils/request.py:27` (TYPE_CHECKING), `scrapy/utils/_download_handlers.py:37` (TYPE_CHECKING).
- → **scrapy.core (engine/scheduler/scraper/spider-middleware runner)**: `engine.py` (the debug helper) type-imports the execution engine and reads its internals — `from scrapy.core.engine import ExecutionEngine`, then `get_engine_status` evals `engine.downloader.active`, `engine.scraper.is_idle`, `engine._slot.scheduler.mqs`, etc. `scrapy/utils/engine.py:10`, `scrapy/utils/engine.py:13-30`.
- → **scrapy.extensions (lifecycle extensions / feed export / telnet)**: `conf.py` supplies the feed-export param helpers consumed by the feed system, reading FEED_* settings. `scrapy/utils/conf.py:127` (`feed_complete_default_values_from_settings`), `scrapy/utils/conf.py:144` (`feed_process_params_from_cli`).
- → **scrapy.logformatter** (extensibility/log layer): `log.py` type-imports the formatter result — `from scrapy.logformatter import LogFormatterResult`. `scrapy/utils/log.py:22`.
- → **scrapy.responsetypes**: `_download_handlers.py` imports the response-type registry — `from scrapy import responsetypes`. `scrapy/utils/_download_handlers.py:17`.
- → **scrapy.exceptions** (shared exception module): imported pervasively for `ScrapyDeprecationWarning`, `UsageError`, `NotConfigured`, `StopDownload`, the download-error family, etc. `scrapy/utils/conf.py:11`, `scrapy/utils/misc.py:18`, `scrapy/utils/signal.py:23`, `scrapy/utils/_download_handlers.py:18-26`.
- → external **Twisted** (declared `Twisted>=21.7.0`): the reactor/Deferred/Cooperator/LoopingCall substrate — `from twisted.internet import asyncioreactor, error`, `from twisted.internet.defer import Deferred`, `from twisted.internet.task import Cooperator`, `LoopingCall`. `pyproject.toml:10`, `scrapy/utils/reactor.py:10-11`, `scrapy/utils/defer.py:25-27`, `scrapy/utils/asyncio.py:11-13`.
- NOTE (in-degree, not an outgoing edge): `scrapy.core.engine` imports 7 distinct utils modules (`asyncio`, `defer`, `deprecate`, `log`, `misc`, `python`, `reactor`) — `scrapy/core/engine.py:32-47` — corroborating that utils is a depended-upon leaf, not a dependent of core (except the `engine.py` debug helper above).

## Data

- Owns an in-process **live-instance registry** (not persisted): `live_refs: defaultdict[type, WeakKeyDictionary[object, float]]`, populated by `object_ref.__new__` recording a monotonic timestamp per live instance. `scrapy/utils/trackref.py:33`, `scrapy/utils/trackref.py:43-46`.
- Owns a bounded in-process **AST/generator-introspection cache**: `_generator_callbacks_cache = LocalWeakReferencedCache(limit=128)`. `scrapy/utils/misc.py:255`.
- Reads (does not own) the on-disk **`scrapy.cfg`** config file via ConfigParser, searching project dir + `/etc/scrapy.cfg`, `c:\scrapy\scrapy.cfg`, `$XDG_CONFIG_HOME`, `~/.scrapy.cfg`. `scrapy/utils/conf.py:73` (`closest_scrapy_cfg`), `scrapy/utils/conf.py:104` (`get_config`), `scrapy/utils/conf.py:112-124` (`get_sources`).
- Reads/writes process **environment variables**: sets `SCRAPY_SETTINGS_MODULE` / mutates `sys.path` in `init_env`, and a `set_environ` context manager that saves+restores env. `scrapy/utils/conf.py:89` (`init_env`), `scrapy/utils/misc.py:221` (`set_environ`).
- No database / queue persistence is owned here (`information_schema`/SQL/queue files absent from this package).

## Boundary rules

- Lowest layer / leaf: most cross-component references are deferred behind `if TYPE_CHECKING:` or function-local imports to keep utils importable early and break cycles — e.g. `from scrapy.utils.asyncio import call_later # noqa: PLC0415` inside `CallLaterOnce.schedule`, and `from scrapy.utils.defer import maybe_deferred_to_future` inside `run_in_thread`. `scrapy/utils/reactor.py:64`, `scrapy/utils/asyncio.py:311`.
- `datatypes.py` declares a hard layering rule in its module docstring: "This module must not depend on any module outside the Standard Library." `scrapy/utils/datatypes.py:5`.
- **Reactor-singleton boundary**: `twisted.internet.reactor` is never imported at module top level — only function-locally (`from twisted.internet import reactor`) — because importing it installs the reactor as a global side effect. `scrapy/utils/reactor.py:32`, `scrapy/utils/reactor.py:178`, `scrapy/utils/defer.py:61`. The `ReactorImportHook` MetaPathFinder actively *forbids* that import in reactorless mode. `scrapy/utils/reactorless.py:33-47`.
- `is_asyncio_reactor_installed` raises `RuntimeError` rather than silently installing a default reactor (a deliberate fail-loud boundary, "versionchanged 2.13"). `scrapy/utils/reactor.py:236-243`.

## Key facts

- Dual concurrency model: the whole package branches on `is_asyncio_available` (true if a running asyncio loop exists OR an `AsyncioSelectorReactor` is installed) to pick asyncio vs Twisted primitives — `call_later` → `loop.call_later` vs `reactor.callLater`; `create_looping_call` → `AsyncioLoopingCall` vs Twisted `LoopingCall`; `run_in_thread` → `asyncio.to_thread` vs `deferToThread`. `scrapy/utils/asyncio.py:34`, `scrapy/utils/asyncio.py:234-251`, `scrapy/utils/asyncio.py:217-231`, `scrapy/utils/asyncio.py:296-313`.
- `deferred_from_coro` is the core Deferred<->coroutine bridge and switches strategy by reactor: with asyncio it wraps via `Deferred.fromFuture(asyncio.ensure_future(o))` (requires AsyncioSelectorReactor); without, `Deferred.fromCoroutine(o)` (noted as broken for coroutines that `await asyncio.sleep`). `scrapy/utils/defer.py:391-403`.
- `maybe_deferred_to_future` / `deferred_to_future` are the reactor-agnostic await wrappers: under asyncio you can only await Futures (`d.asFuture(asyncio.get_event_loop)`), otherwise you await the raw Deferred. `scrapy/utils/defer.py:469-524`.
- The asyncio reactor path is `twisted.internet.asyncioreactor.AsyncioSelectorReactor`; on Windows `install_reactor` first forces `WindowsSelectorEventLoopPolicy` (workaround for twisted issue #12527). `scrapy/utils/reactor.py:95`, `scrapy/utils/reactor.py:98-111`, `scrapy/utils/reactor.py:118-123`.
- `CallLaterOnce` is the de-bounced reactor-loop scheduler (schedules `func` for the next loop only if not already scheduled) — a key engine primitive (imported by `scrapy/core/engine.py:47`). `scrapy/utils/reactor.py:50-92`.
- `CallLaterResult` is a unified handle abstracting `asyncio.TimerHandle` vs Twisted `DelayedCall` so callers get one `.cancel` API regardless of loop. `scrapy/utils/asyncio.py:254-293`.
- `parallel` / `parallel_async` cap concurrency via Twisted `Cooperator.coiterate`; `_AsyncCooperatorAdapter` serializes `__anext__` because async generators can't be awaited in parallel. `scrapy/utils/defer.py:159-173`, `scrapy/utils/defer.py:176-295`.
- `_parallel_asyncio` is the asyncio-native bounded fan-out (an `asyncio.Queue` + N worker tasks), documented as used only by `Scraper.handle_spider_output_async`. `scrapy/utils/asyncio.py:95-130`.
- Many `defer.py` helpers (`defer_fail`, `defer_succeed`, `mustbe_deferred`, `process_chain`, `process_parallel`, `maybeDeferred_coro`) are deprecated shims emitting `ScrapyDeprecationWarning`, signalling a migration away from Deferred-chaining toward coroutines. `scrapy/utils/defer.py:54-59`, `scrapy/utils/defer.py:145-150`, `scrapy/utils/defer.py:305-309`, `scrapy/utils/defer.py:426-430`.
- `get_engine_status` reflectively `eval`s a hard-coded list of engine-internal expressions (e.g. `engine._slot.scheduler.mqs`), so it is tightly (informally) coupled to scrapy.core internals despite living in utils. `scrapy/utils/engine.py:15-35`.
- `build_from_crawler` is the standard component-construction primitive: prefers `objcls.from_crawler(crawler,...)`, else `__init__`, raising `TypeError` if the result is None (the framework's from_crawler convention). `scrapy/utils/misc.py:195-218`.
<!-- DEEPINIT:END -->
