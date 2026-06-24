<!-- DEEPINIT:START -->
# Component: pdata

> Provenance: stage=EXTRACT (blind, code-only) · component=pdata · path=pdata/ · derived from source + go.mod manifests only (prose docs removed per firewall) · date=2026-06-13

## Role

- The canonical data-model layer for all collector pipeline signals: it "provides the data model definitions for all supported pipeline data" (pdata/doc.go:6). It defines the in-memory representations of traces, metrics, logs and profiles (the subpackages `ptrace`, `pmetric`, `plog`, `pprofile` plus the shared `pcommon`) together with their (un)marshalers — declared stable for traces/metrics/logs (pdata/metadata.yaml:11).

## Dependencies (edges)

- **→ featuregate** (the ONLY production cross-component edge): imports `go.opentelemetry.io/collector/featuregate` to register the `pdata.useProtoPooling` gate (pdata/internal/metadata/generated_feature_gates.go:6, registered at:9), wired in the manifest via a local `replace... =>../featuregate` (pdata/go.mod:36).
- **→ client** (edge only from the `xpdata` sub-module, NOT the root module): `xpdata/request` imports `go.opentelemetry.io/collector/client` to encode/decode request context (pdata/xpdata/request/context.go:11), required by the nested module (pdata/xpdata/go.mod:8) with `replace =>../../client` (pdata/xpdata/go.mod, replace block).
- **→ internal/testutil** (test-only edge, not a runtime dependency): required + replaced to `../internal/testutil` (pdata/go.mod:9, pdata/go.mod:37).
- No imports of receiver / processor / exporter / connector / service / otelcol / consumer / component were found in any production source under pdata/ (verified by import scan over `*.go` excluding `_test.go`; only `client`, `featuregate`, `internal/testutil` appear). pdata is a leaf/foundation layer — it is depended upon, it does not depend on pipeline components (pdata/go.mod:5-16).

## Data

- Owns no external persistence / database. The only "stores" are in-memory: the underlying OTLP proto structs are the storage representation, hand-written varint codecs marshal/unmarshal them (pdata/internal/proto/marshal.go:7, pdata/internal/proto/unmarshal.go, pdata/internal/proto/size.go).
- Optional `sync.Pool` memory pools for proto value structs, gated by the `pdata.useProtoPooling` alpha feature gate (pool definitions at pdata/internal/generated_proto_anyvalue.go:120; gate-checked allocation at pdata/internal/wrapper_value.go:31).
- Persisted/serialized forms it produces: protobuf bytes via `ProtoMarshaler`/`ProtoUnmarshaler` (pdata/plog/pb.go:8, pdata/plog/pb.go:35) and JSON via the in-house streaming codec `internal/json` (pdata/plog/json.go:9, pdata/internal/json/stream.go).

## Boundary rules

- **Mutability / shared-ownership invariant**: every public data wrapper carries a `*State`; mutating methods call `AssertMutable`, which panics with "invalid access to shared data" if the data is read-only (pdata/internal/state.go:37, enforced at e.g. pdata/pcommon/map.go:40). `MarkReadOnly` flips the bit so shared/fanned-out data cannot be modified downstream (pdata/plog/logs.go:7, pdata/internal/state.go:29).
- **Reference counting**: `State` holds an atomic ref-count (`Ref`/`Unref`); `Unref` returning true (count==0) signals the data may be released, and a negative count panics "Cannot unref freed data" (pdata/internal/state.go:53-69) — the contract behind pipeline-owned pooling.
- **internal encapsulation boundary**: the raw OTLP structs, wrappers and codecs live under `pdata/internal` (not importable outside the module); public packages expose them only through opaque value types (pdata/pcommon/value.go:144 `getOrig` returns `*internal.AnyValue`; wrapper accessors at pdata/internal/wrapper_value.go:13-22).
- **Module-nesting boundary**: pdata is split into independently-versioned Go modules — root `pdata`, plus `pprofile`, `testdata`, `xpdata` each with their own go.mod and `replace =>..` back-edges (pdata/pprofile/go.mod:1, pdata/xpdata/go.mod:1, pdata/testdata/go.mod). Experimental surface (request-context, entity, pref) is isolated in `xpdata` (pdata/xpdata/xpdata.go).

## Key facts

- **Value model is a typed tagged-union over OTLP `AnyValue`**: `ValueType` has 8 variants (Empty/Str/Int/Double/Bool/Map/Slice/Bytes) and `Type` switches on the proto oneof (pdata/pcommon/value.go:18-28, pdata/pcommon/value.go:200). `Value` is "intended to be passed by value since internally it is just a pointer" (pdata/pcommon/value.go:54-58).
- **Generated, not hand-written**: the bulk of the model is machine-generated via `mdatagen` (`//go:generate mdatagen metadata.yaml`, pdata/doc.go:4); hundreds of `generated_proto_*.go` / `generated_wrapper_*.go` / `generated_enum_*.go` files (pdata/internal/). Edits go in metadata/templates, not the generated files.
- **Hand-rolled proto + JSON codecs, not protobuf-go reflection**: custom varint encode (pdata/internal/proto/marshal.go:7) and a custom JSON iterator/stream (pdata/internal/json/iterator.go, pdata/internal/json/stream.go) — performance-driven choice; `json-iterator/go` and `google.golang.org/protobuf` are deps (pdata/go.mod:6, pdata/go.mod:14).
- **Signal (un)marshaler interface contract** is uniform per signal: `Marshaler`/`Unmarshaler`/`Sizer`/`MarshalSizer` (pdata/plog/encoding.go:6-30) with concrete proto + JSON impls (pdata/plog/pb.go, pdata/plog/json.go) — mirrored in ptrace/pmetric/pprofile (pdata/ptrace/encoding.go, pdata/pmetric/encoding.go, pdata/pprofile/encoding.go).
- **OTLP gRPC service request/response types** are vendored into pdata's `*otlp` subpackages (e.g. `plog/plogotlp`), which depend on `google.golang.org/grpc` (pdata/plog/plogotlp/grpc.go) so signals can be sent over OTLP without an external proto dependency (grpc is a root dep, pdata/go.mod:13).
- **Profiles dictionary indirection**: pprofile resolves `string_value_ref`/`key_ref` indices to real strings after unmarshal so the API works transparently with referenced strings (pdata/pprofile/dictionary_helpers.go:16-19).
<!-- DEEPINIT:END -->
