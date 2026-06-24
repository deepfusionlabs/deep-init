<!-- DEEPINIT:START -->
<!--
provenance:
 stage: extract (BLIND re-derivation from code only)
 component: scrapy.pipelines (item pipelines incl. media/files/images)
 path: scrapy/pipelines/
 doc_in_inputs: false
 inputs: scrapy/pipelines/{__init__,media,files,images}.py + verification reads of
 scrapy/middleware.py, scrapy/core/engine.py, scrapy/crawler.py,
 scrapy/settings/default_settings.py, pyproject.toml
 date: 2026-06-13
-->

# scrapy.pipelines (item pipelines incl. media/files/images)

## Role

- Post-scrape item-processing stage: an ordered manager (`ItemPipelineManager`, a `MiddlewareManager` subclass) runs each configured pipeline's `process_item` over every scraped item, plus the family of asset-downloading pipelines (`MediaPipeline` ABC and its `FilesPipeline`/`ImagesPipeline` concretes) that fetch and store media referenced by item fields. — `scrapy/pipelines/__init__.py:31`, `scrapy/pipelines/media.py:58`
- The package docstring states this is the "Item pipeline". — `scrapy/pipelines/__init__.py:1`

## Dependencies (edges)

- **scrapy.utils** (shared infrastructure / reactor + async glue): imports `is_asyncio_available`, `call_later`, `run_in_thread` from `scrapy.utils.asyncio`; `build_component_list` / `get_component_priority_dict_with_base` usage via `scrapy.utils.conf`; `_maybeDeferred_coro`, `deferred_from_coro`, `ensure_awaitable`, `maybe_deferred_to_future`, `_defer_sleep_async`, `_DEFER_DELAY` from `scrapy.utils.defer`; `global_object_name`, `to_bytes` from `scrapy.utils.python`. — `scrapy/pipelines/__init__.py:17`, `scrapy/pipelines/__init__.py:18`, `scrapy/pipelines/__init__.py:19`, `scrapy/pipelines/media.py:17`, `scrapy/pipelines/media.py:20`
- **scrapy.utils** (more infra, media/files specific): `SequenceExclude`, `CaseInsensitiveDict` from `scrapy.utils.datatypes`; `failure_to_exc_info` from `scrapy.utils.log`; `arg_to_iter` from `scrapy.utils.misc`; `is_botocore_available` from `scrapy.utils.boto`; `ftp_store_file` from `scrapy.utils.ftp`; `urlparse_cached` from `scrapy.utils.httpobj`; `referer_str` / `RequestFingerprinterProtocol` from `scrapy.utils.request`; `_warn_spider_arg` from `scrapy.utils.decorators`; `TWISTED_FAILURE_HAS_STACK` from `scrapy.utils._deps_compat`. — `scrapy/pipelines/media.py:18`, `scrapy/pipelines/media.py:16`, `scrapy/pipelines/media.py:27`, `scrapy/pipelines/media.py:28`, `scrapy/pipelines/files.py:31`, `scrapy/pipelines/files.py:32`, `scrapy/pipelines/files.py:35`, `scrapy/pipelines/files.py:36`, `scrapy/pipelines/files.py:39`
- **scrapy signals + middleware base + addons** (extensibility core): `ItemPipelineManager` subclasses `MiddlewareManager` and reuses its method registry / `_process_chain` / `_set_compat_spider` / `_mw_methods_requiring_spider` / `_check_mw_method_spider_arg`. — `scrapy/pipelines/__init__.py:16`, `scrapy/pipelines/__init__.py:31`, `scrapy/middleware.py:35`, `scrapy/middleware.py:131`
- **scrapy.core** (engine) — runtime call edge: `MediaPipeline._check_media_to_download` awaits `self.crawler.engine.download_async(request)` to fetch each media request through the full downloader stack. — `scrapy/pipelines/media.py:211`, `scrapy/pipelines/media.py:212`, `scrapy/core/engine.py:464`
- **scrapy.crawler** (Crawler lifecycle): every media pipeline is constructed `from_crawler(crawler)`, holds `self.crawler`, and reads `crawler.settings`, `crawler.request_fingerprinter`, `crawler.engine`, `crawler.spider`, `crawler.stats`. — `scrapy/pipelines/media.py:70`, `scrapy/pipelines/media.py:83`, `scrapy/pipelines/media.py:84`, `scrapy/pipelines/media.py:120`, `scrapy/pipelines/files.py:502`, `scrapy/pipelines/files.py:685`
- **scrapy.http** (Request/Response model): builds `Request(u, callback=NO_CALLBACK)` for each media URL and consumes `Response` (body/status/flags). — `scrapy/pipelines/files.py:28`, `scrapy/pipelines/files.py:29`, `scrapy/pipelines/files.py:713`, `scrapy/pipelines/media.py:15`, `scrapy/pipelines/images.py:19`
- **scrapy.settings** (configuration system): pipeline list resolved from `ITEM_PIPELINES`; per-pipeline knobs read via `settings.getbool/getint/get` (e.g. `MEDIA_ALLOW_REDIRECTS`, `FILES_STORE`, `FILES_EXPIRES`, `IMAGES_STORE`, `IMAGES_THUMBS`, AWS/GCS/FTP credentials). — `scrapy/pipelines/__init__.py:37`, `scrapy/pipelines/media.py:93`, `scrapy/pipelines/files.py:506`, `scrapy/pipelines/files.py:514`, `scrapy/pipelines/images.py:116`, `scrapy/settings/default_settings.py:432`
- **scrapy.exceptions**: raises/handles `NotConfigured`, `IgnoreRequest`, `ScrapyDeprecationWarning`. — `scrapy/pipelines/media.py:15`, `scrapy/pipelines/files.py:27`, `scrapy/pipelines/images.py:18`
- **scrapy item + loader + exporters** (item data layer): reads/writes item fields via `itemadapter.ItemAdapter` (`files_urls_field` in / `files_result_field` out). — `scrapy/pipelines/files.py:24`, `scrapy/pipelines/files.py:708`, `scrapy/pipelines/files.py:729`, `scrapy/pipelines/images.py:16`, `scrapy/pipelines/images.py:226`
- **Internal sub-edges (within this package):** `files.py` imports `MediaPipeline`/`FileInfo`/`FileInfoOrError` from `scrapy.pipelines.media`; `images.py` imports `FileException`/`FilesPipeline`/`_md5sum` from `scrapy.pipelines.files`; `files.py` lazily imports `ImagesPipeline` from `scrapy.pipelines.images` inside `__init__` (deferred to break the import cycle). — `scrapy/pipelines/files.py:30`, `scrapy/pipelines/images.py:21`, `scrapy/pipelines/files.py:472`
- **Third-party (technology choices), runtime/optional:** Twisted `Deferred`/`DeferredList`/`maybeDeferred`/`FirstError`/`Failure`; `itemadapter`; optional `botocore` (S3), `google.cloud.storage` (GCS), stdlib `ftplib` (FTP), `PIL`/Pillow (images). — `scrapy/pipelines/media.py:11`, `scrapy/pipelines/files.py:25`, `scrapy/pipelines/files.py:172`, `scrapy/pipelines/files.py:292`, `scrapy/pipelines/files.py:18`, `scrapy/pipelines/images.py:72`

## Data

- Owns no DB; the data-store abstraction is `FilesStoreProtocol` with four backends selected by URI scheme via `STORE_SCHEMES`: `FSFilesStore` (local filesystem, `""`/`file`), `S3FilesStore` (`s3`), `GCSFilesStore` (`gs`), `FTPFilesStore` (`ftp`). — `scrapy/pipelines/files.py:87`, `scrapy/pipelines/files.py:446`
- Each store implements `persist_file` (write) and `stat_file` (read existence/mtime/checksum for the up-to-date check). — `scrapy/pipelines/files.py:90`, `scrapy/pipelines/files.py:99`
- Local files are written under `<basedir>/full/<sha1(url)><ext>` (files) or `full/<sha1(url)>.jpg` + `thumbs/<thumb_id>/<sha1(url)>.jpg` (images). — `scrapy/pipelines/files.py:757`, `scrapy/pipelines/images.py:249`, `scrapy/pipelines/images.py:261`
- Per-spider in-memory dedup/result cache lives in `MediaPipeline.SpiderInfo`: `downloading: set[bytes]`, `downloaded: dict[bytes, FileInfo|Failure]`, `waiting: defaultdict[bytes, list[Deferred]]`, all keyed by request fingerprint. — `scrapy/pipelines/media.py:61`, `scrapy/pipelines/media.py:64`
- Emits run statistics into the crawler stats collector: `file_count` and `file_status_count/<status>`. — `scrapy/pipelines/files.py:684`

## Boundary rules

- Pipelines are pluggable, priority-ordered components discovered from the `ITEM_PIPELINES` setting and composed by `build_component_list`; ordering, not hard-coded calls, defines the chain. — `scrapy/pipelines/__init__.py:34`, `scrapy/pipelines/__init__.py:37`
- This component is the consumer/terminal end of the item flow: it receives already-scraped items and either transforms or drops them; it never schedules crawl requests itself — media fetches are delegated outward to the engine/downloader via `engine.download_async`. — `scrapy/pipelines/media.py:212`
- Media requests are isolated from normal callback flow: each is created with `callback=NO_CALLBACK` and has its `callback`/`errback` stripped before download so pipeline downloads never re-enter spider parsing. — `scrapy/pipelines/files.py:713`, `scrapy/pipelines/media.py:157`, `scrapy/pipelines/media.py:158`
- Optional-dependency boundary: a backend or feature self-disables by raising `NotConfigured` rather than crashing the crawl (missing botocore, unset `FILES_STORE`/`IMAGES_STORE`, missing Pillow). — `scrapy/pipelines/files.py:171`, `scrapy/pipelines/files.py:477`, `scrapy/pipelines/images.py:77`
- Subclass-override boundary: `MediaPipeline` declares the overridable interface as abstract methods (`media_to_download`, `get_media_requests`, `media_downloaded`, `media_failed`, `file_path`); concrete pipelines must implement them. — `scrapy/pipelines/media.py:268`, `scrapy/pipelines/media.py:276`, `scrapy/pipelines/media.py:315`

## Key facts

- Dual concurrency runtime: the manager and media pipeline branch on `is_asyncio_available` — native `asyncio.gather` when the asyncio reactor is installed, else a Twisted `DeferredList`-based path — so both execution models are supported from one code path. — `scrapy/pipelines/__init__.py:115`, `scrapy/pipelines/media.py:135`
- Deduplication invariant: concurrent requests for the same media (same fingerprint) are coalesced — the first triggers the actual download while later ones attach a `Deferred` to `info.waiting[fp]`; results (success or `Failure`) are cached in `info.downloaded[fp]` and all waiters are fired once. — `scrapy/pipelines/media.py:177`, `scrapy/pipelines/media.py:227`, `scrapy/pipelines/media.py:261`
- Deliberate memory-leak mitigation: cached failures are stripped (`cleanFailure`, `frames.clear`, `stack.clear`) and a `StopIteration` `__context__` is nulled to avoid retaining Request/Response references in the cache. — `scrapy/pipelines/media.py:230`, `scrapy/pipelines/media.py:254`
- Conditional-download (freshness) logic: `FilesPipeline._onsuccess` skips re-download when the stored file's age (`time.time - last_modified`) is within `self.expires` days, classifying files as new / uptodate / expired. — `scrapy/pipelines/files.py:556`, `scrapy/pipelines/files.py:558`, `scrapy/pipelines/files.py:425`
- Content-addressed storage: stored paths are derived from `sha1(request.url)` (file extension guessed via `mimetypes`); per-file integrity is an md5 checksum computed streaming via `_md5sum` (8096-byte reads). — `scrapy/pipelines/files.py:740`, `scrapy/pipelines/files.py:61`, `scrapy/pipelines/files.py:69`
- `ImagesPipeline extends FilesPipeline` and adds Pillow processing: EXIF transpose, min-width/min-height rejection (`ImageException`), RGBA/P→RGB conversion, JPEG re-encode, and configurable thumbnail generation (`IMAGES_THUMBS`). — `scrapy/pipelines/images.py:42`, `scrapy/pipelines/images.py:165`, `scrapy/pipelines/images.py:168`, `scrapy/pipelines/images.py:180`
- Per-subclass settings-key resolution: `_key_for_pipe` lets a subclass override a base setting (e.g. `MYPIPELINE_FILES_EXPIRES`) by prefixing the uppercased class name, falling back to the base key. — `scrapy/pipelines/media.py:103`
- Backward-compat shim: the sync `process_item`/`open_spider`/`close_spider` entry points emit `ScrapyDeprecationWarning` and delegate to the `*_async` coroutine variants, marking the async API as canonical. — `scrapy/pipelines/__init__.py:51`, `scrapy/pipelines/__init__.py:60`
- Item-mutation contract: `item_completed` writes the successful results back into the item's result field under `suppress(KeyError)` and always returns the item (drops nothing on its own). — `scrapy/pipelines/files.py:725`, `scrapy/pipelines/images.py:233`
<!-- DEEPINIT:END -->
