<!--
DeepInit provenance header
stage: blind-mirror-test
repo: scrapy@blind
doc_in_inputs: false
tier: deep (.ai/docs, on-demand)
note: every edge is grounded to a file:line re-derived from CODE ONLY. Format: A -> B (kind) — file:line.
-->

# Technical dependencies — scrapy (blind re-derivation)

Each edge below was re-derived from source imports / runtime calls; `kind` is recorded as in the structured facts. "INBOUND" / "project-ref (inbound)" marks edges where the named target consumes the source (an inversion), recorded for context.

## scrapy.core (engine / scheduler / scraper / spider-middleware runner)

- scrapy.core -> scrapy.core.downloader (import + runtime-call: load_object DOWNLOADER,.fetch/.needs_backout/.close) — `scrapy/core/engine.py:132`
- scrapy.core -> scrapy.crawler (import + runtime-call: crawler.settings/.signals/.stats/.spider/.engine) — `scrapy/core/engine.py:112`
- scrapy.core -> scrapy.spiders (import + runtime-call: spider._parse, spider.start) — `scrapy/core/scheduler.py:12`
- scrapy.core -> scrapy.pipelines (import + runtime-call: load_object ITEM_PROCESSOR, process_item_async) — `scrapy/core/scraper.py:24`
- scrapy.core -> scrapy.http (import + isinstance type-dispatch) — `scrapy/core/engine.py:31`
- scrapy.core -> scrapy signals + middleware base + addons (import + runtime-call: signals via crawler.signals; SpiderMiddlewareManager extends MiddlewareManager) — `scrapy/core/spidermw.py:22`
- scrapy.core -> scrapy.settings (runtime-call: crawler.settings[...] / getbool / getint) — `scrapy/core/scheduler.py:255`
- scrapy.core -> scrapy.utils (import: CallLaterOnce, create_looping_call, deferred helpers, load_object/build_from_crawler, job_dir) — `scrapy/core/engine.py:32`
- scrapy.core -> scrapy queues + dupefilter + spiderloader (import + runtime-call: ScrapyPriorityQueue, BaseDupeFilter via DUPEFILTER_CLASS/SCHEDULER_*_QUEUE) — `scrapy/core/scheduler.py:26`
- scrapy.core -> scrapy.extensions (runtime-call: statscollectors via crawler.stats inc_value) — `scrapy/core/scheduler.py:380`

## scrapy.core.downloader (downloader + handlers + TLS)

- scrapy.core.downloader -> scrapy.http (import) — `scrapy/core/downloader/middleware.py:14`
- scrapy.core.downloader -> scrapy signals + middleware base + addons (import / project-ref / runtime-call) — `scrapy/core/downloader/middleware.py:15`
- scrapy.core.downloader -> scrapy signals + middleware base + addons (queue-event: signal send) — `scrapy/core/downloader/__init__.py:182`
- scrapy.core.downloader -> scrapy.settings (runtime-call: settings read) — `scrapy/core/downloader/__init__.py:110`
- scrapy.core.downloader -> scrapy.utils (import) — `scrapy/core/downloader/__init__.py:17`
- scrapy.core.downloader -> scrapy.core.http2 (import) — `scrapy/core/downloader/handlers/http2.py:9`
- scrapy.core.downloader -> scrapy.crawler (import / runtime-call: constructor takes Crawler) — `scrapy/core/downloader/__init__.py:103`
- scrapy.core.downloader -> scrapy queues + dupefilter + spiderloader (import / db-read: DNS cache) — `scrapy/core/downloader/__init__.py:16`
- scrapy.core.downloader -> scrapy item + loader + exporters (import / runtime-call: responsetypes) — `scrapy/core/downloader/handlers/ftp.py:44`
- scrapy.core.downloader -> scrapy signals + middleware base + addons (import: exceptions) — `scrapy/core/downloader/handlers/__init__.py:11`

## scrapy.core.http2 (HTTP/2 client stack)

- scrapy.core.http2 -> scrapy.core.downloader (import: TLS context-factory helper) — `scrapy/core/http2/agent.py:17`
- scrapy.core.http2 -> scrapy.http (import) — `scrapy/core/http2/protocol.py:36`
- scrapy.core.http2 -> scrapy.settings (runtime-call: settings.getbool/getint) — `scrapy/core/http2/agent.py:46-48`
- scrapy.core.http2 -> scrapy.utils (import: _download_handlers, httpobj, deprecate, ssl) — `scrapy/core/http2/stream.py:17-22`
- scrapy.core.http2 -> scrapy signals + middleware base + addons (import: scrapy.exceptions) — `scrapy/core/http2/protocol.py:35`
- scrapy.core.http2 -> scrapy.spiders (import TYPE_CHECKING + getattr read of download_maxsize/warnsize) — `scrapy/core/http2/protocol.py:200-217`

## scrapy.crawler (Crawler + Runner/Process lifecycle)

- scrapy.crawler -> scrapy.spiders (import) — `scrapy/crawler.py:15`
- scrapy.crawler -> scrapy.addons (import) — `scrapy/crawler.py:16`
- scrapy.crawler -> scrapy.core (import + runtime-call) — `scrapy/crawler.py:17`
- scrapy.crawler -> scrapy.core.downloader (runtime-call) — `scrapy/crawler.py:289`
- scrapy.crawler -> scrapy.pipelines (runtime-call) — `scrapy/crawler.py:324`
- scrapy.crawler -> scrapy.spidermiddlewares (runtime-call) — `scrapy/crawler.py:341`
- scrapy.crawler -> scrapy.downloadermiddlewares (runtime-call) — `scrapy/crawler.py:289`
- scrapy.crawler -> scrapy.extensions (import) — `scrapy/crawler.py:19`
- scrapy.crawler -> scrapy.settings (import) — `scrapy/crawler.py:20`
- scrapy.crawler -> scrapy signals + middleware base + addons (import) — `scrapy/crawler.py:21`
- scrapy.crawler -> scrapy queues + dupefilter + spiderloader (import) — `scrapy/crawler.py:22`
- scrapy.crawler -> scrapy.utils (import) — `scrapy/crawler.py:23`
- scrapy.crawler -> scrapy.http (runtime-call) — `scrapy/crawler.py:104`

## scrapy.cmdline + scrapy.commands (CLI)

- scrapy.cmdline -> scrapy.crawler (import + runtime-instantiation) — `scrapy/cmdline.py:13`, `scrapy/cmdline.py:206-213`
- scrapy.cmdline -> scrapy.settings (import + runtime-call: get_project_settings / setdict / setting reads) — `scrapy/cmdline.py:16`, `:174`, `:200`, `:208-210`
- scrapy.cmdline -> scrapy.utils (import: walk_modules_iter / project / python / reactor / conf / defer) — `scrapy/cmdline.py:15-18`, `scrapy/commands/__init__.py:18`, `scrapy/commands/shell.py:17`, `scrapy/commands/parse.py:18`
- scrapy.cmdline -> scrapy.core (runtime-call: engine create/start, scraper.itemproc) — `scrapy/commands/shell.py:99-100`, `:112-114`, `scrapy/commands/parse.py:284-291`
- scrapy.cmdline -> scrapy.http (import: Request/Response/TextResponse) — `scrapy/commands/fetch.py:11`, `scrapy/commands/parse.py:15`, `scrapy/commands/shell.py:15`, `scrapy/commands/bench.py:11`
- scrapy.cmdline -> scrapy.spiders (import + runtime-call: spider classes / loader / spidercls_for_request) — `scrapy/commands/runspider.py:10-11`, `scrapy/commands/fetch.py:13`, `scrapy/commands/list.py:6`, `scrapy/commands/check.py:87`
- scrapy.cmdline -> scrapy.contracts (import + runtime-call: ContractsManager) — `scrapy/commands/check.py:11`, `:79`
- scrapy.cmdline -> scrapy.linkextractors (import: LinkExtractor in bench spider) — `scrapy/commands/bench.py:12`, `:59`
- scrapy.cmdline -> scrapy.shell (import + runtime-call: interactive Shell) — `scrapy/commands/shell.py:16`, `:94`
- scrapy.cmdline -> scrapy.exceptions (import: UsageError / ScrapyDeprecationWarning) — `scrapy/cmdline.py:14`, `scrapy/commands/__init__.py:17`
- scrapy.cmdline -> scrapy (top-level package) (import: __version__ / __path__ / Spider / Request) — `scrapy/cmdline.py:11`, `:101`, `scrapy/commands/startproject.py:11`, `scrapy/commands/version.py:4`
- scrapy.cmdline -> scrapy item data layer (import: ItemAdapter to render scraped items) — `scrapy/commands/parse.py:9`, `:173`

## scrapy.spiders (Spider base + built-in spider types)

- scrapy.spiders -> scrapy.http (import) — `scrapy/spiders/__init__.py:13`
- scrapy.spiders -> scrapy signals + middleware base + addons (import + signal-connect) — `scrapy/spiders/__init__.py:12`, `:80`
- scrapy.spiders -> scrapy.utils (import) — `scrapy/spiders/__init__.py:14`
- scrapy.spiders -> scrapy.crawler (runtime-call: from_crawler reads crawler.settings) — `scrapy/spiders/__init__.py:72-80`
- scrapy.spiders -> scrapy.settings (runtime-call: settings.setdict / getbool / getint) — `scrapy/spiders/__init__.py:79`, `:150-151`
- scrapy.spiders -> scrapy.selector + scrapy.linkextractors (import + instantiate: LinkExtractor/Selector) — `scrapy/spiders/crawl.py:17-18`, `:60`
- scrapy.spiders -> scrapy.exceptions (import) — `scrapy/spiders/feed.py:12`
- scrapy.spiders -> scrapy.core (runtime-call, INBOUND: scraper binds spider._parse, spidermw consumes spider.start) — `scrapy/core/scraper.py:318`

## scrapy.downloadermiddlewares (request/response middleware chain)

- scrapy.downloadermiddlewares -> scrapy.core.downloader (runtime-call: manager runs the hooks) — `scrapy/core/downloader/middleware.py:44`
- scrapy.downloadermiddlewares -> scrapy.crawler (runtime-call: from_crawler factory) — `scrapy/downloadermiddlewares/cookies.py:50`
- scrapy.downloadermiddlewares -> scrapy.core (runtime-call: engine.download_async for robots.txt) — `scrapy/downloadermiddlewares/robotstxt.py:100`
- scrapy.downloadermiddlewares -> scrapy.spidermiddlewares (import + runtime-call: RefererMiddleware for redirect Referer) — `scrapy/downloadermiddlewares/redirect.py:12`
- scrapy.downloadermiddlewares -> scrapy.http (import + construct: Response, CookieJar, Request) — `scrapy/downloadermiddlewares/cookies.py:10`
- scrapy.downloadermiddlewares -> scrapy.settings (import + read: BaseSettings, SETTINGS_PRIORITIES, getbool/getint) — `scrapy/downloadermiddlewares/httpauth.py:16`
- scrapy.downloadermiddlewares -> scrapy signals + middleware base + addons (import + connect: signals.spider_opened/engine_started/request_scheduled) — `scrapy/downloadermiddlewares/httpcache.py:56`
- scrapy.downloadermiddlewares -> scrapy.utils (import: _warn_spider_arg, urlparse_cached, load_object, maybe_deferred_to_future) — `scrapy/downloadermiddlewares/cookies.py:12`
- scrapy.downloadermiddlewares -> scrapy.spiders (runtime-call: reads spider attrs e.g. allowed_domains, spider.crawler) — `scrapy/downloadermiddlewares/offsite.py:75`

## scrapy.spidermiddlewares (spider-input/output middleware chain)

- scrapy.spidermiddlewares -> scrapy.http (import) — `scrapy/spidermiddlewares/referer.py:15`
- scrapy.spidermiddlewares -> scrapy.spiders (import via scrapy top-level re-export) — `scrapy/__init__.py:13`
- scrapy.spidermiddlewares -> scrapy.utils (import) — `scrapy/spidermiddlewares/base.py:6`
- scrapy.spidermiddlewares -> scrapy.settings (runtime-call: settings.get*) — `scrapy/spidermiddlewares/depth.py:48-50`
- scrapy.spidermiddlewares -> scrapy.crawler (runtime-call: from_crawler factory; crawler.settings/stats/spider) — `scrapy/spidermiddlewares/depth.py:46-53`
- scrapy.spidermiddlewares -> scrapy signals + middleware base + addons (import: exceptions IgnoreRequest/NotConfigured) — `scrapy/spidermiddlewares/httperror.py:12`
- scrapy.spidermiddlewares -> scrapy.core (runtime-call, INVERSION: SpiderMiddlewareManager loads these classes by import-path and dispatches their hooks; no compile-time edge out) — `scrapy/core/spidermw.py:54-73`

## scrapy.pipelines (item pipelines incl. media/files/images)

- scrapy.pipelines -> scrapy signals + middleware base + addons (import / class-inheritance: MiddlewareManager) — `scrapy/pipelines/__init__.py:16`, subclass at `scrapy/pipelines/__init__.py:31`, base at `scrapy/middleware.py:35`
- scrapy.pipelines -> scrapy.core (runtime-call: await self.crawler.engine.download_async(request)) — `scrapy/pipelines/media.py:212`, target `scrapy/core/engine.py:464`
- scrapy.pipelines -> scrapy.crawler (runtime-call / from_crawler) — `scrapy/pipelines/media.py:70`, `:83`, `:120`, `scrapy/pipelines/files.py:502`
- scrapy.pipelines -> scrapy.http (import / runtime-call: Request, Response) — `scrapy/pipelines/files.py:28`, build at `files.py:713`, consumed at `scrapy/pipelines/media.py:281`
- scrapy.pipelines -> scrapy.settings (import / runtime-read: ITEM_PIPELINES, getbool/getint) — `scrapy/pipelines/__init__.py:37`, `scrapy/pipelines/media.py:93`, `scrapy/pipelines/files.py:506`/`:514`, `scrapy/pipelines/images.py:116`, default at `scrapy/settings/default_settings.py:432`
- scrapy.pipelines -> scrapy.utils (import) — `scrapy/pipelines/__init__.py:17-20`, `scrapy/pipelines/media.py:17-29`, `scrapy/pipelines/files.py:31-39`
- scrapy.pipelines -> scrapy item + loader + exporters (import / runtime-call: ItemAdapter) — `scrapy/pipelines/files.py:24`, read at `files.py:708`, write-back at `files.py:729` and `scrapy/pipelines/images.py:226`

## scrapy.extensions (lifecycle extensions / feed export / telnet)

- scrapy.extensions -> scrapy signals + middleware base + addons (import / runtime-call: signal connect+send) — `scrapy/extensions/corestats.py:11`, `:31-35`, `scrapy/extensions/feedexport.py:538`, `:578-580`
- scrapy.extensions -> scrapy.crawler (import / runtime-call: sole injected dep) — `scrapy/extensions/feedexport.py:43`, `:453-455`, `scrapy/extensions/telnet.py:32`, `:43`
- scrapy.extensions -> scrapy.core (runtime-call: engine.close_spider_async / read engine state) — `scrapy/extensions/closespider.py:148-150`, `scrapy/extensions/memusage.py:124-129`
- scrapy.extensions -> scrapy.core.downloader (import / runtime-call: read+mutate slots) — `scrapy/extensions/throttle.py:13`, `:101-102`, `:129`
- scrapy.extensions -> scrapy.settings (runtime-call: settings gating/config + type import) — `scrapy/extensions/closespider.py:48-55`, `scrapy/extensions/feedexport.py:461`, `:495-498`
- scrapy.extensions -> scrapy.utils (import / runtime-call) — `scrapy/extensions/feedexport.py:30-35`, `scrapy/extensions/telnet.py:22-24`, `scrapy/extensions/closespider.py:15-21`
- scrapy.extensions -> scrapy.spiders (import: lifecycle handle type) — `scrapy/extensions/corestats.py:11`, `scrapy/extensions/feedexport.py:27`, `scrapy/extensions/httpcache.py:28`
- scrapy.extensions -> scrapy.http (import) — `scrapy/extensions/httpcache.py:15`, `:26`, `scrapy/extensions/closespider.py:13`
- scrapy.extensions -> scrapy item + loader + exporters (import / runtime-call: build+drive BaseItemExporter) — `scrapy/extensions/feedexport.py:44`, `:430-435`, `:626`
- scrapy.extensions -> scrapy.utils (import: responsetypes via adjacent infra + reactor.listen_tcp) — `scrapy/extensions/httpcache.py:16`, `scrapy/extensions/telnet.py:23`

## scrapy.http (Request/Response model + cookies/headers)

- scrapy.http -> scrapy.utils (import: subclass object_ref) — `scrapy/http/request/__init__.py:30`
- scrapy.http -> scrapy.utils (import: Headers subclasses CaselessDict) — `scrapy/http/headers.py:8`
- scrapy.http -> scrapy.utils (import: urlparse_cached for cookie host/scheme) — `scrapy/http/cookies.py:9`
- scrapy.http -> scrapy.utils (import: get_base_url for TextResponse.urljoin) — `scrapy/http/response/text.py:27`
- scrapy.http -> scrapy.utils (import: create_deprecated_class wraps FormRequest) — `scrapy/http/__init__.py:20`
- scrapy.http -> scrapy.selector + scrapy.linkextractors (runtime-call: lazy import to break cycle) — `scrapy/http/response/text.py:150`
- scrapy.http -> scrapy.link (import: Link unwrapped in follow) — `scrapy/http/response/__init__.py:16`
- scrapy.http -> scrapy.exceptions (import: NotSupported / ScrapyDeprecationWarning) — `scrapy/http/response/__init__.py:13`
- scrapy.http -> scrapy.spiders (type-ref: to_dict spider param types against scrapy.Spider) — `scrapy/http/request/__init__.py:384`
- scrapy.http -> scrapy.utils (import: Twisted Failure errback typing) — `scrapy/http/request/__init__.py:35`

## scrapy.settings (configuration system)

- scrapy.settings -> scrapy.utils (import) — `scrapy/settings/__init__.py:14`
- scrapy.settings -> scrapy.exceptions (import: ScrapyDeprecationWarning) — `scrapy/settings/__init__.py:12`
- scrapy.settings -> scrapy.core.downloader (default-registry-ref: DOWNLOADER + DOWNLOAD_HANDLERS_BASE import strings) — `scrapy/settings/default_settings.py:307`
- scrapy.settings -> scrapy.core (default-registry-ref: SCHEDULER import string) — `scrapy/settings/default_settings.py:529`
- scrapy.settings -> scrapy.downloadermiddlewares (default-registry-ref: DOWNLOADER_MIDDLEWARES_BASE chain) — `scrapy/settings/default_settings.py:315`
- scrapy.settings -> scrapy.spidermiddlewares (default-registry-ref: SPIDER_MIDDLEWARES_BASE chain + REFERRER_POLICY) — `scrapy/settings/default_settings.py:552`
- scrapy.settings -> scrapy.extensions (default-registry-ref: EXTENSIONS_BASE + FEED_STORAGES_BASE + HTTPCACHE_*) — `scrapy/settings/default_settings.py:344`
- scrapy.settings -> scrapy.pipelines (default-registry-ref: ITEM_PROCESSOR import string) — `scrapy/settings/default_settings.py:435`
- scrapy.settings -> scrapy.contracts (default-registry-ref: SPIDER_CONTRACTS_BASE import strings) — `scrapy/settings/default_settings.py:540`
- scrapy.settings -> scrapy item + loader + exporters (default-registry-ref: DEFAULT_ITEM_CLASS + FEED_EXPORTERS_BASE) — `scrapy/settings/default_settings.py:263`
- scrapy.settings -> scrapy queues + dupefilter + spiderloader (default-registry-ref: SCHEDULER_*_QUEUE + DUPEFILTER_CLASS + SPIDER_LOADER_CLASS) — `scrapy/settings/default_settings.py:531`
- scrapy.settings -> scrapy.commands (default-registry-ref: COMMANDS_MODULE/NEWSPIDER_MODULE/SPIDER_MODULES/TEMPLATES_DIR/EDITOR) — `scrapy/settings/default_settings.py:247`

(Note: the settings -> component edges are import-string literals resolved by consumers' load_object, NOT compile-time imports — `scrapy/settings/default_settings.py:307`.)

## scrapy.utils (shared infrastructure incl. reactor/async glue)

- scrapy.utils -> scrapy.settings (import) — `scrapy/utils/conf.py:12`, `scrapy/utils/log.py:15`, `scrapy/utils/versions.py:9`
- scrapy.utils -> scrapy.http (import) — `scrapy/utils/iterators.py:13`, `scrapy/utils/serialize.py:9`, `scrapy/utils/datatypes.py:36` (lazy)
- scrapy.utils -> scrapy item + loader + exporters (import) — `scrapy/utils/misc.py:19`
- scrapy.utils -> scrapy.selector + scrapy.linkextractors (import) — `scrapy/utils/iterators.py:14`
- scrapy.utils -> scrapy.spiders (import) — `scrapy/utils/spider.py:7`, `scrapy/utils/request.py:16`
- scrapy.utils -> scrapy queues + dupefilter + spiderloader (import) — `scrapy/utils/spider.py:18`
- scrapy.utils -> scrapy.crawler (import) — `scrapy/utils/test.py:16`, `scrapy/utils/misc.py:27` (TYPE_CHECKING)
- scrapy.utils -> scrapy.core (runtime-call: ExecutionEngine internals via get_engine_status) — `scrapy/utils/engine.py:10`, `:15-30`
- scrapy.utils -> scrapy.extensions (runtime-call: feed_complete_default_values_from_settings / feed_process_params_from_cli) — `scrapy/utils/conf.py:127`, `:144`
- scrapy.utils -> scrapy.http (responsetypes registry) (import) — `scrapy/utils/_download_handlers.py:17`
- scrapy.utils -> Twisted (external runtime, declared dependency) (import) — `pyproject.toml:10`, `scrapy/utils/reactor.py:10-11`, `scrapy/utils/defer.py:25-27`, `scrapy/utils/asyncio.py:11-13`

## scrapy.selector + scrapy.linkextractors (extraction)

- scrapy.selector+linkextractors -> scrapy.http (import) — `scrapy/selector/unified.py:11`
- scrapy.selector+linkextractors -> scrapy.http (runtime-call) — `scrapy/linkextractors/lxmlhtml.py:144`
- scrapy.selector+linkextractors -> scrapy.utils (import) — `scrapy/selector/unified.py:12`, `:13`, `:14`, `scrapy/linkextractors/lxmlhtml.py:22`, `:25`
- scrapy.selector+linkextractors -> scrapy.link (import) — `scrapy/linkextractors/lxmlhtml.py:20`
- scrapy.selector+linkextractors -> scrapy.link (runtime-call) — `scrapy/linkextractors/lxmlhtml.py:133`

## scrapy item + loader + exporters (item data layer)

- scrapy.item+loader+exporters -> scrapy.utils (import: object_ref leak-tracking base for Item) — `scrapy/item.py:15`
- scrapy.item+loader+exporters -> scrapy.utils (import: is_listlike/to_bytes/to_unicode + ScrapyJSONEncoder used by exporters) — `scrapy/exporters.py:21`
- scrapy.item+loader+exporters -> scrapy.utils (import: ScrapyJSONEncoder from scrapy.utils.serialize) — `scrapy/exporters.py:22`
- scrapy.item+loader+exporters -> scrapy.selector + scrapy.linkextractors (import + default_selector_class: ItemLoader builds Selector from response) — `scrapy/loader/__init__.py:90`
- scrapy.item+loader+exporters -> scrapy.http (runtime-ref: ItemLoader type-hints TextResponse, stores it in context) — `scrapy/loader/__init__.py:105`

## scrapy queues + dupefilter + spiderloader (scheduling support)

- scrapy.queues+dupefilter+spiderloader -> scrapy.utils (import: build_from_crawler) — `scrapy/pqueues.py:7`, def at `scrapy/utils/misc.py:176`
- scrapy.queues+dupefilter+spiderloader -> scrapy.utils (import: request_from_dict) — `scrapy/squeues.py:14`, def at `scrapy/utils/request.py:158`
- scrapy.queues+dupefilter+spiderloader -> scrapy.utils (import: job_dir, RequestFingerprinter, referer_str) — `scrapy/dupefilters.py:9-14`
- scrapy.queues+dupefilter+spiderloader -> scrapy.utils (import: load_object, walk_modules_iter, iter_spider_classes) — `scrapy/spiderloader.py:12-13`
- scrapy.queues+dupefilter+spiderloader -> scrapy.core.downloader (runtime-call: crawler.engine.downloader.slots/.active/get_slot_key) — `scrapy/pqueues.py:262`, `:268`, `:272-274`
- scrapy.queues+dupefilter+spiderloader -> scrapy.crawler (import: Crawler handle threaded through from_crawler/__init__) — `scrapy/pqueues.py:17`
- scrapy.queues+dupefilter+spiderloader -> scrapy.http (import: Request; priority/meta read) — `scrapy/pqueues.py:15`, `:167`, `:171`
- scrapy.queues+dupefilter+spiderloader -> scrapy.settings (runtime-call) — `scrapy/spiderloader.py:27`, `:58-59`, `scrapy/pqueues.py:330`, `scrapy/dupefilters.py:99`
- scrapy.queues+dupefilter+spiderloader -> scrapy.spiders (import: Spider discovery/resolution; handles_request) — `scrapy/spiderloader.py:21`, `:126`
- scrapy.queues+dupefilter+spiderloader -> scrapy.core (project-ref, INBOUND: scheduler consumes this) — `scrapy/core/scheduler.py:26`, `:24`, `:191-192`
- scrapy.queues+dupefilter+spiderloader -> scrapy.crawler (project-ref, INBOUND: crawler consumes spider loader) — `scrapy/crawler.py:22`, `:350`
- scrapy.queues+dupefilter+spiderloader -> queuelib (external) (import) — `scrapy/squeues.py:12`, manifest dep `pyproject.toml:21`
- scrapy.queues+dupefilter+spiderloader -> zope.interface (external) (import: implementer/verifyClass) — `scrapy/spiderloader.py:8-9`, manifest dep `pyproject.toml:25`

## scrapy.contracts (spider contract testing)

- scrapy.contracts -> scrapy.http (import: Request, Response) — `scrapy/contracts/__init__.py:12`, `scrapy/contracts/default.py:10`, default request_cls at `scrapy/contracts/__init__.py:142`
- scrapy.contracts -> scrapy.utils (import: get_spec, iterate_spider_output) — `scrapy/contracts/__init__.py:13` (resolves `scrapy/utils/python.py:215`, used at `:148`), `:14` (resolves `scrapy/utils/spider.py:39`, used at `:55`/`:71`/`:186`)
- scrapy.contracts -> scrapy.exceptions (import: ContractFail) — `scrapy/contracts/default.py:9` (resolves `scrapy/exceptions.py:122`), raised at `scrapy/contracts/default.py:112` and `:130`
- scrapy.contracts -> scrapy.spiders (import TYPE_CHECKING type-hint only) — `scrapy/contracts/__init__.py:21`, typed params at `:99` and `:125`
- scrapy.contracts -> scrapy.commands (runtime-call, INBOUND: consumer, not outgoing) — `scrapy/commands/check.py:11`, instantiated at `check.py:79`, from_spider driven at `check.py:90`

## scrapy signals + middleware base + addons (extensibility core)

- scrapy.signals+middleware+addons -> scrapy.utils (import) — `scrapy/middleware.py:11-14`
- scrapy.signals+middleware+addons -> scrapy.utils (import) — `scrapy/addons.py:7-8`
- scrapy.signals+middleware+addons -> scrapy.utils (runtime-call) — `scrapy/signalmanager.py:10`, `:52`
- scrapy.signals+middleware+addons -> scrapy.settings (runtime-call) — `scrapy/middleware.py:89`
- scrapy.signals+middleware+addons -> scrapy.settings (runtime-call) — `scrapy/addons.py:35`
- scrapy.signals+middleware+addons -> scrapy.crawler (runtime-call) — `scrapy/middleware.py:88-89`
- scrapy.signals+middleware+addons -> scrapy.crawler (type-ref) — `scrapy/addons.py:11`, `:21`
- scrapy.signals+middleware+addons -> scrapy.spiders (runtime-call) — `scrapy/middleware.py:59-65`, `:149`
- scrapy.signals+middleware+addons -> scrapy signals + middleware base + addons (import: internal) — `scrapy/signalmanager.py:10`

## External (declared) runtime dependencies — manifest grounding

- Twisted >= 21.7.0 — `pyproject.toml:10`
- pyOpenSSL — `pyproject.toml:11`
- defusedxml — `pyproject.toml:12`
- cssselect — `pyproject.toml:13`
- itemadapter — `pyproject.toml:14`
- itemloaders — `pyproject.toml:15` (and `itemloaders>=1.0.1` per item-layer facts)
- w3lib — `pyproject.toml:24`
- lxml — `pyproject.toml:14` (referenced) / `pyproject.toml:18`
- parsel — `pyproject.toml:16` / `pyproject.toml:18`
- protego — `pyproject.toml:19`
- cryptography — `pyproject.toml:20`
- queuelib — `pyproject.toml:21`
- service_identity — `pyproject.toml:22`
- zope.interface — `pyproject.toml:25`
- PyDispatcher (CPython) / PyPyDispatcher (PyPy) — `pyproject.toml:27-28`
- Note: hyper-h2 (h2) is a hard import in the HTTP/2 stack (`scrapy/core/http2/protocol.py:9-23`) but is NOT in `[project].dependencies` — HTTP/2 is effectively optional/transitive.
