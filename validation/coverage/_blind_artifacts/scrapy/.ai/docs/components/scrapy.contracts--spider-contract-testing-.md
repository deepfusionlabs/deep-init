<!-- DEEPINIT:START -->
<!--
provenance:
 stage: extract (BLIND re-derivation, code-only)
 component: scrapy.contracts (spider contract testing)
 path: scrapy/contracts/
 inputs: scrapy/contracts/__init__.py, scrapy/contracts/default.py, scrapy/commands/check.py, scrapy/settings/default_settings.py, pyproject.toml
 doc_in_inputs: false
 date: 2026-06-13
-->

# scrapy.contracts (spider contract testing)

## Role

- Provides a docstring-driven test framework that turns `@`-prefixed directives in a spider callback's docstring into synthetic `Request`s plus pre/post validation hooks, and runs them as `unittest` cases so a spider's callbacks can be checked without a live crawl. — `scrapy/contracts/__init__.py:92` (`class ContractsManager`), `scrapy/contracts/__init__.py:24` (`class Contract` — "Abstract class for contracts")

## Dependencies (edges)

- → **scrapy.http (Request/Response model)** — imports `Request, Response`; `Request` is the default request class built for each tested method and `Response` is the type passed to pre/post hook wrappers. — `scrapy/contracts/__init__.py:12`, `scrapy/contracts/__init__.py:142` (`request_cls = Request`), `scrapy/contracts/default.py:10`
- → **scrapy.utils (shared infrastructure)** — imports `get_spec` from `scrapy.utils.python` (introspects `Request.__init__` to compute positional/keyword args) and `iterate_spider_output` from `scrapy.utils.spider` (normalizes callback output to an iterable). — `scrapy/contracts/__init__.py:13` (resolves to `scrapy/utils/python.py:215`), `scrapy/contracts/__init__.py:14` (resolves to `scrapy/utils/spider.py:39`), used at `scrapy/contracts/__init__.py:148` and `:55`/`:71`/`:186`
- → **scrapy.signals / middleware base / addons (extensibility core: exceptions)** — `default.py` imports `ContractFail` from `scrapy.exceptions`, raised by `ReturnsContract`/`ScrapesContract` to signal a failed assertion. — `scrapy/contracts/default.py:9` (resolves to `scrapy/exceptions.py:122`, `class ContractFail(AssertionError)`), raised at `scrapy/contracts/default.py:112`, `:130`
- → **scrapy.spiders (Spider base)** — `from_spider` / `tested_methods_from_spidercls` operate on a `Spider` instance / `type[Spider]`; the import is `TYPE_CHECKING`-only (type hints), no runtime dependency. — `scrapy/contracts/__init__.py:21`, `scrapy/contracts/__init__.py:99`, `:125`
- → **scrapy.utils (reactor/async glue, indirect)** — guards against async callbacks: a callback returning an `AsyncGenerator`/`CoroutineType` raises `TypeError("Contracts don't support async callbacks")`. — `scrapy/contracts/__init__.py:53-54`, `:69-70`
- → **third-party `itemadapter`** — `default.py` uses `ItemAdapter` / `is_item` to detect items and check scraped fields. — `scrapy/contracts/default.py:6`, used at `:127` (`ItemAdapter(x)`) and `:74`/`:126` (`is_item`)
- INBOUND (not an outgoing edge, recorded for context): consumed by **scrapy.commands (CLI)** — `scrapy/commands/check.py:11` imports `ContractsManager`, instantiates it from the `SPIDER_CONTRACTS` component list (`check.py:77-79`) and drives `conman.from_spider` / `tested_methods_from_spidercls` under the `scrapy check` command. The default contract set is registered in **scrapy.settings** via `SPIDER_CONTRACTS_BASE`. — `scrapy/settings/default_settings.py:540-545`

## Data

- Owns no persistence / external data store. The only mutable state is a **class-level** registry `ContractsManager.contracts: ClassVar[dict[str, type[Contract]]]` mapping a contract name to its class, populated in `__init__`. — `scrapy/contracts/__init__.py:93`, `:95-97`
- Reads spider state indirectly: contract directives are parsed from each tested method's `__doc__` (docstring), and `_create_testcase` reads `method.__self__.name` (the bound spider's `name`). — `scrapy/contracts/__init__.py:110-111`, `:201`

## Boundary rules

- **CLI/check-only layer:** this subsystem is invoked only by the `scrapy check` command path (`scrapy.commands.check`), not by the crawl engine; the command sets the env flag `SCRAPY_CHECK=true` and monkey-patches `spidercls.start` to yield contract requests. — `scrapy/commands/check.py:93`, `:96`, `:89-91`
- **Settings-driven plug-in registry:** the active contract classes are not hard-coded in this component; they come from the `SPIDER_CONTRACTS` / `SPIDER_CONTRACTS_BASE` component-priority dicts resolved by the command, so users can add/override contracts via settings. — `scrapy/settings/default_settings.py:539-546`, `scrapy/commands/check.py:76-79`
- **Async-callback exclusion:** contracts deliberately refuse async (coroutine / async-generator) callbacks rather than awaiting them, keeping the checker synchronous. — `scrapy/contracts/__init__.py:54`, `:70`
- **Test-framework boundary:** results are reported through the stdlib `unittest.TestResult` protocol (`startTest`/`stopTest`/`addSuccess`/`addFailure`/`addError`), so it bridges into Python's `unittest` rather than Scrapy's own logging. — `scrapy/contracts/__init__.py:10`, `:43-51`, `:73-81`

## Key facts

- **Contract extension contract (the data structure):** a `Contract` subclass declares a `name` (the `@name` directive), optionally `request_cls`, and any of three hooks — `adjust_request_args` (mutate request kwargs), `pre_process` (run before callback), `post_process` (validate callback output); hooks are wired only if present via `hasattr`. — `scrapy/contracts/__init__.py:27-28`, `:36`, `:62`, `:88-89`
- **Hook ordering invariant:** pre-hooks are applied in reversed contract order, post-hooks in forward order, so hooks execute symmetrically around the callback. — `scrapy/contracts/__init__.py:165-168`
- **Directive parsing:** contract directives are extracted by regex from the docstring — a method is "tested" if its docstring contains a line matching `^\s*@` (multiline), and each `@(\w+) (.*)` line is parsed into `(name, args)`. — `scrapy/contracts/__init__.py:100`, `:114-119`
- **Request construction invariant:** built requests force `dont_filter=True` (so the same URL can test multiple callbacks) and set `callback=method`; the request is only built if all required positional args of `request_cls.__init__` are satisfied, else `from_method` returns `None`. — `scrapy/contracts/__init__.py:150-153`, `:161-162`, `:172`
- **`_clean_req` neutralizes side effects:** after hooks, the callback is wrapped so it returns nothing (drains output, records callback exceptions as test errors) and an errback is installed to record download failures as errors. — `scrapy/contracts/__init__.py:174-197`
- **Default built-in contracts (5):** `UrlContract` (`@url`, sets request url, mandatory), `CallbackKeywordArgumentsContract` (`@cb_kwargs`, JSON), `MetadataContract` (`@meta`, JSON), `ReturnsContract` (`@returns request(s)/item(s) [min [max]]`, bounds-check output count), `ScrapesContract` (`@scrapes field...`, asserts item fields present). — `scrapy/contracts/default.py:17`, `:29`, `:43`, `:57`, `:117`
- **`ReturnsContract` type map + bounds:** verifies output objects against `object_type_verifiers` (request/requests → `isinstance Request`; item/items → `is_item`) with default `min_bound=1`, `max_bound=inf`. — `scrapy/contracts/default.py:71-76`, `:89-96`, `:104`
- **Per-contract priorities in defaults:** `Url`/`cb_kwargs`/`meta` at priority 1, `Returns` at 2, `Scrapes` at 3 — controlling apply order via the settings component list. — `scrapy/settings/default_settings.py:541-545`
- **R1 grounding note:** all imports of other `scrapy.*` components were confirmed against existing source files (`scrapy/utils/python.py:215`, `scrapy/utils/spider.py:39`, `scrapy/exceptions.py:122`, `scrapy/http/__init__.py:12`/`:15`). No edges to scrapy.core, scrapy.crawler, scrapy.downloadermiddlewares, scrapy.spidermiddlewares, scrapy.pipelines, scrapy.extensions, scrapy.selector, scrapy.linkextractors, or scrapy.settings were found in this component's two source files (settings coupling is by string class-path only, resolved by the CLI). — `scrapy/contracts/__init__.py:1-21`, `scrapy/contracts/default.py:1-13`
<!-- DEEPINIT:END -->
