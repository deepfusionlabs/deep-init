<!-- DEEPINIT:START -->
<!--
provenance:
 stage: extract (BLIND re-derivation, code-only)
 component: scrapy queues + dupefilter + spiderloader (scheduling support)
 inputs: scrapy/pqueues.py, scrapy/squeues.py, scrapy/dupefilters.py, scrapy/spiderloader.py, scrapy/interfaces.py, pyproject.toml (+ grounding reads of scrapy/core/scheduler.py, scrapy/core/downloader/__init__.py, scrapy/crawler.py, scrapy/utils/{misc,request,job,spider}.py)
 date: 2026-06-13
 note: every claim cites a file:line opened under C:/tmp/p5_scrapy_blind
-->

# scrapy queues + dupefilter + spiderloader (scheduling support)

## Role

- The pluggable backend layer the scheduler plugs in: priority-bucketed request queues, on-disk/in-memory request queue implementations, a request de-duplication filter, and a spider registry that discovers and resolves spider classes — none of which run the crawl loop themselves; they are data structures and registries the scheduler/crawler drive. scrapy/pqueues.py:52, scrapy/squeues.py:1, scrapy/dupefilters.py:53, scrapy/spiderloader.py:51

## Dependencies (edges)

- → scrapy.utils (shared infrastructure): `pqueues.py` imports `build_from_crawler` to instantiate downstream queue classes from a crawler. scrapy/pqueues.py:7 (defined at scrapy/utils/misc.py:176)
- → scrapy.utils (shared infrastructure): `squeues.py` imports `request_from_dict` to rehydrate a serialized request dict back into a Request on pop/peek. scrapy/squeues.py:14 (defined at scrapy/utils/request.py:158)
- → scrapy.utils (shared infrastructure): `dupefilters.py` imports `job_dir`, `RequestFingerprinter`, `RequestFingerprinterProtocol`, `referer_str`. scrapy/dupefilters.py:9-14 (defined at scrapy/utils/job.py:10, scrapy/utils/request.py:110, scrapy/utils/request.py:106, scrapy/utils/request.py:150)
- → scrapy.utils (shared infrastructure): `spiderloader.py` imports `load_object`, `walk_modules_iter` (to import spider modules) and `iter_spider_classes`. scrapy/spiderloader.py:12-13 (defined at scrapy/utils/misc.py:58, scrapy/utils/misc.py:93, scrapy/utils/spider.py:50)
- → scrapy.core.downloader (downloader + handlers): `DownloaderInterface` reaches into `crawler.engine.downloader` and reads its `.slots` / `slot.active` and calls `get_slot_key` to make `DownloaderAwarePriorityQueue` dequeue least-busy slots first. scrapy/pqueues.py:262, scrapy/pqueues.py:268, scrapy/pqueues.py:272-274 (contract at scrapy/core/downloader/__init__.py:99,:107,:148)
- → scrapy.crawler (Crawler lifecycle): `Crawler` is the construction handle threaded through every `from_crawler`/`__init__` here; `DownloaderAwarePriorityQueue` reads `crawler.settings`, `squeues` reads `crawler.spider`, `RFPDupeFilter` reads `crawler.settings`/`crawler.request_fingerprinter`. scrapy/pqueues.py:17, scrapy/pqueues.py:330, scrapy/squeues.py:79, scrapy/dupefilters.py:98-99
- → scrapy.http (Request model): all queues push/pop/peek `Request`; the dupefilter fingerprints a `Request`; priority is read from `request.priority` and start-flag from `request.meta`. scrapy/pqueues.py:15, scrapy/pqueues.py:167, scrapy/pqueues.py:171, scrapy/dupefilters.py:23, scrapy/squeues.py:23
- → scrapy.settings (configuration): `get_spider_loader` reads `SPIDER_LOADER_CLASS`; `SpiderLoader` reads `SPIDER_MODULES`/`SPIDER_LOADER_WARN_ONLY`; `DownloaderAwarePriorityQueue` reads `CONCURRENT_REQUESTS_PER_IP`; `RFPDupeFilter` reads `DUPEFILTER_DEBUG`. scrapy/spiderloader.py:27, scrapy/spiderloader.py:58-59, scrapy/pqueues.py:330, scrapy/dupefilters.py:99
- → scrapy.spiders (Spider base) + scrapy.contracts/extensibility: `spiderloader` discovers `Spider` subclasses and resolves them by name / `handles_request`; `squeues` serializes against the active spider. scrapy/spiderloader.py:21, scrapy/spiderloader.py:126, scrapy/squeues.py:79
- ← scrapy.core (scheduler) consumes this component: the scheduler imports `ScrapyPriorityQueue` and `BaseDupeFilter`, and references the `squeues` classes as its default disk/memory queues — the boundary direction is scheduler-drives-backends, not the reverse. scrapy/core/scheduler.py:24, scrapy/core/scheduler.py:26, scrapy/core/scheduler.py:191-192
- ← scrapy.crawler consumes the spider loader: `crawler.py` imports `SpiderLoaderProtocol, get_spider_loader` and builds `self.spider_loader`. scrapy/crawler.py:22, scrapy/crawler.py:350
- (external) → `queuelib` (manifest dep `queuelib>=1.4.2`, pyproject.toml:21): `squeues` builds its disk/memory queues by subclassing `queuelib.queue.*`. scrapy/squeues.py:12, scrapy/squeues.py:149-176
- (external) → `zope.interface` (manifest dep `zope.interface>=5.1.0`, pyproject.toml:25): `spiderloader` declares `@implementer(ISpiderLoader)` and `verifyClass`-checks any configured loader. scrapy/spiderloader.py:8-9, scrapy/spiderloader.py:29, scrapy/spiderloader.py:50

## Data

- Disk-persisted request queues: `ScrapyPriorityQueue` writes one downstream-queue instance per (priority, start-flag) under a *key* persistence directory; subdir named by priority with an `s` suffix for start requests. scrapy/pqueues.py:88-98, scrapy/pqueues.py:151-164
- Per-slot persistence directories: `DownloaderAwarePriorityQueue` creates one subdir per download slot (domain), name path-sanitized + MD5-hash-suffixed to avoid collisions. scrapy/pqueues.py:290-296, scrapy/pqueues.py:391 (sanitizer at scrapy/pqueues.py:22-37)
- On-disk queue files: `squeues` `FifoDiskQueue`/`LifoDiskQueue` subclasses auto-create the parent directory (`_with_mkdir`) and persist serialized request dicts. scrapy/squeues.py:27-35, scrapy/squeues.py:149-174
- Dupefilter persistence: when `JOBDIR` is set, seen fingerprints are tracked in `requests.seen` (one hex fingerprint per line), opened append+read, line-buffered with `write_through`, and pre-loaded into an in-memory `set` on init. scrapy/dupefilters.py:67-70, scrapy/dupefilters.py:87-94
- In-memory de-dup set: `RFPDupeFilter.fingerprints` is a `set[str]` consulted/updated on every `request_seen`. scrapy/dupefilters.py:83, scrapy/dupefilters.py:106-113
- Spider registry: `SpiderLoader._spiders` (name→class dict) and `_found` (name→locations, for duplicate detection) built by walking `SPIDER_MODULES`. scrapy/spiderloader.py:60-62, scrapy/spiderloader.py:84-105

## Boundary rules

- This layer is backend-only: it is imported and driven by `scrapy.core.scheduler` / `scrapy.crawler`; it never imports the scheduler or engine modules — it only reaches the downloader indirectly through the live `crawler.engine.downloader` handle. scrapy/core/scheduler.py:26, scrapy/pqueues.py:262
- All concrete backends are constructed via the `from_crawler`/`from_settings` factory convention rather than direct construction, keeping them swappable by setting. scrapy/pqueues.py:100-116, scrapy/squeues.py:82-86, scrapy/dupefilters.py:96-104, scrapy/spiderloader.py:107-109
- Pluggability is enforced by contract: the spider loader is checked against the `ISpiderLoader` zope interface via `verifyClass` before use; queues conform to the structural `QueueProtocol`; the loader to `SpiderLoaderProtocol`. scrapy/spiderloader.py:29, scrapy/pqueues.py:40-49, scrapy/spiderloader.py:33-47
- `DownloaderAwarePriorityQueue` refuses to operate when `CONCURRENT_REQUESTS_PER_IP != 0` (raises `ValueError`) — a hard incompatibility guard at construction. scrapy/pqueues.py:330-333
- Resumed crawls must use the same priority-queue class: a non-dict `slot_startprios` is rejected with an explicit "incompatible priority queue" error. scrapy/pqueues.py:335-344

## Key facts

- Priority inversion convention: stored priority is `-request.priority`, and **lower numbers are higher priority** with one internal queue per priority value. scrapy/pqueues.py:70-71, scrapy/pqueues.py:166-167
- Start requests get their own parallel queue family: when a `start_queue_cls` is configured and `request.meta["is_start_request"]` is true, the request goes to `_start_queues` (keyed `<prio>s`) instead of `queues`, and `pop` drains regular before start at a given priority. scrapy/pqueues.py:171-179, scrapy/pqueues.py:184-212
- `curprio` is the cached minimum active priority, recomputed lazily by `_update_curprio` from non-empty buckets; `peek` is optional and raises `NotImplementedError` if the downstream queue lacks it. scrapy/pqueues.py:133, scrapy/pqueues.py:214-221, scrapy/pqueues.py:223-237, scrapy/squeues.py:61-66
- Downloader-aware fairness: `_next_slot` picks the slot with the fewest active downloads, with a round-robin tiebreak that prefers the next slot after the last selected (`_last_selected_slot`). scrapy/pqueues.py:277-279, scrapy/pqueues.py:358-383
- Queue persistence is built by class-factory composition: `_serializable_queue` (push/pop/peek serialize layer) ∘ `_with_mkdir` (dir creation) ∘ `queuelib.queue.*`, then `_scrapy_serialization_queue` adds `from_crawler` + request↔dict marshalling. scrapy/squeues.py:38-71, scrapy/squeues.py:74-110, scrapy/squeues.py:149-176
- Serialization technology choice: disk queues use pickle (protocol 4) or marshal; pickling errors (`PicklingError`/`AttributeError`/`TypeError`, the last from `parsel.Selector`) are normalized to `ValueError`. scrapy/squeues.py:139-145, scrapy/squeues.py:171-174
- De-dup identity = request fingerprint: `RFPDupeFilter` filters on the canonical url+method+body fingerprint (hex), delegating to a pluggable `RequestFingerprinterProtocol` (default `RequestFingerprinter`). scrapy/dupefilters.py:53-57, scrapy/dupefilters.py:80-82, scrapy/dupefilters.py:115-117
- `BaseDupeFilter` is the documented no-op default (filters nothing); its `open`/`close` may return a Twisted `Deferred`, and `BaseDupeFilter.log` is deprecated. scrapy/dupefilters.py:27-29, scrapy/dupefilters.py:38-50
- Spider discovery is import-time eager: `SpiderLoader.__init__` walks all `SPIDER_MODULES` immediately, warns (not raises) on import/syntax errors only when `SPIDER_LOADER_WARN_ONLY`, and warns on duplicate spider names. scrapy/spiderloader.py:62, scrapy/spiderloader.py:89-105, scrapy/spiderloader.py:64-82
- `DummySpiderLoader` exists as an explicit "load no spiders" backend (every `load` raises `KeyError`). scrapy/spiderloader.py:136-148
- Filesystem-safe slot naming combines a char-sanitized prefix with an MD5 suffix to disambiguate slots that sanitize to the same string. scrapy/pqueues.py:22-37
-->
<!-- DEEPINIT:END -->
