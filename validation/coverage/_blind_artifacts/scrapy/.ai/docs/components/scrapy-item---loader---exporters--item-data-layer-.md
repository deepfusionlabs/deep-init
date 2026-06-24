# Component: scrapy item + loader + exporters (item data layer)

Blind re-derivation from source. Files: `scrapy/item.py`, `scrapy/loader/__init__.py`, `scrapy/exporters.py`.

## Role

The structured-data layer of Scrapy: it defines the scraped-record model (`Item`/`Field` with a fields-declaring metaclass), the user-facing populator (`ItemLoader`) that fills items via field processors from selectors/responses, and the family of exporters that serialize items to JSON/JSONLines/XML/CSV/Pickle/Marshal/Pprint/Python formats (scrapy/item.py:57; scrapy/loader/__init__.py:20; scrapy/exporters.py:1).

## Dependencies (edges)

- → scrapy.utils (shared infrastructure): `Item` subclasses `object_ref` from `scrapy.utils.trackref` so item instances are tracked for memory-leak debugging (scrapy/item.py:15, scrapy/item.py:57).
- → scrapy.utils (shared infrastructure): exporters import `is_listlike`, `to_bytes`, `to_unicode` from `scrapy.utils.python` (scrapy/exporters.py:21).
- → scrapy.utils (shared infrastructure): JSON exporters use `ScrapyJSONEncoder` from `scrapy.utils.serialize` (scrapy/exporters.py:22; scrapy/utils/serialize.py:12).
- → scrapy.selector + scrapy.linkextractors (extraction): `ItemLoader` imports `Selector` and sets `default_selector_class = Selector`, building a selector from a `response` when none is passed (scrapy/loader/__init__.py:14, scrapy/loader/__init__.py:90, scrapy/loader/__init__.py:100-102).
- → scrapy.http (Request/Response model): `ItemLoader` type-hints `response: TextResponse` (TYPE_CHECKING import) and stores it in the loader context (scrapy/loader/__init__.py:17, scrapy/loader/__init__.py:96, scrapy/loader/__init__.py:105).
- → third-party `itemloaders` (manifest dep `itemloaders>=1.0.1`): `ItemLoader` subclasses `itemloaders.ItemLoader`, delegating processor/context machinery to the upstream library (scrapy/loader/__init__.py:11, scrapy/loader/__init__.py:20, scrapy/loader/__init__.py:106; pyproject.toml:15).
- → third-party `itemadapter` (manifest dep `itemadapter>=0.1.0`): exporters wrap every item in `ItemAdapter` and use `is_item` to treat dict/dataclass/attrs/pydantic items uniformly; field iteration goes through `field_names`/`get_field_meta` (scrapy/exporters.py:18, scrapy/exporters.py:80, scrapy/exporters.py:104-105, scrapy/exporters.py:286; pyproject.toml:14).
- Internal (within this component): `loader/__init__.py` imports `Item` from `scrapy.item` (default item class), and `exporters.py` imports `Field, Item` from `scrapy.item` (scrapy/loader/__init__.py:13, scrapy/loader/__init__.py:89; scrapy/exporters.py:20).

## Data

- Owns no external/persistent store. In-process per-item state only: `Item._values` is a plain dict holding populated field values, separate from the class-level `fields` declaration map (scrapy/item.py:86, scrapy/item.py:83).
- A process-global live-instance registry is read indirectly: subclassing `object_ref` registers each new `Item` in `trackref.live_refs` (a `defaultdict[type, WeakKeyDictionary]`) for leak inspection (scrapy/item.py:57; scrapy/utils/trackref.py:33, scrapy/utils/trackref.py:43-46).
- Exporters do not own files; each takes a caller-provided file-like sink (`file: BytesIO`) and writes serialized bytes/rows to it (scrapy/exporters.py:114, scrapy/exporters.py:116; scrapy/exporters.py:237).

## Boundary rules

- Field-name allowlist invariant: assigning an undeclared key raises `KeyError` — only names present in `fields` are accepted (scrapy/item.py:94-98).
- Attribute/item access separation: attribute get/set on declared fields is forbidden and redirected to `item[...]` syntax via `__getattr__`/`__setattr__`; only underscore-prefixed names may be set as attributes (scrapy/item.py:103-111).
- Adapter boundary: exporters never assume a concrete item type — all access is mediated by `ItemAdapter`/`is_item`, so the data layer stays type-agnostic across dict/dataclass/attrs/pydantic/`Item` (scrapy/exporters.py:80, scrapy/exporters.py:363).
- Serialization is pluggable per field: `serialize_field` reads a per-field `serializer` callable from field metadata, defaulting to identity (base), CSV multi-value join, or recursive Python serialization in subclasses (scrapy/exporters.py:62-66, scrapy/exporters.py:249-253, scrapy/exporters.py:350-356).

## Key facts

- `ItemMeta` metaclass collects every `Field`-typed class attribute into the `fields` dict at class creation and builds a shadow `_class` base (renamed `x_<ClassName>`), which is how field inheritance is composed (scrapy/item.py:28, scrapy/item.py:34-54).
- `Field` is just a `dict[str, Any]` subclass — a metadata bag (e.g. `serializer`, processors), not a typed descriptor (scrapy/item.py:24).
- `Item` is a `MutableMapping[str, Any]` (dict-like) but is NOT a dict; itemadapter supports it as one of several item types (scrapy/item.py:57, scrapy/item.py:60-64).
- `ItemLoader` is a thin Scrapy-specific subclass of upstream `itemloaders.ItemLoader`; Scrapy adds only the selector/response wiring (auto-build `Selector` from a response, default item class = `Item`) and defers all processor logic to the library (scrapy/loader/__init__.py:20, scrapy/loader/__init__.py:89-106).
- `BaseItemExporter` is an ABC; concrete exporters implement `export_item` and the lifecycle `start_exporting`/`finish_exporting`; `_get_serialized_fields` centralizes field selection honoring `fields_to_export` (str list or name→header Mapping) and `export_empty_fields` (scrapy/exporters.py:39, scrapy/exporters.py:58-60, scrapy/exporters.py:74-110).
- `JsonItemExporter` builds a single JSON array by manually emitting `[`, comma-separators, and `]` across `start/export/finish` so it can stream items without holding them all in memory (scrapy/exporters.py:152-164).
- `CsvItemExporter` wraps the binary sink in a `TextIOWrapper` with `newline=""` to avoid double line-endings on Windows, lazily writes the header row from declared field names, and `detach`es on finish to avoid closing the caller's file (scrapy/exporters.py:237-244, scrapy/exporters.py:272-273, scrapy/exporters.py:282-294).
- `PythonItemExporter` recursively serializes nested items to built-in Python types so any downstream codec (json/msgpack) can consume the result; it overrides `export_item` to RETURN a dict instead of writing (scrapy/exporters.py:335, scrapy/exporters.py:358-375).
- Public surface: `Item` and `Field` are re-exported at top level via `scrapy/__init__.py` (`from scrapy.item import Field, Item`); consumers include `scrapy.extensions.feedexport` (uses `BaseItemExporter`) and `scrapy.utils.misc` (scrapy/__init__.py:11; scrapy/exporters.py:27-36).
