<!--
DeepInit provenance header
stage: blind-mirror-test
repo: scrapy@blind
doc_in_inputs: false
tier: deep (.ai/docs, on-demand)
note: data-stores / persistence facts re-derived from CODE ONLY. Every claim cites a file:line.
-->

# Data layer — scrapy (blind re-derivation)

## Summary: no bundled database

Scrapy ships no fixed database. Persistence is pluggable file/ftp/s3 feed-export and httpcache backends, not a bundled DB — `scrapy/settings/default_settings.py:378-381`. The settings module only references on-disk paths as string defaults (it does not itself read/write them): `JOBDIR=None`, `HTTPCACHE_DIR='httpcache'`, `FEED_TEMPDIR`, `FILES_STORE`/`IMAGES_STORE` — `scrapy/settings/default_settings.py:437`, `:410`, `:391`.

What persistence exists is component-owned and falls into a few categories: **scheduler job-directory persistence** (request queues + dupefilter seen-set), **media/feed file stores**, **HTTP cache backends**, **spider job state**, and a large amount of **in-memory transient state** (queues, pools, caches). Each is grounded below.

## On-disk / persistent stores

### Scheduler & queues (JOBDIR-gated)

- Scheduler job-directory persistence: a `requests.queue/` dir + `active.json` (priority-queue startprios state), read on open and written on close, only when JOBDIR is set — `scrapy/core/scheduler.py:480-498`.
- Disk-persisted priority queues: one downstream-queue per (priority, start-flag) under a key dir, subdir named by priority with an `s` suffix for start requests — `scrapy/pqueues.py:88-98`, `scrapy/pqueues.py:151-164`.
- Per-slot persistence dirs for DownloaderAwarePriorityQueue: one path-sanitized + MD5-suffixed subdir per download slot/domain — `scrapy/pqueues.py:290-296`, `scrapy/pqueues.py:22-37`.
- On-disk queue files via queuelib FifoDiskQueue/LifoDiskQueue subclasses that auto-mkdir the parent and store serialized request dicts — `scrapy/squeues.py:27-35`, `scrapy/squeues.py:149-174`.
- Serialization tech choice: pickle protocol 4 or marshal; PicklingError/AttributeError/TypeError normalized to ValueError — `scrapy/squeues.py:139-145`.
- Disk-queue preferred over memory on enqueue: serializable requests go to disk, non-serializable fall back to memory and bump `scheduler/unserializable` — `scrapy/core/scheduler.py:364-385`, `:414-436`.

### Dupefilter

- Dupefilter JOBDIR persistence: a `requests.seen` file, one hex fingerprint per line, append+read, line-buffered/write_through, pre-loaded into a set on init — `scrapy/dupefilters.py:67-70`, `:87-94`.
- In-memory de-dup set: `RFPDupeFilter.fingerprints` (set[str]) — `scrapy/dupefilters.py:83`, `:106-113`.
- De-dup identity = request fingerprint (canonical url+method+body, hex) via the pluggable RequestFingerprinterProtocol (default RequestFingerprinter) — `scrapy/dupefilters.py:53-57`, `:115-117`.

### Media / files / images stores (FilesPipeline / ImagesPipeline)

- `FilesStoreProtocol` abstraction with four URI-scheme-selected backends in STORE_SCHEMES: FSFilesStore (local fs), S3FilesStore (s3), GCSFilesStore (gs), FTPFilesStore (ftp) — `scrapy/pipelines/files.py:87`, `:446`.
- Each store owns `persist_file` (write) + `stat_file` (read mtime/checksum for the freshness check) — `scrapy/pipelines/files.py:90`, `:99`.
- Content-addressed paths under `<basedir>/full/<sha1(url)><ext>` (files) and `full/<sha1(url)>.jpg` + `thumbs/<thumb_id>/<sha1(url)>.jpg` (images) — `scrapy/pipelines/files.py:757`, `scrapy/pipelines/images.py:249`, `:261`.
- Per-file integrity is a streaming md5 checksum via `_md5sum` (8096-byte reads) — `scrapy/pipelines/files.py:740`, `:69`.
- Conditional-download freshness: `FilesPipeline._onsuccess` skips re-download when stored file age (`time.time-last_modified`) is within `self.expires` days — `scrapy/pipelines/files.py:556`, `:425`.
- Run statistics written to crawler stats: `file_count`, `file_status_count/<status>` — `scrapy/pipelines/files.py:684`.

### HTTP cache backends (scrapy.extensions)

- HTTP cache filesystem backend: writes/reads meta, pickled_meta, response_headers/body, request_headers/body under `<cachedir>/<spider.name>/<key[0:2]>/<key>`, optional gzip — `scrapy/extensions/httpcache.py:351-380`, `:314-320`.
- HTTP cache DBM backend: a per-spider DBM db `<cachedir>/<spider.name>.db` storing pickled `{key}_data` + `{key}_time` — `scrapy/extensions/httpcache.py:247-256`, `:283-307`.
- HTTP cache RFC2616 freshness ports Mozilla/Firefox heuristics, caches 300/301/308 indefinitely, and serves a stale cached response on 5xx unless must-revalidate — `scrapy/extensions/httpcache.py:109-110`, `:165-173`, `:195-196`.
- HTTP cache persistence is also reachable via the httpcache downloader middleware, which DELEGATES storage to the pluggable HTTPCACHE_STORAGE/HTTPCACHE_POLICY via load_object (`storage.retrieve_response`/`store_response`) — `scrapy/downloadermiddlewares/httpcache.py:47`.

### Spider job state

- Spider job state: pickles `spider.state` to `<jobdir>/spider.state` on close, unpickles on open — `scrapy/extensions/spiderstate.py:35-51`.

### Feed exports (scrapy.extensions)

- Feed exports via pluggable storage backends: local file / stdout / S3 / GCS / FTP; blocking backends stage to a NamedTemporaryFile then upload off-thread — `scrapy/extensions/feedexport.py:124-137`, `:167-363`.
- BlockingFeedStorage.store offloads blocking I/O via run_in_thread and returns a Deferred — `scrapy/extensions/feedexport.py:132-133`, `:251`, `:307`, `:353`.
- Custom feed storage MUST implement the IFeedStorage zope interface `__init__`/`open`/`store` — `scrapy/extensions/feedexport.py:91-106`.
- Each exporter writes to a caller-supplied file-like sink (the item layer owns no files) — `scrapy/exporters.py:114`, `:237`.

### Pickle trust boundary

- Persistence uses Python pickle protocol 4 in three places (spider state, DBM cache, filesystem cache meta), with `loads` marked unsafe (`# noqa: S301`) — a trust boundary on cache/jobdir contents — `scrapy/extensions/spiderstate.py:39`, `:44`, `scrapy/extensions/httpcache.py:293`, `:307`, `:368`, `:391`.

### CLI-side writes

- `--pidfile` writes PID to a file — `scrapy/commands/__init__.py:133-136`.
- `--profile` dumps cProfile stats to a file — `scrapy/cmdline.py:233-234`.
- `startproject` copies a template tree and renders project files to disk — `scrapy/commands/startproject.py:109-123`.
- `genspider` copies/renders a spider `.py` into NEWSPIDER_MODULE, reading templates from TEMPLATES_DIR/scrapy templates — `scrapy/commands/genspider.py:162-164`, `:226-234`.

### Config files / environment (read by scrapy.utils, not owned)

- Reads (does not own) the on-disk `scrapy.cfg` via ConfigParser, searching project dir + `/etc/scrapy.cfg` + `c:\scrapy\scrapy.cfg` + `$XDG_CONFIG_HOME` + `~/.scrapy.cfg` — `scrapy/utils/conf.py:104`, `:112-124`.
- Reads/writes process environment: sets `SCRAPY_SETTINGS_MODULE` + mutates `sys.path` in `init_env`; save/restore via the `set_environ` context manager — `scrapy/utils/conf.py:89`, `scrapy/utils/misc.py:221`.

## In-memory (transient) state

- Engine in-flight tracking: `_Slot.inprogress` set[Request] of requests currently being downloaded — `scrapy/core/engine.py:65-86`.
- In-memory request store: dual priority queues — memory queue `mqs` (always) + optional disk queue `dqs` (when dqdir) — `scrapy/core/scheduler.py:349-350`.
- Scraper in-flight buffer: `Slot.queue` deque of (result, request, deferred) tuples + active set + active_size byte accounting bounded by max_active_size — `scrapy/core/scraper.py:58-99`.
- Downloader per-slot state: `Downloader.slots` dict[str,Slot] with active/queue/transferring sets, no persistence — `scrapy/core/downloader/__init__.py:107`, Slot dataclass `:44-58`.
- Lazy per-scheme handler registry caches `_schemes`/`_handlers`/`_notconfigured`/`_old_style_handlers` — `scrapy/core/downloader/handlers/__init__.py:53-59`.
- Persistent Twisted HTTP connection pool, in-process, `maxPersistentPerHost = CONCURRENT_REQUESTS_PER_DOMAIN` — `scrapy/core/downloader/handlers/http11.py:94-97`; H2ConnectionPool for HTTP/2 — `scrapy/core/downloader/handlers/http2.py:43`.
- HTTP/2 in-memory pools: `H2ConnectionPool._connections` dict keyed by (scheme,host,port) — `scrapy/core/http2/agent.py:39`; `_pending_requests` deque while connecting — `:42-44`; per-connection `streams` dict + `_pending_request_stream_pool` — `scrapy/core/http2/protocol.py:120`, `:124`; per-stream response body `BytesIO` — `scrapy/core/http2/stream.py:148`.
- Downloader-middleware in-memory stores: cookie jars `self.jars` (defaultdict[Any, CookieJar]) — `scrapy/downloadermiddlewares/cookies.py:46`; robots.txt parser cache `self._parsers` (value may be an in-flight Deferred) — `scrapy/downloadermiddlewares/robotstxt.py:43`; seen-offsite-domains `self.domains_seen` — `scrapy/downloadermiddlewares/offsite.py:29`; proxy table from `getproxies` `self.proxies` — `scrapy/downloadermiddlewares/httpproxy.py:29`.
- Media pipeline per-spider dedup/result cache `MediaPipeline.SpiderInfo` keyed by request fingerprint: downloading/downloaded/waiting — `scrapy/pipelines/media.py:61`.
- HTTP model: in-memory CookieJar wrapping stdlib `http.cookiejar.CookieJar` (no DB / no disk) — `scrapy/http/cookies.py:5`, `:34`; per-instance `__slots__` on Request/Response — `scrapy/http/request/__init__.py:109-120`, `scrapy/http/response/__init__.py:61-68`.
- Settings: in-memory only, `self.attributes` dict[str, SettingsAttribute] (value, priority), no external persistence owned — `scrapy/settings/__init__.py:105`, `:59`.
- Utils: in-process live-instance registry `live_refs` (defaultdict[type, WeakKeyDictionary]) — `scrapy/utils/trackref.py:33`, `:43-46`; bounded AST/generator-introspection cache `_generator_callbacks_cache = LocalWeakReferencedCache(limit=128)` — `scrapy/utils/misc.py:255`.
- Item layer: per-item `Item._values` dict, distinct from the class-level `fields` map — `scrapy/item.py:86`, `:83`.
- Spider registry: `SpiderLoader._spiders` (name->class) + `_found` (name->locations, duplicate detection), built by walking SPIDER_MODULES — `scrapy/spiderloader.py:60-62`, `:84-105`.
- Stats collector (in-memory, read+mutate; the collector is owned outside these components) — counters such as `feedexport/{failed,success}_count/<storage>`, `memusage/*`, `item_scraped_count`, `retry/count`, `httpcache/hit`, `offsite/filtered` — `scrapy/extensions/feedexport.py:573-576`, `scrapy/extensions/corestats.py:41-61`, `scrapy/downloadermiddlewares/retry.py:121`, `scrapy/downloadermiddlewares/httpcache.py:93`, `scrapy/downloadermiddlewares/offsite.py:64`.
- Link extraction is stateless: parses bodies into in-memory Selector trees, returns `list[Link]`; no file/queue/DB access — `scrapy/linkextractors/lxmlhtml.py:139`.

## Cross-hook scratch store

- `Request.meta` is used as a cross-hook / cross-retry scratch store: `redirect_times`/`redirect_ttl` (`scrapy/downloadermiddlewares/redirect.py:94`), `retry_times` (`scrapy/downloadermiddlewares/retry.py:98`), `cached_response` (`scrapy/downloadermiddlewares/httpcache.py:98`), `proxy`/`_auth_proxy` (`scrapy/downloadermiddlewares/httpproxy.py:89`).
