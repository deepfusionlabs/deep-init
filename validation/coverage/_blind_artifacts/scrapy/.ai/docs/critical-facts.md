<!--
DeepInit provenance header
stage: blind-mirror-test
repo: scrapy@blind
doc_in_inputs: false
tier: deep (.ai/docs, on-demand)
note: key invariants / boundary rules / technology choices re-derived from CODE ONLY. Every claim cites a file:line.
-->

# Critical facts — scrapy (blind re-derivation)

## Technology choices (grounded to the manifest + code)

- **Async model: Twisted as the core async/reactor engine** — `pyproject.toml:10` Twisted>=21.7.0; the engine is built on twisted Deferred/inlineCallbacks — `scrapy/core/engine.py:19`.
- **asyncio integration: a Twisted asyncio reactor is the default** — `scrapy/utils/reactor.py:10` (`from twisted.internet import asyncioreactor`); tests force `--reactor=asyncio` — `pyproject.toml:260`; the engine also uses native asyncio — `scrapy/core/engine.py:10`. The default reactor constant is `twisted.internet.asyncioreactor.AsyncioSelectorReactor` — `scrapy/settings/default_settings.py:580`, `scrapy/utils/reactor.py:95`.
- **HTTP transport: built-in HTTP/1.1 and HTTP/2 download handlers** — `scrapy/settings/default_settings.py:289-291` (http11.HTTP11DownloadHandler, http2.HTTP2DownloadHandler), with a dedicated HTTP/2 stack in `scrapy/core/http2/` (agent/protocol/stream).
- **Additional transports/schemes: data:, file:, s3:, ftp: download handlers** — `scrapy/settings/default_settings.py:287-292`.
- **HTML/XML parsing & extraction: lxml + parsel + cssselect** — `pyproject.toml:14`, `:18`, `:13`; Selector wraps parsel's `_ParselSelector` — `scrapy/selector/unified.py:39`.
- **TLS/crypto: pyOpenSSL + cryptography + service_identity** — `pyproject.toml:11`, `:20`, `:22`; the downloader context factory at `scrapy/core/downloader/contextfactory.py`.
- **Signals/event bus: PyDispatcher (CPython) / PyPyDispatcher (PyPy) behind SignalManager** — `pyproject.toml:27-28`, `scrapy/signalmanager.py:14`.
- **Request queues / scheduling: queuelib disk+memory queues + priority queues** — `pyproject.toml:21`, `scrapy/squeues.py`, `scrapy/pqueues.py:52`. The default scheduler priority queue is DownloaderAwarePriorityQueue and the default dupefilter is RFPDupeFilter — `scrapy/settings/default_settings.py:533`, `:336`.
- **robots.txt: protego parser** — `pyproject.toml:19`, `scrapy/robotstxt.py:109` (ProtegoRobotParser).
- **Item adaptation/loading: itemadapter + itemloaders + w3lib** — `pyproject.toml:15`, `:16`, `:24`; ItemLoader at `scrapy/loader/__init__.py:20` (a thin subclass of upstream itemloaders.ItemLoader; manifest dep itemloaders>=1.0.1, `pyproject.toml:15`).
- **Secure XML parsing: defusedxml** — `pyproject.toml:12`; XmlRpcRequest hardens parsing with `defusedxml.monkey_patch` — `scrapy/http/request/rpc.py:18`, `:32-42`.
- **Interface contracts: zope.interface (e.g. IFeedStorage)** — `pyproject.toml:25`, `scrapy/extensions/feedexport.py:91`; the spider loader is verifyClass-checked against zope ISpiderLoader — `scrapy/spiderloader.py:29`.
- **Datastores are not bundled: persistence is pluggable file/ftp/s3 feed-export & httpcache backends, not a fixed DB** — `scrapy/settings/default_settings.py:378-381`.
- **License & Python support: BSD-3-Clause, requires-python >=3.10** — `pyproject.toml:49`, `:52`.
- **hyper-h2 (h2) for HTTP/2** is a hard import (`scrapy/core/http2/protocol.py:9-23`) but is NOT in `[project].dependencies` — HTTP/2 is effectively optional/transitive.

## Core invariants & boundary rules

### Engine / scheduling

- **Scheduler-interface contract enforced structurally:** `BaseSchedulerMeta` metaclass duck-types issubclass/isinstance (must have has_pending_requests/enqueue_request/next_request); the engine raises TypeError if the SCHEDULER class is not a BaseScheduler — `scrapy/core/scheduler.py:33-49`, `scrapy/core/engine.py:155-162`.
- **Collaborators are pluggable via settings + load_object, never hard-wired** (DOWNLOADER, SCHEDULER, ITEM_PROCESSOR, DUPEFILTER_CLASS, SCHEDULER_*_QUEUE) — `scrapy/core/engine.py:132`.
- **Concurrency substrate is a runtime switch:** the engine branches on `is_asyncio_available` (Deferred/inlineCallbacks vs `asyncio.ensure_future`) — `scrapy/core/engine.py:196-201`.
- **Request-processing loop** is a debounced `CallLaterOnce(self._start_scheduled_requests)` ("nextcall") plus a 5s heartbeat LoopingCall that re-schedules it — `scrapy/core/engine.py:103`, `:538`, `:299-308`.
- **Backpressure boundary:** the engine stops sending when `needs_backout` is true, ORing downloader and scraper-slot backout signals — `scrapy/core/engine.py:341-354`.
- **Default request order is LIFO/DFO:** the default Scheduler stores requests in priority queues that with default settings behave as a LIFO stack giving depth-first crawl order — `scrapy/core/scheduler.py:128-164`.
- **Priority convention:** stored priority is `-request.priority` and LOWER numbers are higher priority, one internal queue per priority value — `scrapy/pqueues.py:70-71`, `:166-167`.
- **Spider idleness + graceful close:** `spider_is_idle` checks scraper-slot idle + downloader inactive + start-iterator exhausted + scheduler empty; `_spider_idle` honors a DontCloseSpider veto and reads a custom reason from CloseSpider — `scrapy/core/engine.py:422-431`, `:560-583`.
- **Async-API migration boundary:** every public sync method is deprecated and delegates to an `_async` coroutine variant — `scrapy/core/engine.py:164-174`.

### Crawler / lifecycle

- **One reactor per process:** only the first crawler gets init_reactor via `self._initialized_reactor`; install must precede any `twisted.internet.reactor` import — `scrapy/crawler.py:756-761`, `:114-123`.
- **Reactor-enabled vs reactorless are mutually exclusive, hard-enforced with RuntimeError** — `scrapy/crawler.py:139-142`, `:565-568`, `:843-846`; CrawlerRunner refuses TWISTED_REACTOR_ENABLED=False — `scrapy/crawler.py:415-418`.
- **Module-level import of `twisted.internet.reactor` is lint-banned** (`pyproject.toml:407-413`), so the reactor is imported lazily inside functions — `scrapy/crawler.py:635`, `:664`, `:713`, `:783`; `ReactorImportHook` actively forbids that import in reactorless mode — `scrapy/utils/reactorless.py:33-47`.
- **crawl/crawl_async are once-only per Crawler instance**, guarded by `self.crawling`/`self._started` — `scrapy/crawler.py:179-185`, `:209-215`.
- **Settings are frozen after `_apply_settings`** (idempotent-guarded by `if self.settings.frozen: return`) — `scrapy/crawler.py:147`, `:95-96`.
- **Two-phase signal shutdown:** first signal -> graceful stop; second signal -> forced unclean kill; mirrored on the reactorless path — `scrapy/crawler.py:634-639`, `:705-710`, `:641-646`, `:1007`, `:1031`.
- **`_apply_reactorless_default_settings`** swaps HTTP/HTTPS download handlers to HttpxDownloadHandler and disables telnet+FTP when running without a Twisted reactor — `scrapy/crawler.py:154-166`.

### Settings

- **The priority ladder is the layering invariant:** `SETTINGS_PRIORITIES = {default:0, command:10, addon:15, project:20, spider:30, cmdline:40}`; a set only takes effect if the incoming priority >= the stored priority — `scrapy/settings/__init__.py:31`, `:69`.
- **Immutability gate:** every mutator routes through `_assert_mutability`, which raises TypeError once `freeze` sets `self.frozen=True` — `scrapy/settings/__init__.py:608`, `:624`.
- **`_BASE` convention:** framework component lists live in `*_BASE` settings, user overrides in the un-suffixed twin; `getwithbase` composes name_BASE then name so user entries win — `scrapy/settings/__init__.py:319`, `scrapy/settings/default_settings.py:315`.
- **Settings is a low-level leaf:** it imports only scrapy.exceptions and scrapy.utils, and must NOT import the components it configures (referenced only as import-string defaults to avoid cycles) — `scrapy/settings/__init__.py:12`, `scrapy/settings/default_settings.py:307`.
- **Typed accessors coerce env-var-style strings:** getbool accepts 0/1/'0'/'1'/True/False/'true'/'false'; getlist splits on ','; getdict/getdictorlist parse JSON — `scrapy/settings/__init__.py:171`, `:225`, `:270`.

### Middleware chains

- **Middleware-vs-runner split:** the chain packages hold the policies; the managers that order/drive them are separate components in scrapy.core, discovering hooks by duck-typed hasattr — `scrapy/core/downloader/middleware.py:34`, `:44-50`; `scrapy/core/spidermw.py:58-71`.
- **Downloader hook contract:** process_request/process_response/process_exception must return None/Response/Request else `_InvalidOutput` is raised; None=continue, Response/Request=short-circuit — `scrapy/core/downloader/middleware.py:107-111`, `:131-135`, `:149-153`.
- **Symmetric chain ordering:** process_request appended, process_response/process_exception appendleft (reverse order) — `scrapy/core/downloader/middleware.py:45-52`.
- **Priority-ordered chain, NOT import order:** integer priorities in DOWNLOADER_MIDDLEWARES_BASE (Offsite=50, RobotsTxt=100, Retry=550, Redirect=600, Cookies=700, HttpProxy=750, HttpCache=900) — `scrapy/settings/default_settings.py:317-330`; spider side in SPIDER_MIDDLEWARES_BASE (start=25, httperror=50, referer=700, urllength=800, depth=900) — `scrapy/settings/default_settings.py:553-558`.
- **`from_crawler` is the only construction boundary;** middlewares raise NotConfigured to opt out when their enable-setting is off — `scrapy/downloadermiddlewares/cookies.py:51`, `scrapy/spidermiddlewares/urllength.py:35-36`.
- **Spider middlewares never import the core runner — inversion of control:** SpiderMiddlewareManager loads them by import-path and dispatches hooks — `scrapy/core/spidermw.py:54-73`.
- **Spider middleware output-protocol enforcement:** middleware lacking async spider-output support raises TypeError; process_spider_input must return None or raise else `_InvalidOutput` — `scrapy/core/spidermw.py:258-265`, `:88-93`.
- **The downloadermiddlewares `__init__.py` is empty** (1 line) — each module is a standalone, independently-loadable component — `scrapy/downloadermiddlewares/__init__.py`.

### Security boundaries

- **HTTPS certificate verification is OFF by default:** `_ScrapyClientContextFactory` is non-peer-verifying, `DOWNLOAD_VERIFY_CERTIFICATES` defaults False, and `_ScrapyClientTLSOptions` deliberately catches VerificationError/CertificateError/ValueError to warn-not-fail — `scrapy/core/downloader/contextfactory.py:42-43`, `:76`, `:142-152`, `scrapy/core/downloader/tls.py:71-110`, `scrapy/settings/default_settings.py:305`.
- **Twisted-version-conditional TLS:** `_ScrapyClientTLSOptions26` vs `_ScrapyClientTLSOptions` via TWISTED_TLS_NEW_IMPL; `OP_LEGACY_SERVER_CONNECT (0x4)` forced on the SSL context — `scrapy/core/downloader/contextfactory.py:144-152`, `:259-265`, `scrapy/core/downloader/tls.py:121-179`.
- **HTTPS-over-proxy uses an HTTP CONNECT tunnel** (`_TunnelingTCP4ClientEndpoint`/`_TunnelingAgent`); HTTPS proxies for HTTPS destinations are explicitly unsupported — `scrapy/core/downloader/handlers/http11.py:165-259`, `:424-427`.
- **Cross-origin header-stripping on redirect:** Cookie dropped unless same-host + no scheme downgrade; Authorization dropped on any scheme/host/port change; proxy creds stripped on scheme change — `scrapy/downloadermiddlewares/redirect.py:132-174`.
- **HTTP/2 hostname firewall:** a stream refuses to send unless the request URL netloc matches the connection base URI host/netloc/ip, else closes INVALID_HOSTNAME — `scrapy/core/http2/stream.py:199-207`, `:260-269`. ALPN enforcement: only b'h2' is acceptable, non-h2 drops the connection without GOAWAY — `scrapy/core/http2/protocol.py:271-283`, `:482-483`.
- **Referrer-policy import-path classes from the response header are forbidden** (allow_import_path=False), allowed only from trusted settings — `scrapy/spidermiddlewares/referer.py:372`, `:410-424`.
- **Decompression-bomb guards:** httpcompression enforces DOWNLOAD_MAXSIZE raising IgnoreRequest on `_DecompressionMaxSizeExceeded` — `scrapy/downloadermiddlewares/httpcompression.py:32-59`, `:120-126`; SitemapSpider gunzips under a max_size cap (DOWNLOAD_MAXSIZE), silently dropping a sitemap on overflow — `scrapy/spiders/sitemap.py:119-138`.
- **Pickle trust boundary:** spider state, DBM cache, filesystem cache meta all use pickle protocol 4 with `loads` marked unsafe (`# noqa: S301`) — `scrapy/extensions/spiderstate.py:39`, `:44`, `scrapy/extensions/httpcache.py:293`, `:307`, `:368`, `:391`.
- **Telnet security:** when TELNETCONSOLE_PASSWORD is unset a random 8-byte hex password is generated per run and logged at INFO; the console exposes a live Python manhole over engine/crawler/stats — `scrapy/extensions/telnet.py:62-64`, `:96-122`.

### Data model (scrapy.http)

- **bytes is the on-the-wire boundary type:** Response.body rejects str; Headers normalizes all keys/values to bytes; decoding to text is exclusively TextResponse's job — `scrapy/http/response/__init__.py:128-138`, `scrapy/http/headers.py:43-68`, `scrapy/http/response/__init__.py:196-200`.
- **Text-only shortcuts gated by subtype:** base Response.css/xpath/jmespath raise NotSupported; only TextResponse and subclasses implement them — `scrapy/http/response/__init__.py:202-218`, `scrapy/http/response/text.py:155-166`.
- **URL invariant:** `_set_url` runs w3lib safe_url_string (unless meta['verbatim_url']) and raises 'Missing scheme' unless the URL has `://` or is about:/data: — `scrapy/http/request/__init__.py:255-272`.
- **NO_CALLBACK sentinel** marks requests with no spider callback and raises RuntimeError if ever invoked — `scrapy/http/request/__init__.py:60-81`.
- **`scrapy.Request` and `scrapy.http.Request` are the SAME class:** the root package imports the model FROM scrapy.http, so scrapy.http is the canonical home and scrapy.Request is an alias — `scrapy/__init__.py:10`.
- **The leaf data layer imports only scrapy.utils, scrapy.selector (lazy), scrapy.link, scrapy.exceptions and root scrapy for typing** — never engine/downloader/middleware/pipelines; it is imported BY them — `scrapy/__init__.py:10`.

### Spiders

- **Async-iterator start contract:** `start` is an async def yielding Request/items via AsyncIterator (versionadded 2.13); default reads start_urls and yields `Request(url, dont_filter=True)` — `scrapy/spiders/__init__.py:82-135`.
- **Mandatory name invariant:** construction raises `ValueError('... must have a name')` if neither passed nor class-set — `scrapy/spiders/__init__.py:45-49`.
- **Framework callback contract:** core calls the private `_parse` indirection (not parse directly); Spider._parse delegates to parse, subclasses override _parse for rule/feed/sitemap dispatch; the scraper binds to it — `scrapy/spiders/__init__.py:137-138`, `scrapy/spiders/crawl.py:116-122`, `scrapy/core/scraper.py:318`.
- **No-downward-coupling layering:** spiders import http/settings/utils/selector/linkextractors but never import scrapy.core.* at runtime — `scrapy/spiders/__init__.py:12-28`.
- **Circular-import workaround invariant:** Spider.logger imports SpiderLoggerAdapter inside the property body with a "# circular import" note — `scrapy/spiders/__init__.py:54-60`.
- **CrawlSpider rule engine:** `_compile_rules` deep-copies each rule into `self._rules` so per-instance compilation never mutates the class-level rules tuple — `scrapy/spiders/crawl.py:63-95`, `:213-218`.

### Pipelines

- **Pipelines are pluggable, priority-ordered components** discovered from ITEM_PIPELINES and composed via build_component_list; ordering (not hard-coded calls) defines the chain — `scrapy/pipelines/__init__.py:34`, `:37`.
- **Terminal/consumer end of item flow:** receives already-scraped items, transforms or drops them, never schedules crawl requests itself; media fetches are delegated outward to `engine.download_async` — `scrapy/pipelines/media.py:212`.
- **Media requests are isolated from spider callback flow:** created with `callback=NO_CALLBACK` and have callback/errback stripped before download so pipeline downloads never re-enter parsing — `scrapy/pipelines/files.py:713`, `scrapy/pipelines/media.py:157`.
- **Optional-dependency boundary:** a backend/feature self-disables by raising NotConfigured rather than crashing (missing botocore, unset FILES_STORE/IMAGES_STORE, missing Pillow) — `scrapy/pipelines/files.py:171`, `:477`, `scrapy/pipelines/images.py:77`.
- **Deduplication invariant:** concurrent same-fingerprint media requests are coalesced — first triggers the download, later ones attach a Deferred to `info.waiting[fp]`; result cached in `info.downloaded[fp]` and all waiters fired once — `scrapy/pipelines/media.py:177`, `:227`, `:261`.

### Extensions

- **Self-gating:** an extension that should not run raises `scrapy.exceptions.NotConfigured` in __init__/from_crawler rather than loading inert — `scrapy/extensions/closespider.py:58-59`, `scrapy/extensions/telnet.py:44-45`, `scrapy/extensions/feedexport.py:461-462`.
- **The extensions package does NOT load itself:** extensions are registered in EXTENSIONS_BASE and loaded by ExtensionManager which lives OUTSIDE this dir at `scrapy/extension.py:18`; the `scrapy/extensions/__init__.py` is empty — `scrapy/settings/default_settings.py:344-355`, `scrapy/extensions/__init__.py`.
- **AutoThrottle algorithm** deliberately will NOT decrease delay on non-200 responses to avoid positive-feedback delay collapse — `scrapy/extensions/throttle.py:104-129`.

### CLI

- **The single declared console entry point is `scrapy = "scrapy.cmdline:execute"`** — `pyproject.toml:63-64`.
- **Reactor selection is automatic:** AsyncCrawlerProcess when TWISTED_REACTOR is the asyncio reactor and FORCE_CRAWLER_PROCESS is off, else CrawlerProcess — `scrapy/cmdline.py:206-213`.
- **All commands subclass abstract ScrapyCommand;** run and short_desc are @abstractmethod — `scrapy/commands/__init__.py:27`, `:56-57`, `:141-146`.
- **Command discovery is convention-based:** one Command class per module under scrapy.commands, named by the module's last path segment, excluding base classes — `scrapy/cmdline.py:49`, `:54-60`.
- **Exit-code protocol:** each command sets `self.exitcode`, execute passes it to sys.exit; crawl/runspider set 1 on bootstrap_failed; UsageError exits 2 — `scrapy/cmdline.py:215`, `:166`, `scrapy/commands/crawl.py:33-34`.

### Utils (shared infra)

- **Dual concurrency model:** the package branches on `is_asyncio_available` to pick asyncio vs Twisted primitives (call_later, create_looping_call, run_in_thread) — `scrapy/utils/asyncio.py:234-251`, `:217-231`, `:296-313`, predicate at `:34`.
- **`deferred_from_coro` is the core Deferred<->coroutine bridge,** switching by reactor — `scrapy/utils/defer.py:391-403`.
- **`build_from_crawler`** prefers `objcls.from_crawler(crawler,...)` else `__init__`, raising TypeError on a None result (the framework from_crawler convention) — `scrapy/utils/misc.py:195-218`.
- **`load_object`** resolves an absolute dotted path to a class/function/variable/instance — the canonical plugin/component-loading primitive — `scrapy/utils/misc.py:58-90`.
- **datatypes.py declares a hard layering rule** in its docstring: "This module must not depend on any module outside the Standard Library." — `scrapy/utils/datatypes.py:5`.
- **Fail-loud boundary:** `is_asyncio_reactor_installed` raises RuntimeError instead of silently installing a default reactor (versionchanged 2.13) — `scrapy/utils/reactor.py:236-243`.
- **On Windows, install_reactor forces WindowsSelectorEventLoopPolicy** (twisted issue #12527 workaround) — `scrapy/utils/reactor.py:98-111`, `:118-123`.

### Scheduling support

- **DownloaderAwarePriorityQueue refuses CONCURRENT_REQUESTS_PER_IP != 0** (raises ValueError at construction) — `scrapy/pqueues.py:330-333`.
- **Resumed crawls must reuse the same priority-queue class:** non-dict slot_startprios rejected with an incompatible-priority-queue error — `scrapy/pqueues.py:335-344`.
- **Spider discovery is import-time eager:** SpiderLoader.__init__ walks all SPIDER_MODULES immediately, warns (not raises) on import/syntax errors only when SPIDER_LOADER_WARN_ONLY, and warns on duplicate spider names — `scrapy/spiderloader.py:62`, `:89-105`.

### Contracts

- **CLI/check-only layer:** invoked solely via the `scrapy check` command, which sets env SCRAPY_CHECK=true and monkey-patches `spidercls.start` to yield contract requests (not driven by the crawl engine) — `scrapy/commands/check.py:93`, `:96`, `:89-91`.
- **Async-callback exclusion:** a callback returning AsyncGenerator/CoroutineType raises `TypeError('Contracts don't support async callbacks')`, keeping the checker synchronous — `scrapy/contracts/__init__.py:53-54`, `:69-70`.
- **Request construction invariant:** built requests force `dont_filter=True` (so one URL can test multiple callbacks) and set callback=method — `scrapy/contracts/__init__.py:150-153`, `:161-162`, `:172`.

### Extensibility core

- **Dependency inversion at the layer boundary:** the MiddlewareManager base is subclassed inward by DownloaderMiddlewareManager (`scrapy/core/downloader/middleware.py:34`), SpiderMiddlewareManager (`scrapy/core/spidermw.py:48`), ExtensionManager (`scrapy/extension.py:18`), ItemPipelineManager (`scrapy/pipelines/__init__.py:31`); the Crawler owns the manager instances (`scrapy/crawler.py:75-76`) — `scrapy/middleware.py:35`.
- **Per-component graceful degradation:** NotConfigured while loading a middleware/add-on disables only that one (logged), never aborts the chain — `scrapy/middleware.py:98-104`, `scrapy/addons.py:42-48`.
- **The middleware chain is async-first:** `_process_chain` is async def, awaiting each method via ensure_awaitable, optionally injecting the spider as the trailing arg — `scrapy/middleware.py:131-153`.
- **Signals are duck-typed** (a signal is any object); PyDispatcher is the chosen backend, platform-split in the manifest (PyDispatcher on CPython, PyPyDispatcher on PyPy) — `scrapy/signalmanager.py:15`, `pyproject.toml:27-28`.

## Item-layer specifics

- **Field-name allowlist:** setting an undeclared key raises KeyError; only names in `fields` are accepted — `scrapy/item.py:94-98`.
- **ItemMeta metaclass** collects all Field-typed class attributes into the `fields` dict at class creation — `scrapy/item.py:28`, `:34-54`.
- **Item is a MutableMapping[str, Any] dict-like but NOT a dict** — `scrapy/item.py:57`, `:60-64`.
- **Adapter boundary:** exporters access every item only through `itemadapter.ItemAdapter`/`is_item`, staying type-agnostic across dict/dataclass/attrs/pydantic/Item — `scrapy/exporters.py:80`, `:363`.

## Extraction-layer specifics

- **Selector type is inferred from response class** (xml for XmlResponse, else html); explicit `type=` forces it — `scrapy/selector/unified.py:21`.
- **Public API alias:** LxmlLinkExtractor is exported as LinkExtractor, and lxml.html is the only/default extractor — `scrapy/linkextractors/__init__.py:128`, `:130`.
- **Only schemes {http, https, file, ftp} are followable** — `scrapy/linkextractors/__init__.py:124`.
- **A large default extension blocklist IGNORED_EXTENSIONS is applied** unless overridden by deny_extensions — `scrapy/linkextractors/__init__.py:18`, `scrapy/linkextractors/lxmlhtml.py:204`.
