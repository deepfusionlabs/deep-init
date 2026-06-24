<!--
 DeepInit provenance (R3)
 stage: EMIT (deep component doc)
 component: websocket
 run_id: run-2026-06-13-kemal-e2e
 inputs: extraction(websocket) · src/kemal/{websocket_handler,websocket,event_stream}.cr @ b73de3d8e6de
 date: 2026-06-13
 repo_sha: b73de3d8e6de97541866b6ecdc8c6ee1ef3eb747
-->
# websocket

**Role.** Real-time transports: the `WebSocketHandler` middleware (with Origin allow-list enforcement), the `WebSocket` route wrapper, and Server-Sent Events (`EventStream`).

**Paths.** `src/kemal/websocket_handler.cr` · `src/kemal/websocket.cr` · `src/kemal/event_stream.cr`

## WebSocketHandler & the Origin boundary
- `WebSocketHandler` (`websocket_handler.cr:5`, `INSTANCE` singleton) only engages when `context.ws_route_found?` AND the request is a genuine upgrade (`Upgrade: websocket` + `Connection: Upgrade`, case-insensitive, `websocket_handler.cr:38-43`); otherwise it `call_next`s. — `src/kemal/websocket_handler.cr:5`
- **BR-websocket:001 — Origin allow-list (security-relevant boundary).** When `Kemal.config.websocket_allowed_origins` is non-empty, a WebSocket upgrade is REJECTED (403 Forbidden) unless the request Origin (normalized to `scheme://host[:port]`, default-port-stripped, lowercased; literal `'null'` supported) matches an entry; an EMPTY allow-list disables the check (allow-all). This is the cross-site-WebSocket-hijacking boundary. — `src/kemal/websocket_handler.cr:45`
- WS routes are stored in a `Radix::Tree(WebSocket)` under `'/ws{path}'`. NOTE the path-key asymmetry: `add_route` builds the key via `radix_path('ws', path)` = `'/' + 'ws' + path` (`websocket_handler.cr:30,34-36`) while `lookup_ws_route` uses the literal `'"/ws" + path'` (`websocket_handler.cr:22`) — both yield `'/ws{path}'`, consistent but expressed two different ways. — `src/kemal/websocket_handler.cr:22`

## WebSocket route wrapper
- `WebSocket` (`websocket.cr`) subclasses `HTTP::WebSocketHandler` and just stores `path` + the user proc; `call` delegates to `super` (the stdlib upgrade handshake). — `src/kemal/websocket.cr:4`

## EventStream (Server-Sent Events)
- `EventStream` (`event_stream.cr`) implements SSE: `setup_headers` sets `Content-Type text/event-stream`, `Cache-Control no-cache`, `X-Accel-Buffering no`, and `Connection keep-alive` unless already set (`event_stream.cr:45-52`); `send` splits multi-line data into separate `data:` lines and flushes (`event_stream.cr:18-28`); `comment` sends a keep-alive comment line. `EventStream.serve` is the entry used by the `sse` DSL. — `src/kemal/event_stream.cr:45`

## Cross-component edges
- websocket ← core: `config.setup` appends `WebSocketHandler::INSTANCE` as the penultimate terminal link (before `RouteHandler::INSTANCE`).
- websocket ← core DSL: `sse` routes (`dsl.cr:63-68`) wrap `EventStream.serve` as GET routes — SSE reuses `RouteHandler`, not a separate transport at the routing layer.
- websocket → ext: reads `context.ws_route_found?` (bolted on in `ext/context.cr`).
