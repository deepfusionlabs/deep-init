<!-- DEEPINIT:HUMAN-AUTHORED — not a DeepInit-managed region -->
# DeepInit in the Wild — (recall / discovery)

Two record shapes:

- **Shape A — a real finding.** A grounded, verified defect (family, `file:line`, the cited
 rule/contradiction) on a pinned `repo@SHA`. Published **only** when airtight, after the
 moonshot gate ladder. None yet — by design, the bar is high.
- **Shape B — precision / silence.** "We ran DeepInit on X and it stayed silent / suppressed the
 by-design near-candidates — here's the precision story." The *expected* outcome on a clean repo,
 and itself trust-first content.

Recall (the metamorphic bugfix-pair number, currently **14/22**, metamorphic-FP **0/22**) lives in
the test-plan's external oracle (§26), not here — that is the rigorous recall measurement; these
records are field case-study material.

## Records

**Fifteen** real-repo deterministic-detector sweeps over **~1.12M LOC** across **Crystal / Python /
TypeScript / Go / Rust / Java / Ruby-Rails / PHP / Elixir / C# / Kotlin / C / C++ / OCaml / Swift**
(single-component, multi-component, a famous L-tier monorepo, mature M-tier servers,
multi-crate/multi-module workspaces, and several component-scoped L-tier giants). They demonstrate
**both halves of the thesis at once**: on clean code the suite stays silent (kemal, pyccel, ripgrep,
Poco: 0 fires, mechanism-named suppressions, 0 false defects — "comprehension, not keyword-matching");
on real famous repos it **fired real, structurally-verified candidates** (excalidraw IF-8/IF-6;
Signal-Server/PHP/Kotlin/C#/nginx IF-8; Elixir/Poco IF-6; Go/PHP/C#/Ruby/nginx/dune/swift-nio IF-3a)
— and precision-first held every time (every fire recorded **gated**, never published). The M4c
batch (**C / C++ / OCaml / Swift**) added the structurally-novel stacks: a fifth IF-8 regime
(**permitted + textual**, C/nginx), a third **hard-ban enforcement mechanism** (the build-manifest
DAG — OCaml/dune `(libraries)`, Swift/SPM `.target`), and the sharpest cross-family contrast —
**IF-7c reactivating on C++** (79 real empty catches vs C's zero, all suppressed by the
cross-component moat).

The **cross-language structural contrast** is the corpus's sharpest signal — the *same* deterministic
detectors comprehend each language's rules rather than keyword-matching. The full IF-family × language
matrix lives in **`docs/reference/deepinit-language-structural-rules.md`**; the IF-8 spine (five regimes):

| IF-8 regime | Languages (field witness) | Outcome |
|-------------|---------------------------|---------|
| **Hard ban** (compile/build error) — 3 enforcement mechanisms: compiler import-check · module/assembly system · **build-manifest DAG** | Go packages · Rust crates · C# assemblies · Java/Kotlin Maven/Gradle *modules* · **OCaml** (dune `(libraries)` manifest) · **Swift** (SPM `.target` manifest) | **0 cycles** — DAG verified by a real Tarjan SCC (OCaml + Kahn topo-sort); artifacts + maintainer-flagged near-misses suppressed |
| **Partial ban** (compile-time only) | **Elixir** (compiler deadlocks on a compile-time cycle; runtime calls free) | runtime cycle **FIRES** (`channel↔socket`); compile-time graph = enforced DAG |
| **Permitted + explicit imports** | **Java** (33-pkg SCC) · **PHP** (31-component SCC) · **Kotlin** (14-pkg SCC) · **C# namespaces** (21+12-ns SCC) · **TypeScript** | **FIRES** — a real, groundable SCC |
| **Permitted + textual** (M4c — no module system; `#include` + include guards, no compiler/linker ban) — **discipline-dependent** | **C** (nginx — FIRES) · **C++** (Poco — disciplined-acyclic) | **C/nginx FIRES** `{core,event,os}` (umbrella header); **C++/Poco is a clean DAG** — same regime, opposite outcome (permission ≠ presence) |
| **Permitted + hidden** (autoload) | **Ruby** (Rails/Zeitwerk) | **reduced visibility** — explicit graph is a DAG; the real app cycle is below the substrate, not fabricated (honest recall caveat) |

Every fire was **independently re-computed by the main loop** (a second Tarjan over its own grep'd
edges, converging with the agent on the exact minimal witnesses — the cross-validation that also
caught a Windows-path false-negative in the Ruby IF-7c scan).

> **Gate discipline.** A Shape-A candidate is recorded only as *structurally verified* — the
> not-already-known / intent / severity / adversarial-refutation / operator-sign-off gates are **not**
> run, and **nothing is published or filed** (the operator's hard moonshot gate + the BLAST-RADIUS
> rule). A famous repo also carries the training-contamination caveat (the structural facts here rest
> on the live code, re-read at the pinned SHA).

- **`kemalcr-kemal-crystal-sweep.json`** (Crystal, single-component, `@b73de3d8`) — IF-6 / IF-7c /
 IF-8 / IF-10 over kemal's real Crystal source: **0 fires**, ~4 named suppressions (re-raise vs
 swallow; runtime-call vs const-fold; different-named-by-design vs same-name-divergent;
 single-component → IF-8/IF-3a N/A). Exercises the suite on an **off-mainstream** language (the
 moat — near-zero const-fold/dead-code tooling exists for Crystal).
- **`pyccel-pyccel-crossmodule-sweep.json`** (Python, **multi-component** ~59k LOC, 11 modules,
 `@b559732`) — the **cross-module** families kemal couldn't reach: IF-8 (clean acyclic graph,
 module-load-verified), IF-6 cross-module (polymorphic class-attribute overrides ≠ a divergent
 set), IF-10 cross-module (local-not-imported DEBUG flags), IF-7c (~19 swallows, each a deliberate
 fallback / `errors.report(fatal)` re-raise / `sys.exit` / expected-condition). **0 fires**, ~27
 named suppressions.

- **`excalidraw-excalidraw-typescript-sweep.json`** (TypeScript, **famous L-tier** monorepo ~135k
 LOC / 6 packages, `@0cf56b1`) — the **first sweep that FIRED**: two structurally-verified Shape-A
 candidates (re-read off the agent by the main loop) — a real **element↔utils cross-package runtime
 import cycle** (IF-8) and a real same-named-conflicting-membership **`Ellipse<Point>` divergence**
 across math/utils (IF-6) — plus 2 borderline IF-7c empty-catch fires (graceful-default fallbacks,
 likely-suppress) and IF-10 correctly silent (the one near-candidate is runtime feature-detection).
 **Recorded gated** — not confirmed bugs, not filed (see the gate discipline above).
- **`caddyserver-caddy-go-sweep.json`** (Go, **M-tier** ~71.5k LOC / 318 files / 6 component buckets,
 `@fcba554d`) — the **first Go-stack** datapoint: IF-8 / IF-6 / IF-10 / IF-7c / IF-3a. **1 LOW fire**
 (an IF-3a coupling — `cmd/main.go` re-assigns the root package's exported mutable globals
 `caddy.DefaultStorage` / `caddy.ConfigAutosavePath` cross-component with no setter; a minor
 code-smell, recorded **not filed**) + **38 named suppressions** / **0 false defects**. Decisive
 Go-specific comprehension: **Go forbids package import cycles at compile time**, verified by building
 the real **46-package / 195-edge** import graph and running Tarjan SCC → **0 cycles** (proven DAG),
 so IF-8 correctly **suppresses** the spurious size-5 SCC that the lossy 6-bucket component graph
 produces (a granularity artifact a naive component-level detector would over-fire on). CI-enforced
 `errcheck` collapses IF-7c to documented `_ =` / `//nolint` ignores; the registry idiom collapses
 IF-3a's surface to two exported globals (the lone fire).
- **`burntsushi-ripgrep-rust-sweep.json`** (Rust, **M-tier** multi-crate ~37.8k LOC / 100 files / 10
 crates, `@82313cf9`) — the **first Rust** datapoint, a **clean Shape-B**: **0 fires / 33 named
 suppressions / 0 false defects** (IF-8 5 / IF-6 6 / IF-10 7 / IF-7c 8 / IF-3a 7). Rust comprehension:
 **Cargo forbids cross-crate dependency cycles** (compile error) — IF-8 built the real 9-member
 cross-crate graph (incl. the `[dev-dependencies]` loophole Cargo permits, checked + empty) → strict
 DAG, so a cross-component cycle is structurally impossible (Rust's intra-crate module cycles are
 scoped out); the `Result` / `?` no-exceptions model reshapes IF-7c (`let _ =` / `.ok` discards,
 all deliberate); `cfg!` / `#[cfg]` feature gates are correctly excluded from IF-10's literal-`const`
 slice; and 3 coincidental cross-crate `ErrorKind` homonyms (sharing the `Regex` variant) are
 suppressed as independent taxonomies with no behavioral entailment.
- **`signalapp-Signal-Server-java-sweep.json`** (Java, **component-scoped L-tier** Maven service,
 `@adb5b6a4`) — the **first Java** datapoint and the corpus's cleanest **language contrast**: the
 service module's package graph (790 main files / ~71.4k LOC) **FIRED IF-8** on a genuine
 **33-package strongly-connected import cycle** (a "big ball of mud" core; 38 minimal 2-node
 mutual-import pairs; all four Core packages controllers/storage/auth/identity inside it; closed in
 part by a layering inversion — a request DTO imports a controller). This fire is **real, not an
 artifact**: unlike Go/Rust, **javac imposes no package-cycle ban** (Maven bans only cross-*module*
 cycles; this sweep scoped within the service module where package cycles are legal). The
 **headline was independently re-computed by the main loop** (a second Tarjan SCC over the grep'd
 import edges — same 38 pairs). The other four families over the 6-package core (~35k LOC) stayed
 silent: **1 genuine fire (IF-8, GATED) + 26 named suppressions / 0 false defects**. Distinctive Java
 findings: IF-10's substrate is idiomatically absent (no truthiness + Dropwizard-injected config →
 zero `static final boolean`); IF-7c needs an **`InterruptedException` carve-out** (`Util.sleep`
 passes the mechanical §23 letter but is precision-suppressed as a cancellation signal); IF-3a's
 permissive mutable-static shape is foreclosed by Dropwizard DI + strict layering. Recorded **gated**.
- **`discourse-discourse-ruby-sweep.json`** (Ruby on Rails, **component-scoped L-tier** app,
 `@420bced6`) — the **first Ruby/Rails** datapoint and the **first dynamic-autoload stack**: over the
 app core (686 files / ~91.8k LOC) + lib's `require_relative` graph, **IF-3a FIRED** on a real
 cross-directory coupling — the Redis key string `"discourse_id_challenge_token"` is **written** by a
 service (`challenge_flow.rb:41` setex) and **read** by a controller (`metadata_controller.rb:33`
 get), coupled only by a bare duplicated magic-string with no shared constant (LOW–MEDIUM, GATED,
 parallel to caddy's lone IF-3a fire). **1 genuine fire (IF-3a, GATED) + 23 named suppressions / 0
 false defects.** The signature Ruby finding is the **autoload-visibility limitation**: Zeitwerk
 resolves app/ dependencies by constant reference, not import statement, so IF-8 (the real
 `Post↔Topic↔User` model cycle) and IF-7c (the cross-component moat) have structurally reduced
 visibility — the suite **declines to fabricate fires from edges it cannot ground** (an honest recall
 caveat, never an FP — the strongest precision-discipline demonstration in the corpus). Plus: Rails
 MVC concentrates value-sets in the model layer (all 24 enums in app/models → cross-component IF-6
 thin); config-as-runtime-state starves IF-10 (0 boolean-literal consts); and **0 bare untyped
 `rescue`** in the entire app core (all 42 empty/comment-only rescues are typed expected-condition
 value-fallbacks).
- **`laravel-framework-php-sweep.json`** (PHP, `@7c851385`, MIT) — the **first PHP** datapoint and the
 cleanest **permitted + VISIBLE** IF-8 contrast: no cycle ban (like Java/Ruby) but explicit `use`
 imports (unlike Ruby's autoload). **IF-8 FIRED** on a **31-component SCC** across the Illuminate
 components (37 mutual-`use` pairs; robustness-tested — survives removing Contracts+Support at 23
 nodes; main-loop double-verified) — striking because the Illuminate components ship as *separate
 composer packages* yet are cyclically entangled. **IF-3a FIRED** on `Worker::$pausable/$restartable`
 (mutable `public static` flags cross-written by Foundation+Queue). 2 GATED fires + 31 named
 suppressions / 0 false defects.
- **`phoenix-elixir-sweep.json`** (Elixir, `@cd55c239`, MIT) — the **first Elixir/BEAM** datapoint and
 the **missing MIDDLE** of the IF-8 spectrum: a **partial ban** (the compiler deadlocks on a
 compile-time cycle → compile-time DAG enforced; runtime-call cycles permitted → `channel↔socket`
 runtime cycle FIRED). Also **IF-6 FIRED** on `@invalid_local_url_chars` (an open-redirect blocklist
 stricter in controller than endpoint — a security-relevant divergence) and **IF-3a FIRED ×2** (a
 Phoenix.Config ETS table + an Endpoint persistent_term read directly across components). 4 GATED
 fires + 52 named suppressions / 0 false defects.
- **`jellyfin-csharp-sweep.json`** (C#/.NET, `@dd42a121`, GPL-2.0) — the **first C#** datapoint and the
 **HYBRID**: the same language bans cross-PROJECT cycles at build (24-project DAG, like Go/Rust) but
 permits cross-NAMESPACE cycles (like Java) → **IF-8 FIRED** two namespace SCCs (a **21-ns** cycle in
 MediaBrowser.Controller [High] + a **12-ns** cycle in MediaBrowser.Model [Medium]; both
 main-loop-verified). **IF-3a FIRED** on the legacy BaseItem static service-locator. IF-10's **484**
 const near-candidates all suppressed (C# forbids non-bool truthiness). 3 GATED fires + 19 named
 suppressions / 0 false defects.
- **`okhttp-kotlin-sweep.json`** (Kotlin, `@eef98589`, Apache-2.0) — the **first Kotlin** datapoint;
 Kotlin sits in the Java structural class (no package-cycle ban) → **IF-8 FIRED** on a **14-package
 SCC** anchored on the public okhttp3 package (public↔internal, a known OkHttp pattern;
 main-loop-verified bidirectional 2-cycles). IF-6/IF-10/IF-7c/IF-3a a clean Shape-B. 1 GATED fire +
 45 named suppressions / 0 false defects.
- **`nginx-c-sweep.json`** (C, `@da80db97`, BSD-2-Clause) — the **first pure-C** datapoint (M4c) and
 the **highest-novelty IF-8 substrate**: the preprocessor `#include` model with **no module system**.
 It completes the IF-8 spectrum with a fifth, most-permissive regime — **permitted + textual** (no
 compiler/linker cycle ban; include guards *enable* cyclic include graphs). **IF-8 FIRED** the real
 **`{core, event, os}` 3-component cycle**, present identically in the full (`.c+.h`) and header-only
 (`.h`) graphs — interface-level co-recursion closed through the umbrella god-header `ngx_core.h`
 (which pulls sibling event/os headers while being `#include`d by ~every file); **main-loop
 double-verified** (a second Tarjan over the orchestrator's own edges converged on the same SCC), with
 `http`/`mail`/`stream`/`misc` correctly suppressed as acyclic leaves and the 13 `os/unix`↔`os/win32`
 duplicate-basename headers resolved to one `os` component (the caddy-lesson precision guard).
 **IF-3a FIRED** on the **accept-mutex protocol globals** (`ngx_use_accept_mutex`/`ngx_accept_mutex_held`
 — bare `=0/=1` assignment, no accessor, cross-written by 3 subsystems event/core/os, read in 5;
 main-loop-verified), the **purest canonical IF-3a shape** in the corpus on its richest substrate (a
 flat global namespace) — the borderline `ngx_cycle` lifecycle-baton and the atomic-mediated
 `ngx_stat_*` counters correctly suppressed in favor of it. **2 GATED fires + 40 named suppressions /
 0 false defects** against a ~342-candidate naive surface. Two more corpus firsts: **IF-10** muted by
 the novel **config-as-preprocessor-flag** mechanism (`#if (MACRO)` where MACRO is `./configure`-driven)
 + the `#if 0` deliberate-disable idiom; **IF-7c** is **applicable=false** — pure C has no `catch`
 construct for the empty-handler predicate to match (the first substrate-absent verdict).
- **`poco-cpp-sweep.json`** (C++, `@501ddd66`, BSL-1.0) — the **first C++** datapoint (M4c, ) and
 the deliberate **C sibling**: same permitted+textual `#include` IF-8 regime, but POCO's strict
 layering yields a **clean DAG** (Foundation the universal out-degree-0 sink; header-only graph ==
 full graph) where nginx FIRED — proving the regime is about *permission*, not *presence*. **Headline:
 IF-7c REACTIVATES** vs pure C — 79 real empty `catch` handlers exist (C had zero), all suppressed by
 the cross-component-consumed moat → **0 fires / 0 FP** (the strongest IF-7c precision result), the
 biggest carve-out the C++-mandatory destructor-must-not-throw idiom. **IF-6 FIRED** on the syslog
 `Facility` enum (Foundation 20 vs Net 24 members — the 3rd IF-6 fire in the corpus). 1 GATED fire +
 101 named suppressions / 0 false defects.
- **`dune-ocaml-sweep.json`** (OCaml, `@bef216d3`, MIT) — the **first OCaml / functional-ML** datapoint
 (M4c, ): **IF-8 HARD-BAN via the build manifest** (dune's `(libraries)` stanzas declare the
 inter-lib graph; dune rejects a cycle → a 35-node / 141-edge DAG, double-verified by Tarjan + a Kahn
 topo-sort; the maintainer-flagged `dune_lang→dune_engine` near-miss correctly suppressed). **IF-3a
 FIRED** on `Dune_engine.Clflags` (raw `ref` cells exposed in the `.mli`, read across ≥4 libs) —
 **muted-by-purity but one mechanism-distinct escape**, the opposite end of the IF-3a spectrum from
 C's richest substrate. 1 GATED fire + 42 named suppressions / 0 false defects.
- **`swift-nio-swift-sweep.json`** (Swift, `@3263350c`, Apache-2.0) — the **first Swift** datapoint
 (M4c, ): **IF-8 HARD-BAN via the SPM target manifest** (an 8-module DAG agreeing with
 `.target(dependencies:)`), with two named Swift-specific over-fire traps — an **ARC retain-cycle is a
 memory concept, not a module-graph edge**, and 94 `@testable import` test-edges are out of scope.
 **IF-3a FIRED** on the `SWIFTNIO_STRICT` env-var magic-string (NIOPosix + NIOEmbedded, divergent
 parse — the same shape as Ruby's Redis-key). 1 GATED fire + 43 named suppressions / 0 false defects.

**No cost ledger** is recorded for any sweep: a direct detector sweep is not a representative full
Detect→Emit run, so it would mis-state DeepInit's run cost ( needs a real full-pipeline run — see
`validation/cost/`).
