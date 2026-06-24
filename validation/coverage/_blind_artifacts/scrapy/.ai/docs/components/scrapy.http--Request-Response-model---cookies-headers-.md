<!-- DEEPINIT:START -->
<!--
Provenance:
 stage: EXTRACT (blind re-derivation, code-only)
 component: scrapy.http (Request/Response model + cookies/headers)
 path: scrapy/http/
 inputs: scrapy/http/**, pyproject.toml, scrapy/__init__.py (for re-export grounding)
 date: 2026-06-13
 rule: R1 — every claim grounded to a file:line actually opened; prose docs excluded.
-->

# scrapy.http — Request/Response model + cookies/headers

## Role

- The HTTP data-model package: defines the `Request`/`Response` value objects (plus their typed subclasses and the `Headers`/`CookieJar` helpers) that the engine, downloader, middlewares, spiders and pipelines pass around — "Module containing all HTTP related classes" (`scrapy/http/__init__.py:2`). `Request` "represents an HTTP request, which is usually generated in a Spider and executed by the Downloader" (`scrapy/http/request/__init__.py:85-87`); `Response` "is usually downloaded (by the Downloader) and fed to the Spiders for processing" (`scrapy/http/response/__init__.py:36-38`).

## Dependencies (edges)

- → **scrapy.utils** (shared infrastructure): `Request`/`Response` subclass `object_ref` for live-instance tracking — `from scrapy.utils.trackref import object_ref` (`scrapy/http/request/__init__.py:30`, `scrapy/http/response/__init__.py:17`). (import)
- → **scrapy.utils**: URL safety/curl/encoding/python helpers — `safe_url_string` via w3lib (`scrapy/http/request/__init__.py:23`), `curl_to_request_kwargs` (`scrapy/http/request/__init__.py:28`), `to_bytes`/`to_unicode`/`memoizemethod_noargs` (`scrapy/http/request/__init__.py:29`, `scrapy/http/headers.py:9`, `scrapy/http/response/text.py:26`). (import)
- → **scrapy.utils**: `CaselessDict`/`CaseInsensitiveDict` back the `Headers` class — `from scrapy.utils.datatypes import CaseInsensitiveDict, CaselessDict` (`scrapy/http/headers.py:8`); `Headers(CaselessDict)` (`scrapy/http/headers.py:23`). (import / subclass)
- → **scrapy.utils**: cookie host/scheme resolution + base-url lookup — `urlparse_cached` (`scrapy/http/cookies.py:9`), `get_base_url` (`scrapy/http/response/text.py:27`). (import / runtime-call)
- → **scrapy.utils**: deprecation machinery wraps `FormRequest` — `create_deprecated_class` (`scrapy/http/__init__.py:20`, used at `scrapy/http/__init__.py:27`); `get_func_args` for xmlrpc dumps args (`scrapy/http/request/rpc.py:16`). (import / runtime-call)
- → **scrapy** (root) / item data layer: `Response.cb_kwargs`/`meta` proxy through to the bound `Request`, and `to_dict(spider=...)` types against `scrapy.Spider` — `import scrapy` (`scrapy/http/request/__init__.py:26`), `to_dict(self, *, spider: scrapy.Spider | None =...)` (`scrapy/http/request/__init__.py:384`). (import / type-ref) NOTE re-export inversion: the root package imports the model FROM here — `from scrapy.http import FormRequest, Request` (`scrapy/__init__.py:10`), so `scrapy.Request`/`scrapy.http.Request` are the same class.
- → **scrapy.selector + scrapy.linkextractors** (extraction): `TextResponse.selector` lazily builds a `Selector` over itself — `from scrapy.selector import Selector` (`scrapy/http/response/text.py:150`, deferred to break a circular import per the `# circular import` note `scrapy/http/response/text.py:149`); `css`/`xpath`/`jmespath` delegate to it (`scrapy/http/response/text.py:155-166`). (runtime-call, lazy)
- → **scrapy** (`scrapy.link.Link`): `Response.follow`/`follow_all` accept and unwrap `Link` objects — `from scrapy.link import Link` (`scrapy/http/response/__init__.py:16`), `if isinstance(url, Link): url = url.url` (`scrapy/http/response/__init__.py:248-249`). (import)
- → **scrapy** (`scrapy.exceptions`): non-text responses raise `NotSupported` from `css`/`xpath`/`jmespath` (`scrapy/http/response/__init__.py:13,206,212,218`); `FormRequest`/`form` deprecation raises `ScrapyDeprecationWarning` (`scrapy/http/request/form.py:18,35-40`; `scrapy/http/__init__.py:10,22-23`). (import)
- → external libs (technology choices, not internal components): `w3lib` for URL/encoding/headers (`scrapy/http/request/__init__.py:23`, `scrapy/http/response/text.py:16-23`, `scrapy/http/headers.py:6`); `parsel` for selectors/follow (`scrapy/http/response/text.py:15,200-202`); `parsel.csstranslator.HTMLTranslator` + `lxml.html` form parsing (`scrapy/http/request/form.py:15,24-30`); `defusedxml.xmlrpc.monkey_patch` hardens XML-RPC (`scrapy/http/request/rpc.py:13,18`); Twisted `Failure` typing for errbacks (`scrapy/http/request/__init__.py:35`, `scrapy/http/response/__init__.py:23`). (import)
- NO outgoing edges to scrapy.core / scrapy.core.downloader / scrapy.core.http2 / scrapy.crawler / scrapy.cmdline / scrapy.commands / scrapy.spiders (beyond the type-only `scrapy.Spider` ref above) / scrapy.downloadermiddlewares / scrapy.spidermiddlewares / scrapy.pipelines / scrapy.extensions / scrapy.settings / scrapy.contracts / signals: no imports of those packages exist in `scrapy/http/**` (verified across all files read). The data model is a leaf the rest of the framework depends ON, not the reverse.

## Data

- Owns no persistence / no DB / no on-disk store. The only stateful store is the in-memory **`CookieJar`**, a thin wrapper over the stdlib `http.cookiejar.CookieJar` — `from http.cookiejar import CookieJar as _CookieJar` (`scrapy/http/cookies.py:5`), `self.jar: _CookieJar = _CookieJar(self.policy)` (`scrapy/http/cookies.py:34`). Cookies are keyed/stored in the jar's `_cookies` dict-of-dict-of-dict (`scrapy/http/cookies.py:76`).
- Per-instance state is held in `__slots__` on `Request`/`Response` (e.g. `_url`, `_body`, `_headers`, `_meta`, `_cookies` — `scrapy/http/request/__init__.py:109-120`; `_url`,`_body`,`_headers`,`_flags`,status/request/certificate/ip/protocol — `scrapy/http/response/__init__.py:61-68`). `request.meta` / `cb_kwargs` are lazily-created dicts (`scrapy/http/request/__init__.py:239-249`).

## Boundary rules

- **Leaf data layer / no inward coupling to runtime components.** The package imports only `scrapy.utils`, `scrapy.selector` (lazily), `scrapy.link`, `scrapy.exceptions`, and the root `scrapy` namespace for typing — never the engine, downloader, middleware chains, or pipelines (verified, see Dependencies). It is imported by them.
- **Lazy import to break cycles.** `TextResponse.selector` defers `from scrapy.selector import Selector` to call time with an explicit `# circular import` comment (`scrapy/http/response/text.py:149-150`); `Request`/`Response` reference each other only under `TYPE_CHECKING` with `# circular import` notes (`scrapy/http/request/__init__.py:40-43`, `scrapy/http/response/__init__.py:28`).
- **bytes is the on-the-wire boundary type.** `Response.body` must be `bytes` and rejects `str` with a "use TextResponse or HtmlResponse" error (`scrapy/http/response/__init__.py:128-138`); `Headers` normalizes every key/value to `bytes` (`normkey`/`normvalue`/`_tobytes`, `scrapy/http/headers.py:43-68`). Decoding to text is exclusively `TextResponse`'s job (`Response.text` raises, `scrapy/http/response/__init__.py:196-200`; `TextResponse.text`, `scrapy/http/response/text.py:92-101`).
- **Text-only shortcuts gated by subtype.** Base `Response.css/xpath/jmespath` raise `NotSupported` (`scrapy/http/response/__init__.py:202-218`); only `TextResponse` (and its `HtmlResponse`/`XmlResponse`/`JsonResponse` subclasses) implement them (`scrapy/http/response/text.py:155-166`).
- **`Headers` is read by other components via the `WrappedRequest`/`WrappedResponse` urllib2-shaped adapters** so the stdlib cookiejar can drive cookie extraction/injection without the cookiejar knowing about Scrapy types (`scrapy/http/cookies.py:138-217`).

## Key facts

- **`__slots__` + `attributes` tuple drive copy/serialize.** Each class declares `attributes` (the public kwargs) and `replace`/`copy`/`to_dict` iterate it via `kwargs.setdefault(x, getattr(self, x))` — `Request.attributes` (`scrapy/http/request/__init__.py:90-100`), `replace` (`scrapy/http/request/__init__.py:336-344`), `to_dict` (`scrapy/http/request/__init__.py:384-410`); `Response.attributes`/`replace` (`scrapy/http/response/__init__.py:47-53,180-188`). Subclasses extend the tuple (`JsonRequest`: `(*Request.attributes, "dumps_kwargs")`, `scrapy/http/request/json_request.py:25`; `TextResponse`: `(*Response.attributes, "encoding")`, `scrapy/http/response/text.py:45`).
- **URL invariant: scheme required + URL canonicalized.** `_set_url` runs `safe_url_string` (unless `meta["verbatim_url"]`) and raises "Missing scheme in request url" unless the URL has `://` or is `about:`/`data:` (`scrapy/http/request/__init__.py:255-272`).
- **callback/errback validated at construction; `NO_CALLBACK` sentinel** marks requests with no spider callback and raises if ever invoked (`scrapy/http/request/__init__.py:60-81`; type/callable checks `scrapy/http/request/__init__.py:158-163`). `Request.method` is upper-cased (`scrapy/http/request/__init__.py:140`).
- **`Response.meta`/`cb_kwargs` are not owned — they proxy the bound request** and raise `AttributeError` when the response is untied (`scrapy/http/response/__init__.py:93-110`).
- **`Headers` is a multi-valued caseless bytes dict**: values are stored as `list[bytes]`, `__getitem__`/`get` return the last value, `getlist` returns all; keys normalized via `.title` (`scrapy/http/headers.py:43-104`).
- **`TextResponse` encoding resolution order** (declared → BOM → header → body-declared → chardet-style inference, default ascii) is memoized via `memoizemethod_noargs`, and `selector`/`text`/`json` results are cached in slots (`scrapy/http/response/text.py:43,74-145,86-90,146-153`).
- **`FormRequest` and the whole `scrapy.http.request.form` module are deprecated** (module-level `warn(...)` recommending `form2request`), and `scrapy.http` re-exports it wrapped in `create_deprecated_class` (`scrapy/http/request/form.py:35-40`; `scrapy/http/__init__.py:25-32`).
- **Subclass content-type contracts:** `JsonRequest` defaults `Content-Type: application/json` + serializes `data` with `sort_keys=True` (`scrapy/http/request/json_request.py:30-51`); `XmlRpcRequest` forces POST + `dont_filter=True` + `Content-Type: text/xml` and hardens parsing with `defusedxml` (`scrapy/http/request/rpc.py:18,32-42`); the `*Response` MIME subclasses are empty `__slots__`-only markers whose behavior is purely the dispatched type (`scrapy/http/response/html.py:11-12`, `scrapy/http/response/json.py:11-12`, `scrapy/http/response/xml.py:11-12`).
- **Twisted async is the framework substrate** (`Twisted>=21.7.0`, `pyproject.toml:9-10`); within this leaf package Twisted appears only as the `Failure` errback type (`scrapy/http/request/__init__.py:35`) — the model itself is synchronous plain-Python value objects.
<!-- DEEPINIT:END -->
