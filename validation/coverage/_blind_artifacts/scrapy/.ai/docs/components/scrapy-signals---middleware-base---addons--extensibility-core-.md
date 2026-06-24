# Component: scrapy signals + middleware base + addons (extensibility core)

Derived BLIND from source only. Files in scope: `scrapy/middleware.py`, `scrapy/signalmanager.py`, `scrapy/addons.py`, manifest `pyproject.toml`.

## Role

- The shared, settings-driven plug-in machinery the whole framework reuses: an abstract `MiddlewareManager(ABC)` base that loads middleware classes from settings, builds them from the crawler, and runs their methods as an awaitable chain — `scrapy/middleware.py:35`.
- A PyDispatcher-backed `SignalManager` facade for connecting/disconnecting receivers and sending signals with catch-and-log semantics — `scrapy/signalmanager.py:14`.
- An `AddonManager` that loads add-on classes from the `ADDONS` setting and lets them mutate the `Settings` object before crawl — `scrapy/addons.py:18`.

## Dependencies (edges)

- → scrapy.utils (shared infrastructure): imports `ensure_awaitable` (`scrapy/middleware.py:11`), `argument_is_required` (`scrapy/middleware.py:12`), `build_from_crawler` + `load_object` (`scrapy/middleware.py:13`), `global_object_name` (`scrapy/middleware.py:14`).
- → scrapy.utils: `AddonManager` imports `build_component_list` (`scrapy/addons.py:7`) and `build_from_crawler` + `load_object` (`scrapy/addons.py:8`).
- → scrapy.utils: `SignalManager` delegates all sending to `scrapy.utils.signal` (imported as `_signal`) and uses `maybe_deferred_to_future` (`scrapy/signalmanager.py:10-11`); e.g. `send_catch_log` forwards to `_signal.send_catch_log` (`scrapy/signalmanager.py:52`).
- → scrapy signals + middleware base + addons (this extensibility core, internal): `signalmanager.py` re-exports the signal-sending utilities from `scrapy.utils.signal` (`scrapy/signalmanager.py:10`).
- → scrapy.settings (configuration system): `MiddlewareManager.from_crawler` reads `crawler.settings` and `_get_mwlist_from_settings(settings)` (`scrapy/middleware.py:84,89`); `AddonManager.load_settings`/`load_pre_crawler_settings` read `settings["ADDONS"]` (`scrapy/addons.py:35,69`); `Settings`/`BaseSettings` imported under TYPE_CHECKING (`scrapy/middleware.py:26`, `scrapy/addons.py:12`).
- → scrapy.crawler (Crawler lifecycle): `from_crawler(crawler)` is the construction entry point and `self.crawler` is stored (`scrapy/middleware.py:88-89,42`); `AddonManager.__init__` takes and stores a `Crawler` (`scrapy/addons.py:21-22`); `Crawler` imported under TYPE_CHECKING (`scrapy/middleware.py:25`, `scrapy/addons.py:11`). NOTE: at runtime the dependency is inverted — `scrapy/crawler.py:75-76` constructs `AddonManager(self)` and `SignalManager(self)`, so Crawler owns these objects.
- → scrapy.spiders (Spider base): `_spider`/`_set_compat_spider` access `crawler.spider` and the chain can append `self._spider` as an argument (`scrapy/middleware.py:59-80,149`); `Spider` imported under TYPE_CHECKING (`scrapy/middleware.py:24`).
- → scrapy (exceptions): imports `NotConfigured` + `ScrapyDeprecationWarning` (`scrapy/middleware.py:10`, `scrapy/addons.py:6`, `scrapy/signalmanager.py:9`); `NotConfigured` is caught during middleware/add-on load to skip-and-log disabled components (`scrapy/middleware.py:98`, `scrapy/addons.py:42`).
- → Twisted (manifest dep `Twisted>=21.7.0`, `pyproject.toml:10`): return types use `twisted.internet.defer.Deferred` (`scrapy/middleware.py:19,155,161`; `scrapy/signalmanager.py:7,56,109`).
- → PyDispatcher (manifest dep `PyDispatcher>=2.0.5`, `pyproject.toml:27`): `SignalManager` uses `pydispatch.dispatcher` for `connect`/`disconnect` and the default `dispatcher.Anonymous` sender (`scrapy/signalmanager.py:6,15,33,42`).
- NOTE (omission, R1): no outbound import edges to scrapy.core, scrapy.core.downloader, scrapy.core.http2, scrapy.cmdline/commands, scrapy.downloadermiddlewares, scrapy.spidermiddlewares, scrapy.pipelines, scrapy.extensions, scrapy.http, scrapy.selector/linkextractors, item/loader/exporters, queues/dupefilter/spiderloader, or scrapy.contracts. Those modules depend INWARD on this one — e.g. `DownloaderMiddlewareManager(MiddlewareManager)` (`scrapy/core/downloader/middleware.py:34`), `SpiderMiddlewareManager(MiddlewareManager)` (`scrapy/core/spidermw.py:48`), `ExtensionManager(MiddlewareManager)` (`scrapy/extension.py:18`), `ItemPipelineManager(MiddlewareManager)` (`scrapy/pipelines/__init__.py:31`).

## Data (data-stores / persistence)

- No external/persistent data store. State is in-memory only: `self.middlewares` tuple (`scrapy/middleware.py:51`), `self.methods` a `defaultdict(deque)` mapping method name → ordered callables (`scrapy/middleware.py:53`), `self._mw_methods_requiring_spider` set (`scrapy/middleware.py:54`).
- `AddonManager.addons` is an in-memory list of loaded add-on instances (`scrapy/addons.py:23`).
- The signal receiver registry is not owned here — it lives in PyDispatcher's global `dispatcher` (`scrapy/signalmanager.py:6,33`).

## Boundary rules

- Construction is settings-driven and crawler-scoped: managers are built via `from_crawler` which resolves class paths from settings, then `load_object` + `build_from_crawler` each one (`scrapy/middleware.py:88-114`); add-ons the same via `build_component_list(settings["ADDONS"])` (`scrapy/addons.py:35,69`).
- Graceful per-component degradation: a `NotConfigured` raised while loading any middleware or add-on disables only that component (logged), never aborts the chain (`scrapy/middleware.py:98-104`, `scrapy/addons.py:42-48`).
- Subclass contract: `_get_mwlist_from_settings` is `@classmethod @abstractmethod` — every concrete manager MUST supply its own settings key, and `component_name` is a required class attribute used in the "Enabled …" log line (`scrapy/middleware.py:38,82-85,109`).
- Deprecation firewall: a `crawler=None` construction, a `spider`-requiring middleware method, and `send_catch_log_deferred`/`open_spider`/`close_spider` all emit `ScrapyDeprecationWarning` rather than being removed outright (`scrapy/middleware.py:44-50,121-128,155-165`; `scrapy/signalmanager.py:68-72`).
- Spider access is mediated: `_spider` prefers `crawler.spider`, falls back to a legacy `_compat_spider`, else raises — middleware methods do not hold a Spider directly (`scrapy/middleware.py:58-80`).
- Add-on phasing: `load_pre_crawler_settings` (classmethod, no crawler) runs early settings that need no crawler instance, separate from `load_settings` which builds instances and calls `update_settings` (`scrapy/addons.py:25-48,57-72`).

## Key facts

- The middleware chain is async-first: `_process_chain` is an `async def` that awaits each method through `ensure_awaitable`, optionally injecting the spider as the trailing arg and emitting a deferred-return warning (`scrapy/middleware.py:131-153`).
- Method ordering is a `deque` per method name; only `process_spider_output` and `process_spider_exception` may be `None` in the chain (typed `Callable | None`) (`scrapy/middleware.py:52-53`).
- `_add_middleware` is a deliberate no-op hook (`# noqa: B027`) that subclasses override to register each middleware's methods (`scrapy/middleware.py:116-117`).
- Signals are duck-typed: a signal is "any object" and the manager keeps a per-instance `sender` (default `dispatcher.Anonymous`) auto-injected into every connect/disconnect/send via `kwargs.setdefault("sender",...)` (`scrapy/signalmanager.py:15,32,41,51,67,91,101`).
- `SignalManager.wait_for` builds a one-shot awaitable: a Twisted `Deferred` whose handler disconnects itself then fires, bridged to a future via `maybe_deferred_to_future` (`scrapy/signalmanager.py:104-116`).
- Two-tier signal-send evolution recorded in code: `send_catch_log` (sync), the deprecated `send_catch_log_deferred`, and the current async `send_catch_log_async` (added 2.14) all delegate to `scrapy.utils.signal` (`scrapy/signalmanager.py:44-92`).
- Typing-heavy generic chain: uses `Concatenate`, `ParamSpec`, `TypeVar`, and `cast` to type the per-method transform `obj -> obj` (`scrapy/middleware.py:8,31-32,140-142`).
- PyDispatcher is the chosen signal backend, platform-split in the manifest: `PyDispatcher` on CPython, `PyPyDispatcher` on PyPy (`pyproject.toml:27-28`).
- Package metadata: Scrapy 2.16.0, BSD-3-Clause, requires-python >=3.10, async test reactor `--reactor=asyncio` (`pyproject.toml:140,49,52`, `pyproject.toml:261`).
