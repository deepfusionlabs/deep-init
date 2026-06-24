<!-- DEEPINIT:START -->
# Component: scrapy.cmdline + scrapy.commands (CLI)

Path: `scrapy/cmdline.py`, `scrapy/commands/`
Provenance: BLIND re-derivation from code only (docs removed). Every claim cites a file:line opened under `C:/tmp/p5_scrapy_blind`.

## Role

- The `scrapy` console entry point: `execute` parses `argv`, resolves a command name to a `ScrapyCommand` subclass, builds an argparse parser from it, optionally wires up a crawler process, and dispatches to `cmd.run` — it is the process bootstrap layer, not crawl logic (`scrapy/cmdline.py:169-215`).

## Dependencies (edges)

- → scrapy.crawler — imports and instantiates `AsyncCrawlerProcess` / `CrawlerProcess`, choosing between them on settings, and assigns the result to `cmd.crawler_process` (`scrapy/cmdline.py:13`, `scrapy/cmdline.py:206-213`).
- → scrapy.settings — `execute` loads settings via `get_project_settings`, calls `settings.setdict(cmd.default_settings, priority="command")`, and reads `TWISTED_REACTOR` / `FORCE_CRAWLER_PROCESS` / `TWISTED_REACTOR_ENABLED` to pick the process class (`scrapy/cmdline.py:16`, `scrapy/cmdline.py:174`, `scrapy/cmdline.py:200`, `scrapy/cmdline.py:208-210`).
- → scrapy.utils — imports `walk_modules_iter` (command discovery), `get_project_settings`/`inside_project`, `garbage_collect`, and `_asyncio_reactor_path` (`scrapy/cmdline.py:15-18`); base class imports `arglist_to_dict`/`feed_process_params_from_cli` from `scrapy.utils.conf` (`scrapy/commands/__init__.py:18`).
- → scrapy.utils (reactor/async glue) — `shell.py` uses `_schedule_coro` and `parse.py` uses `_schedule_coro`/`aiter_errback`/`deferred_from_coro` from `scrapy.utils.defer` (`scrapy/commands/shell.py:17`, `scrapy/commands/parse.py:18`).
- → scrapy (top-level package) — `cmdline` reads `scrapy.__version__`; `startproject`/`genspider`/`bench`/`version` import `scrapy` for `__version__` / `__path__` / `Spider` / `Request` (`scrapy/cmdline.py:11`, `scrapy/cmdline.py:101`, `scrapy/commands/startproject.py:11`, `scrapy/commands/bench.py:9`, `scrapy/commands/version.py:4`).
- → scrapy.core (engine / scraper) — `shell.py` calls `crawler._create_engine` + `engine.start_async(...)` to manually drive the engine; `parse.py` reaches `pcrawler.engine.scraper.itemproc` to push items through the pipeline (`scrapy/commands/shell.py:99-100`, `scrapy/commands/shell.py:112-114`, `scrapy/commands/parse.py:284-291`).
- → scrapy.http — `fetch.py`/`parse.py`/`shell.py`/`bench.py` import `Request`/`Response`/`TextResponse` to build/print downloader requests (`scrapy/commands/fetch.py:11`, `scrapy/commands/parse.py:15`, `scrapy/commands/shell.py:15`, `scrapy/commands/bench.py:11`).
- → scrapy.spiders / spiderloader — `runspider`/`fetch`/`shell`/`parse` use `iter_spider_classes`/`spidercls_for_request`/`DefaultSpider` and `DummySpiderLoader`; `list`/`edit`/`genspider` use `get_spider_loader`; `check`/`fetch`/`shell`/`parse` call `crawler_process.spider_loader.load(...)` (`scrapy/commands/runspider.py:10-11`, `scrapy/commands/fetch.py:13`, `scrapy/commands/shell.py:18`, `scrapy/commands/list.py:6`, `scrapy/commands/edit.py:8`, `scrapy/commands/genspider.py:14`, `scrapy/commands/check.py:87`).
- → scrapy.contracts — `check.py` builds a `ContractsManager` from `SPIDER_CONTRACTS` and runs spider contracts via `unittest` (`scrapy/commands/check.py:11`, `scrapy/commands/check.py:79`).
- → scrapy.linkextractors — `bench.py`'s `_BenchSpider` uses `LinkExtractor` to follow links (`scrapy/commands/bench.py:12`, `scrapy/commands/bench.py:59`).
- → scrapy item data layer — `parse.py` imports `ItemAdapter` (third-party `itemadapter`) to render scraped items as dicts (`scrapy/commands/parse.py:9`, `scrapy/commands/parse.py:173`).
- → scrapy.exceptions — every command raises `UsageError` for arg validation; base imports `ScrapyDeprecationWarning` (`scrapy/cmdline.py:14`, `scrapy/commands/__init__.py:17`).
- → scrapy.shell — `shell.py` instantiates the interactive `Shell` object (`scrapy/commands/shell.py:16`, `scrapy/commands/shell.py:94`).
- → Twisted (external, technology choice) — base class uses `twisted.python.failure` (`--pdb`); `parse.py` uses `twisted.internet.defer.Deferred`/`maybeDeferred` (`scrapy/commands/__init__.py:15`, `scrapy/commands/parse.py:10`).

## Data

- Owns no persistent store. CLI-driven file writes: `--pidfile` writes the PID to a file (`scrapy/commands/__init__.py:133-136`); `--profile` dumps cProfile stats to a file (`scrapy/cmdline.py:233-234`); `startproject` copies a template tree and renders project files (`scrapy/commands/startproject.py:109-123`); `genspider` copies/renders a spider `.py` into `NEWSPIDER_MODULE` (`scrapy/commands/genspider.py:162-164`).
- Reads from disk: `runspider` imports a spider from an arbitrary `.py`/`.pyw` file by manipulating `sys.path` (`scrapy/commands/runspider.py:19-29`); `genspider`/`startproject` read template files from `TEMPLATES_DIR` or `scrapy/templates` (`scrapy/commands/genspider.py:226-234`, `scrapy/commands/startproject.py:133-141`).

## Boundary rules

- All commands subclass the abstract `ScrapyCommand` (`scrapy/commands/__init__.py:27`); `run` and `short_desc` are `@abstractmethod` (`scrapy/commands/__init__.py:56-57`, `scrapy/commands/__init__.py:141-146`); spider-running commands share `BaseRunSpiderCommand` for `-a`/`-o`/`-O` handling (`scrapy/commands/__init__.py:149-196`).
- Command discovery is by convention, not registry: one `Command` class per module under `scrapy.commands`, mapped to the command name by its module's last path segment (`scrapy/cmdline.py:54-60`), excluding the base classes (`scrapy/cmdline.py:49`).
- `requires_project` gates project-only commands so they are hidden/refused outside a project dir (`scrapy/commands/__init__.py:28`, `scrapy/cmdline.py:57`, `scrapy/cmdline.py:134-140`); `crawl`/`parse`/`check`/`list`/`edit` set it True (`scrapy/commands/crawl.py:13`, `scrapy/commands/parse.py:39`, `scrapy/commands/check.py:46`, `scrapy/commands/list.py:13`, `scrapy/commands/edit.py:12`).
- `requires_crawler_process` decides whether `execute` builds a crawler process before `run`; commands needing no engine (`startproject`/`genspider`/`list`/`settings`/`edit`/`version`) opt out (`scrapy/commands/__init__.py:29`, `scrapy/cmdline.py:206`, `scrapy/commands/startproject.py:36`, `scrapy/commands/list.py:14`).
- Extension boundary: third-party commands are loaded from the `scrapy.commands` entry-point group and from `settings["COMMANDS_MODULE"]`, merged over the built-ins (`scrapy/cmdline.py:63-84`).
- Layer position: this is the outermost orchestration layer — it constructs `CrawlerProcess` and drives it (`crawl`/`start`), but defers all crawl execution to scrapy.crawler/scrapy.core; it never implements scheduling or downloading itself (`scrapy/commands/crawl.py:30-33`).

## Key facts

- The single declared console entry point is `scrapy = "scrapy.cmdline:execute"` (`pyproject.toml:63-64`).
- Async-reactor selection is automatic: when `TWISTED_REACTOR` is the asyncio reactor and `FORCE_CRAWLER_PROCESS` is off, `AsyncCrawlerProcess` is used; otherwise (or with the reactor disabled) `CrawlerProcess` (`scrapy/cmdline.py:206-213`).
- Custom argparse subclass `ScrapyArgumentParser` special-cases `-:`-prefixed tokens (e.g. `-o -:json`) so a leading `-` value is not parsed as a flag (`scrapy/cmdline.py:28-37`).
- Global options (`--logfile`/`-L`/`--nolog`/`--profile`/`--pidfile`/`-s`/`--pdb`) are injected by the base class and applied to settings at cmdline priority in `process_options` (`scrapy/commands/__init__.py:77-139`).
- `-s NAME=VALUE`, `-a NAME=VALUE`, and `-o/-O FILE` mutate the live `Settings` object (e.g. `-o` becomes the `FEEDS` setting) before the engine starts (`scrapy/commands/__init__.py:116`, `scrapy/commands/__init__.py:189-196`).
- Exit-code protocol: each command sets `self.exitcode`, which `execute` passes to `sys.exit`; crawl/runspider set exitcode 1 on `bootstrap_failed`; `_run_print_help` exits 2 on `UsageError` (`scrapy/cmdline.py:215`, `scrapy/commands/crawl.py:33-34`, `scrapy/cmdline.py:166`).
- `runspider` loads a self-contained spider by temporarily prepending the file's dir to `sys.path`, requiring `.py`/`.pyw`, and uses `DummySpiderLoader` since there is no project (`scrapy/commands/runspider.py:19-29`, `scrapy/commands/runspider.py:33-35`).
- `shell` bypasses the normal `crawler_process.crawl` flow and manually creates+starts the engine in/out of the reactor, running the crawler in a daemon thread (`scrapy/commands/shell.py:84-101`, `scrapy/commands/shell.py:127-135`).
- `check` runs spider contracts on top of Python's `unittest` `TextTestRunner`, gating exitcode on test success (`scrapy/commands/check.py:80`, `scrapy/commands/check.py:122`).
- `genspider -e` and `edit` shell out via `os.system(...)` to an external editor (`scrapy/commands/genspider.py:123`, `scrapy/commands/edit.py:48`); `bench` spawns `scrapy.utils.benchserver` as a subprocess (`scrapy/commands/bench.py:39-43`).
- `garbage_collect` is force-run in a `finally` on exit to flush Twisted `DebugInfo.__del__` errors under PyPy (`scrapy/cmdline.py:240-244`).
- The help formatter must use `builtins.list` because `scrapy.commands.list` shadows the `list` builtin (`scrapy/commands/__init__.py:218-220`).
<!-- DEEPINIT:END -->
