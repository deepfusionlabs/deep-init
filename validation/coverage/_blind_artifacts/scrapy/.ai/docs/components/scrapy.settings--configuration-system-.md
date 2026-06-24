<!-- DEEPINIT:START -->
<!--
provenance:
 stage: extract
 component: scrapy.settings (configuration system)
 run: p5-scrapy-blind
 inputs: scrapy/settings/__init__.py, scrapy/settings/default_settings.py, pyproject.toml
 date: 2026-06-13
 mode: BLIND (code-only re-derivation; prose docs removed from tree)
-->

# scrapy.settings (configuration system)

Path: `scrapy/settings/` — two files: `__init__.py`, `default_settings.py`.

## Role

- Priority-aware configuration store for the whole framework: a `MutableMapping[str, Any]` (`BaseSettings`) that pairs every value with a numeric priority and supports being frozen immutable, plus `Settings`, which pre-loads the global default registry on construction. (`scrapy/settings/__init__.py:79`, `scrapy/settings/__init__.py:690`)

## Dependencies (edges)

NOTE on edge kinds: this component has only FOUR compile-time imports (all into `scrapy.exceptions` and `scrapy.utils`). Every other coupling to a sibling component is via an **import-string literal in the default registry** (`default_settings.py`) that this module merely *stores as a string*; it is resolved to a real class later by the consumer that calls `load_object`, not here. Those are recorded below as `default-registry-ref` (a weaker, runtime-string coupling), distinct from real imports.

Compile-time imports:
- scrapy.utils — imports `load_object` (used to resolve component-priority-dict keys / `_BASE` overrides) and `global_object_name` (used to normalize keys to import paths for dedup). (`scrapy/settings/__init__.py:14`, `scrapy/settings/__init__.py:15`; used at `scrapy/settings/__init__.py:366`, `scrapy/settings/__init__.py:370`)
- scrapy signals + middleware base + addons — via `scrapy.exceptions.ScrapyDeprecationWarning`, imported for deprecation warnings on `CONCURRENT_REQUESTS_PER_IP` / `DNS_RESOLVER`. (`scrapy/settings/__init__.py:12`, used at `scrapy/settings/__init__.py:157`, `scrapy/settings/__init__.py:166`)

Default-registry string references (stored here, resolved elsewhere; kind=default-registry-ref):
- scrapy.core.downloader — `DOWNLOADER` default `"scrapy.core.downloader.Downloader"` and `DOWNLOAD_HANDLERS_BASE` maps schemes to `scrapy.core.downloader.handlers.*` handler classes. (`scrapy/settings/default_settings.py:307`, `scrapy/settings/default_settings.py:286`)
- scrapy.core (engine / scheduler / scraper) — `SCHEDULER` default `"scrapy.core.scheduler.Scheduler"`. (`scrapy/settings/default_settings.py:529`)
- scrapy.downloadermiddlewares — `DOWNLOADER_MIDDLEWARES_BASE` enumerates the ordered downloader-middleware chain (offsite 50 … httpcache 900). (`scrapy/settings/default_settings.py:315`)
- scrapy.spidermiddlewares — `SPIDER_MIDDLEWARES_BASE` enumerates the ordered spider-middleware chain (start 25 … depth 900); also `REFERRER_POLICY` default `"scrapy.spidermiddlewares.referer.DefaultReferrerPolicy"`. (`scrapy/settings/default_settings.py:552`, `scrapy/settings/default_settings.py:500`)
- scrapy.extensions — `EXTENSIONS_BASE` enumerates lifecycle extensions (corestats, telnet, memusage, feedexport, autothrottle, …) and `FEED_STORAGES_BASE` / `HTTPCACHE_POLICY` / `HTTPCACHE_STORAGE` point at `scrapy.extensions.*`. (`scrapy/settings/default_settings.py:344`, `scrapy/settings/default_settings.py:376`, `scrapy/settings/default_settings.py:417`)
- scrapy.pipelines — `ITEM_PROCESSOR` default `"scrapy.pipelines.ItemPipelineManager"`. (`scrapy/settings/default_settings.py:435`)
- scrapy.contracts — `SPIDER_CONTRACTS_BASE` maps the built-in contracts (`scrapy.contracts.default.*`) to order ints. (`scrapy/settings/default_settings.py:540`)
- scrapy item + loader + exporters — `DEFAULT_ITEM_CLASS` default `"scrapy.item.Item"` and `FEED_EXPORTERS_BASE` maps formats to `scrapy.exporters.*ItemExporter`. (`scrapy/settings/default_settings.py:263`, `scrapy/settings/default_settings.py:363`)
- scrapy queues + dupefilter + spiderloader — `SCHEDULER_DISK_QUEUE`/`SCHEDULER_MEMORY_QUEUE`/`SCHEDULER_PRIORITY_QUEUE` point at `scrapy.squeues`/`scrapy.pqueues`; `DUPEFILTER_CLASS` → `scrapy.dupefilters.RFPDupeFilter`; `SPIDER_LOADER_CLASS` → `scrapy.spiderloader.SpiderLoader`. (`scrapy/settings/default_settings.py:531`, `scrapy/settings/default_settings.py:336`, `scrapy/settings/default_settings.py:548`)
- scrapy.utils (reactor / request) — `TWISTED_REACTOR` default `"twisted.internet.asyncioreactor.AsyncioSelectorReactor"`, `REQUEST_FINGERPRINTER_CLASS` → `scrapy.utils.request.RequestFingerprinter`. (`scrapy/settings/default_settings.py:580`, `scrapy/settings/default_settings.py:503`)
- scrapy.commands (CLI) — `COMMANDS_MODULE` / `NEWSPIDER_MODULE` / `SPIDER_MODULES` / `TEMPLATES_DIR` / `EDITOR` are CLI/project-scaffolding settings consumed by the command layer. (`scrapy/settings/default_settings.py:247`, `scrapy/settings/default_settings.py:485`, `scrapy/settings/default_settings.py:575`)

## Data

- Owns no external persistence. In-memory store is `self.attributes: dict[str, SettingsAttribute]`, each `SettingsAttribute` holding `(value, priority)`. (`scrapy/settings/__init__.py:105`, `scrapy/settings/__init__.py:59`)
- References (as string defaults, does not itself read/write) on-disk locations used by other components: `JOBDIR` (default `None`), `HTTPCACHE_DIR` (default `"httpcache"`), `FEED_TEMPDIR`, `FILES_STORE`/`IMAGES_STORE`. (`scrapy/settings/default_settings.py:437`, `scrapy/settings/default_settings.py:410`, `scrapy/settings/default_settings.py:387`, `scrapy/settings/default_settings.py:391`)
- `default_settings.py` is a flat module of UPPERCASE module-level globals; `Settings.__init__` ingests it via `setmodule`, which copies every `key.isupper` global. (`scrapy/settings/__init__.py:558`, `scrapy/settings/__init__.py:706`)

## Boundary rules

- Priority ladder is the layering invariant: `SETTINGS_PRIORITIES = {default:0, command:10, addon:15, project:20, spider:30, cmdline:40}`; a `set` only takes effect if the incoming priority `>=` the stored priority. (`scrapy/settings/__init__.py:31`, `scrapy/settings/__init__.py:69`)
- Immutability gate: every mutator routes through `_assert_mutability`, which raises `TypeError` once `freeze` has set `self.frozen=True` — settings are frozen before the crawl runs. (`scrapy/settings/__init__.py:608`, `scrapy/settings/__init__.py:624`)
- `_BASE` convention: framework-supplied component lists live in `*_BASE` settings; user overrides live in the un-suffixed twin, and `getwithbase` composes `name_BASE` then `name` so user entries win. (`scrapy/settings/__init__.py:319`, `scrapy/settings/default_settings.py:315`)
- This module is a low-level leaf: it depends only on `scrapy.exceptions` and `scrapy.utils`, and must NOT import the higher-level components it configures (they are referenced only as import-string defaults to avoid import cycles). (`scrapy/settings/__init__.py:12`, `scrapy/settings/default_settings.py:307`)

## Key facts

- Component-priority-dictionary semantics: `get_component_priority_dict_with_base` resolves each key via `load_object` to its import path so a class and its dotted-path string dedupe to one entry, then restores the original representation; `replace_in_component_priority_dict` / `set_in_component_priority_dict` / `setdefault_in_component_priority_dict` mutate these dicts regardless of the setting's own priority. (`scrapy/settings/__init__.py:338`, `scrapy/settings/__init__.py:409`, `scrapy/settings/__init__.py:481`)
- Nested `BaseSettings` for per-key priorities: `Settings.__init__` promotes every default that is a `dict` into a `BaseSettings` instance so each key inside (e.g. a middleware ordering) carries its own priority; `SettingsAttribute` propagates `maxpriority` of a nested `BaseSettings`. (`scrapy/settings/__init__.py:709`, `scrapy/settings/__init__.py:62`)
- Typed accessors with coercion: `getbool` accepts 0/1/'0'/'1'/True/False/'true'/'false'; `getlist` splits a string on ","; `getdict`/`getdictorlist` parse JSON strings — designed so env-var string values coerce correctly. (`scrapy/settings/__init__.py:171`, `scrapy/settings/__init__.py:225`, `scrapy/settings/__init__.py:270`)
- Deprecation shims live here: `get` warns on `CONCURRENT_REQUESTS_PER_IP` and `DNS_RESOLVER`; `default_settings.__getattr__` warns and returns 0 for the removed `CONCURRENT_REQUESTS_PER_IP` global (it is absent from `__all__`). (`scrapy/settings/__init__.py:152`, `scrapy/settings/__init__.py:161`, `scrapy/settings/default_settings.py:589`)
- Technology choices baked into defaults: Twisted reactor defaults to the asyncio selector reactor; default scheduler priority queue is `DownloaderAwarePriorityQueue`; default request fingerprinter and dupefilter (`RFPDupeFilter`) are set here. (`scrapy/settings/default_settings.py:580`, `scrapy/settings/default_settings.py:533`, `scrapy/settings/default_settings.py:336`)
- `iter_default_settings` / `overridden_settings` reflect over `default_settings` globals (UPPERCASE filter) to compute which settings differ from defaults — used to report effective overrides. (`scrapy/settings/__init__.py:715`, `scrapy/settings/__init__.py:722`)
- Manifest pins this module: `pyproject.toml` carries a dedicated mypy override `module = "scrapy.settings.default_settings"` (`ignore_errors = true`), confirming the default registry is a recognized special module. (`pyproject.toml:120`)
<!-- DEEPINIT:END -->
