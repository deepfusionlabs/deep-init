<!-- DEEPINIT:START -->
<!--
provenance:
 stage: extract (BLIND re-derivation from code only)
 component: scrapy.core.downloader (downloader + handlers + TLS)
 path: scrapy/core/downloader/
 inputs: scrapy/core/downloader/**, pyproject.toml, scrapy/settings/default_settings.py
 doc_in_inputs: false
 date: 2026-06-13
-->

# scrapy.core.downloader (downloader + handlers + TLS)

## Role

- Owns the network-fetch concern: the `Downloader` accepts a `Request` via `fetch`, runs it through the downloader-middleware chain, applies per-slot concurrency/delay throttling, and dispatches it to the per-scheme handler that performs the actual transfer, returning a `Response` (or a redirect `Request`) — `scrapy/core/downloader/__init__.py:99` (class `Downloader`), `__init__.py:124` (`fetch`), `__init__.py:223` (`_download` → `self.handlers.download_request_async`).

## Dependencies (edges)

- **scrapy.http (Request/Response model)** — imports `Request`, `Spider` (re-exported), and consumes `Request`/`Response` throughout: `scrapy/core/downloader/__init__.py:13` (`from scrapy import Request, Spider, signals`); middleware imports `Request, Response` from `scrapy.http` at `scrapy/core/downloader/middleware.py:14`. `[HIGH]`
- **scrapy signals (extensibility core)** — sends `request_reached_downloader`, `response_downloaded`, `request_left_downloader` and connects `_close` to `engine_stopped`: `scrapy/core/downloader/__init__.py:182`, `__init__.py:231`, `__init__.py:248`, and `scrapy/core/downloader/handlers/__init__.py:70` (`crawler.signals.connect(self._close, signals.engine_stopped)`). `[HIGH]`
- **scrapy middleware base (extensibility core)** — `DownloaderMiddlewareManager` subclasses `MiddlewareManager`: `scrapy/core/downloader/middleware.py:15` (`from scrapy.middleware import MiddlewareManager`), `middleware.py:34` (`class DownloaderMiddlewareManager(MiddlewareManager)`). `[HIGH]`
- **scrapy.settings (configuration system)** — reads `CONCURRENT_REQUESTS`, `CONCURRENT_REQUESTS_PER_DOMAIN`/`_PER_IP`, `RANDOMIZE_DOWNLOAD_DELAY`, `DOWNLOAD_SLOTS`, `DOWNLOAD_DELAY`, `DOWNLOAD_HANDLERS`, TLS settings: `scrapy/core/downloader/__init__.py:110-122`, `handlers/__init__.py:60-65`, `contextfactory.py:86-97`. `[HIGH]`
- **scrapy.utils (shared infra incl. reactor/async glue)** — async/reactor glue (`scrapy.utils.asyncio`, `scrapy.utils.defer`), config (`scrapy.utils.conf.build_component_list`), object loading (`scrapy.utils.misc.build_from_crawler, load_object`), TLS/SSL helpers (`scrapy.utils.ssl`), and the shared download helpers `scrapy.utils._download_handlers`: `scrapy/core/downloader/__init__.py:17-31`, `middleware.py:16-23`, `handlers/__init__.py:12-19`, `handlers/http11.py:43-57`, `contextfactory.py:28-29`. `[HIGH]`
- **scrapy.core.http2 (HTTP/2 client stack)** — the H2 handler imports the H2 agent + connection pool: `scrapy/core/downloader/handlers/http2.py:9` (`from scrapy.core.http2.agent import H2Agent, H2ConnectionPool`). `[HIGH]`
- **scrapy.crawler (Crawler lifecycle)** — every constructor takes a `Crawler` and pulls `settings`/`signals`/`spider` from it: `scrapy/core/downloader/__init__.py:103-106` (`def __init__(self, crawler: Crawler)`), `handlers/__init__.py:50`, `contextfactory.py:79`. `[HIGH]`
- **scrapy.resolver (DNS cache, scheduling support)** — IP-based slot keying reads the shared DNS cache: `scrapy/core/downloader/__init__.py:16` (`from scrapy.resolver import dnscache`), used at `__init__.py:173` (`dnscache.get(key, key)`). `[HIGH]`
- **scrapy.responsetypes (item/response data layer)** — file/ftp/datauri handlers pick a Response subclass by mime/args: `scrapy/core/downloader/handlers/ftp.py:44`, `handlers/file.py:9`, `handlers/datauri.py:9` (`from scrapy.responsetypes import responsetypes`). `[HIGH]`
- **scrapy.exceptions (extensibility core)** — raises/consumes `NotConfigured`, `NotSupported`, `StopDownload`, `DownloadTimeoutError`, `ResponseDataLossError`, `UnsupportedURLSchemeError`, `ScrapyDeprecationWarning`, `_InvalidOutput`: `scrapy/core/downloader/handlers/__init__.py:11`, `middleware.py:13`, `http11.py:35-41`, `http2.py:10-14`. `[HIGH]`
- **External: Twisted (async runtime — technology choice)** — `Deferred`/`inlineCallbacks`/`Failure`, `twisted.web.client.Agent`/`HTTPConnectionPool`, `twisted.internet.ssl`, `twisted.protocols.ftp.FTPClient`: `scrapy/core/downloader/__init__.py:10-11`, `handlers/http11.py:15-30`, `handlers/ftp.py:39,97`; declared `Twisted>=21.7.0` at `pyproject.toml:9`. `[HIGH]`
- **External: pyOpenSSL + service_identity + zope.interface (TLS — technology choice)** — `OpenSSL.SSL`, `service_identity.*`, `zope.interface` implementer/verify: `scrapy/core/downloader/tls.py:7-16`, `contextfactory.py:6-16`; declared at `pyproject.toml:11,18,22`. `[HIGH]`
- **External: botocore (S3 auth, optional)** — imported lazily for AWS request signing: `scrapy/core/downloader/handlers/s3.py:33-34,59`, gated by `scrapy.utils.boto.is_botocore_available` at `s3.py:7,23`. `[HIGH]`
- **External: httpx / h2 / socksio (experimental streaming handler, optional)** — `scrapy/core/downloader/handlers/_httpx.py:42,54,62`; registered (not in BASE) by `scrapy.crawler` at `scrapy/crawler.py:164`. `[HIGH]`

## Data

- **In-memory per-slot download state (no persistence)** — `Downloader.slots: dict[str, Slot]` keyed by domain/IP/meta slot, each `Slot` holding `active`/`queue`/`transferring` sets and a deque: `scrapy/core/downloader/__init__.py:107` (`self.slots`), `__init__.py:44-58` (`@dataclass Slot`). `[HIGH]`
- **Lazy per-scheme handler registry (in-memory caches)** — `_schemes`, `_handlers`, `_notconfigured`, `_old_style_handlers`: `scrapy/core/downloader/handlers/__init__.py:53-59`. `[HIGH]`
- **Persistent HTTP connection pool (Twisted, in-process)** — `HTTPConnectionPool(reactor, persistent=True)` with `maxPersistentPerHost` = `CONCURRENT_REQUESTS_PER_DOMAIN`: `scrapy/core/downloader/handlers/http11.py:94-97`; HTTP/2 uses `H2ConnectionPool`: `handlers/http2.py:43`. `[HIGH]`
- **DNS cache read (shared `LocalCache`, not owned)** — read via `dnscache.get(...)` for IP-concurrency slot keys: `scrapy/core/downloader/__init__.py:173`. `[MEDIUM]`
- **Optional local-file write (ftp handler)** — when `ftp_local_filename` is set, body is streamed to a file on disk: `scrapy/core/downloader/handlers/ftp.py:58-60` (`Path(filename.decode).open("wb")`). `[HIGH]`

## Boundary rules

- **Handler scheme protocol** — every handler exposes `async download_request(request) -> Response` (+ optional `close` and a `lazy` flag); enforced via the `DownloadHandlerProtocol` and the `BaseDownloadHandler` ABC: `scrapy/core/downloader/handlers/__init__.py:41-46`, `handlers/base.py:15-31`. `[HIGH]`
- **Middleware contract** — `process_request`/`process_response`/`process_exception` must return `None`/`Response`/`Request`; a violation raises `_InvalidOutput`: `scrapy/core/downloader/middleware.py:107-111`, `middleware.py:131-135`, `middleware.py:149-153`. `[HIGH]`
- **Symmetric chain ordering** — `process_request` appended (engine→downloader order) while `process_response`/`process_exception` are `appendleft` (reverse order): `scrapy/core/downloader/middleware.py:45-52`. `[HIGH]`
- **Per-scheme dispatch + graceful unsupported** — scheme is taken from the URL; an unknown/failed scheme raises `NotSupported` rather than crashing the loop: `scrapy/core/downloader/handlers/__init__.py:141-147`. `[HIGH]`
- **Consumed by the engine, not the reverse** — `scrapy.core.engine` loads the `DOWNLOADER` setting, instantiates `Downloader(crawler)`, and drives `fetch`/`needs_backout`/`close`; this component does not import the engine: `scrapy/core/engine.py:132-139,495`, `default_settings.py:307`. `[HIGH]`

## Key facts

- **Throttling is per-slot, not global** — concurrency uses `ip_concurrency or domain_concurrency` per slot; `needs_backout` is the only global cap (`len(active) >= total_concurrency`): `scrapy/core/downloader/__init__.py:140-141,151`. `[HIGH]`
- **Slot key precedence** — `request.meta["download_slot"]` overrides; else the URL hostname, optionally resolved to an IP via `dnscache` when IP-concurrency is on: `scrapy/core/downloader/__init__.py:166-175`. `[HIGH]`
- **Download delay can be randomized** — `download_delay` returns `random.uniform(0.5*delay, 1.5*delay)` when `randomize_delay`; queue processing self-throttles via `call_later` to prevent bursts: `scrapy/core/downloader/__init__.py:63-66,203-217`. `[HIGH]`
- **Strict ordering in `_download` is load-bearing** — comment "The order is very important … Do not change!": add-to-transferring → download → fire `response_downloaded` → (finally) remove-from-transferring + re-process queue + fire `request_left_downloader`: `scrapy/core/downloader/__init__.py:223-252`. `[HIGH]`
- **Idle slots are garbage-collected** — a looping call (`_SLOT_GC_INTERVAL = 60.0s`) drops slots with no active requests past their delay window: `scrapy/core/downloader/__init__.py:101,269-279`. `[HIGH]`
- **Handlers are lazy-loaded per scheme** — instanced on first request for that scheme (`lazy = True` default); load failure is recorded in `_notconfigured` and degrades to `NotSupported` instead of aborting: `scrapy/core/downloader/handlers/__init__.py:72-118`. `[HIGH]`
- **DOWNLOAD_HANDLERS_BASE wires the scheme→class map** — data/file/http/https/s3/ftp; http & https both map to `HTTP11DownloadHandler`: `scrapy/settings/default_settings.py:286-293`. `[HIGH]`
- **HTTPS cert verification is OFF by default** — `_ScrapyClientContextFactory` is "non-peer-certificate verifying"; `DOWNLOAD_VERIFY_CERTIFICATES` defaults to `False`, and `_ScrapyClientTLSOptions` deliberately catches `VerificationError`/`CertificateError`/`ValueError` to warn-not-fail: `scrapy/core/downloader/contextfactory.py:42-43,76,142-152`, `tls.py:71-110`, `default_settings.py:305`. `[HIGH]`
- **Twisted-version-conditional TLS path** — picks `_ScrapyClientTLSOptions26` vs `_ScrapyClientTLSOptions` based on `TWISTED_TLS_NEW_IMPL`; legacy-server-connect option `0x4` is forced on the SSL context: `scrapy/core/downloader/contextfactory.py:144-152,259-265`, `tls.py:121-179`. `[HIGH]`
- **HTTPS-over-proxy uses a CONNECT tunnel** — `_TunnelingTCP4ClientEndpoint`/`_TunnelingAgent` send an HTTP CONNECT and start TLS on a 200; HTTPS proxies for HTTPS destinations are explicitly unsupported: `scrapy/core/downloader/handlers/http11.py:165-259,424-427`. `[HIGH]`
- **maxsize/warnsize enforced mid-stream** — `_ResponseReader` cancels the download once `download_maxsize` is exceeded and warns at `download_warnsize`; `StopDownload` can short-circuit via the `headers_received`/`bytes_received` signals: `scrapy/core/downloader/handlers/http11.py:686-713,509-524`. `[HIGH]`
- **S3 handler delegates the actual fetch to the https handler** — it signs the request with botocore then calls the loaded `https` handler's `download_request`: `scrapy/core/downloader/handlers/s3.py:44-48,70`. `[HIGH]`
- **Async/Deferred bridge throughout** — the component bridges Twisted `Deferred` and native `async`/`await` via `deferred_from_coro`/`maybe_deferred_to_future`; `fetch` is `@inlineCallbacks` while the inner path is coroutine-based: `scrapy/core/downloader/__init__.py:24-28,124-135,191`. `[HIGH]`
- **Deprecation shims preserved** — sync `download`/`download_request` wrappers, `ScrapyClientContextFactory`/`BrowserLikeContextFactory`/`AcceptableProtocolsContextFactory` deprecated classes, and a module-level `__getattr__` for old TLS method names: `scrapy/core/downloader/middleware.py:54-71`, `handlers/__init__.py:131-139`, `contextfactory.py:160-165,248-253`, `tls.py:45-60`. `[HIGH]`
- **httpx streaming handler is experimental + optional** — `experimental = True`, registered outside BASE, keeps a per-proxy client pool (httpx lacks per-request proxies): `scrapy/core/downloader/handlers/_httpx.py:77,98-101`, `crawler.py:164`. `[HIGH]`
<!-- DEEPINIT:END -->
