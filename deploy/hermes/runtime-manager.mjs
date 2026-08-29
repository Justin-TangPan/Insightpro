import { randomBytes, timingSafeEqual } from "node:crypto"
import { spawn } from "node:child_process"
import { cpSync, existsSync, lstatSync, mkdirSync, openSync, readFileSync, readdirSync, renameSync, symlinkSync, unlinkSync, writeFileSync, chownSync, chmodSync } from "node:fs"
import http from "node:http"
import https from "node:https"
import net from "node:net"
import path from "node:path"

const root = process.env.INSIGHT_AGENT_DATA_ROOT || "/srv/insight-agent"
const spacesRoot = path.join(root, "spaces")
const tokensRoot = path.join(root, "dashboard-tokens")
const registryPath = path.join(root, "registry.json")
const templateRoot = "/template"
const workspaceRulesTemplate = "/opt/insight-agent/AGENTS.override.md"
const knowledgeRoot = "/knowledge/public"
const adminGid = 10002
const firstAdminUid = 11000
const firstUserUid = 20000
const firstPort = 12000
const maxActive = Number(process.env.OPENCODE_MAX_ACTIVE || 6)
const idleMs = Number(process.env.OPENCODE_IDLE_SECONDS || 1800) * 1000
const internalSecret = process.env.OPENCODE_GATEWAY_SECRET || ""
const providerUrl = new URL(process.env.HERMES_PROVIDER_BASE_URL || "http://127.0.0.1:9")
const providerKey = process.env.HERMES_PROVIDER_API_KEY || ""
const publicApi = process.env.INSIGHT_PUBLIC_API_URL || "http://host.docker.internal:8000/api"
const active = new Map()
const starting = new Map()

function providerApiPath(basePath, requestPath) {
  return `${basePath.replace(/\/$/, "")}${requestPath.replace(/^\/v1(?=\/|$)/, "")}`
}

// Private workspaces deny traversal to other users; this makes files created
// by an admin in the shared knowledge directory readable to team members.
process.umask(0o002)

async function refreshPublicKnowledge() {
  try {
    const routes = { homepage: "/homepage/modules", hotspots: "/github-trending?since=daily", solutions: "/solutions/aliyun" }
    const entries = await Promise.all(Object.entries(routes).map(async ([name, route]) => {
      const response = await fetch(publicApi + route, { signal: AbortSignal.timeout(15000) })
      if (!response.ok) throw new Error(`${route}: ${response.status}`)
      return [name, await response.json()]
    }))
    const destination = path.join(knowledgeRoot, "insight-public-data.json")
    writeFileSync(destination, JSON.stringify({ refreshedAt: new Date().toISOString(), ...Object.fromEntries(entries) }, null, 2), { mode: 0o644 })
    chownSync(destination, 0, adminGid)
    chmodSync(destination, 0o644)
  } catch (error) {
    console.error("Public knowledge refresh failed", error)
  }
}

mkdirSync(spacesRoot, { recursive: true, mode: 0o711 })
mkdirSync(tokensRoot, { recursive: true, mode: 0o700 })
mkdirSync(knowledgeRoot, { recursive: true, mode: 0o755 })
chmodSync(spacesRoot, 0o711)
chmodSync(tokensRoot, 0o700)
chmodSync(knowledgeRoot, 0o2775)
chownSync(knowledgeRoot, 0, adminGid)

let registry = existsSync(registryPath) ? JSON.parse(readFileSync(registryPath, "utf8")) : { users: {} }

function saveRegistry() {
  writeFileSync(registryPath, JSON.stringify(registry, null, 2), { mode: 0o600 })
}

function dashboardTokenFor(userId) {
  const tokenPath = path.join(tokensRoot, userId)
  if (existsSync(tokenPath)) return readFileSync(tokenPath, "utf8").trim()
  const token = randomBytes(32).toString("base64url")
  writeFileSync(tokenPath, token, { mode: 0o600 })
  return token
}

function safeEqual(left, right) {
  const a = Buffer.from(left || "")
  const b = Buffer.from(right || "")
  return a.length === b.length && a.length > 0 && timingSafeEqual(a, b)
}

function nextUid(role, records = Object.values(registry.users)) {
  const floor = role === "admin" ? firstAdminUid : firstUserUid
  const ceiling = role === "admin" ? firstUserUid : Infinity
  return Math.max(floor, ...records.filter(item => item.uid >= floor && item.uid < ceiling).map(item => item.uid + 1))
}

function identity(req) {
  if (!safeEqual(req.headers["x-insight-runtime-secret"], internalSecret)) return null
  const userId = String(req.headers["x-insight-user-id"] || "").toLowerCase()
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(userId)) return null
  return {
    userId,
    role: req.headers["x-insight-agent-role"] === "admin" ? "admin" : "user",
    authRole: req.headers["x-insight-auth-role"] === "admin" ? "admin" : "user",
    displayName: decodeURIComponent(String(req.headers["x-insight-display-name"] || "")).slice(0, 80),
    agentSessionId: String(req.headers["x-insight-agent-session-id"] || ""),
  }
}

function recordFor({ userId, role, displayName }) {
  let record = registry.users[userId]
  if (!record) {
    record = {
      uid: nextUid(role),
      port: Math.max(firstPort, ...Object.values(registry.users).map(item => item.port + 1)),
      role,
      displayName,
      createdAt: new Date().toISOString(),
      usage: { runtime_starts: 0, days: {} },
    }
    registry.users[userId] = record
  } else {
    if (record.role !== role || (role === "admin" && record.uid === adminGid)) record.uid = nextUid(role)
    record.role = role
    record.displayName = displayName || record.displayName
  }
  saveRegistry()
  return record
}

function recordUsage(userId, usage = {}) {
  const record = registry.users[userId]
  if (!record) return
  const day = new Date().toISOString().slice(0, 10)
  const state = record.usage || (record.usage = { runtime_starts: 0, days: {} })
  const item = state.days[day] || (state.days[day] = { requests: 0, input_tokens: 0, output_tokens: 0 })
  item.requests += 1; item.input_tokens += Number(usage.prompt_tokens || 0); item.output_tokens += Number(usage.completion_tokens || 0)
  saveRegistry()
}

function adoptLegacy(space, role) {
  if (role !== "admin" || existsSync(path.join(root, ".legacy-migrated"))) return
  for (const name of ["data", "cache", "state", "workspace"]) {
    const source = path.join(root, name)
    const destination = path.join(space, name)
    if (existsSync(source) && !existsSync(destination)) renameSync(source, destination)
  }
  writeFileSync(path.join(root, ".legacy-migrated"), new Date().toISOString(), { mode: 0o600 })
}

function ownTree(target, uid, gid, directoryMode = 0o2770) {
  chownSync(target, uid, gid)
  chmodSync(target, directoryMode)
  for (const entry of readdirSync(target, { withFileTypes: true })) {
    if (entry.isSymbolicLink()) continue
    const child = path.join(target, entry.name)
    if (entry.isDirectory()) ownTree(child, uid, gid, directoryMode)
    else {
      chownSync(child, uid, gid)
      chmodSync(child, 0o660)
    }
  }
}

function copyConfig(space, role, uid) {
  const hermesRoot = path.join(space, "hermes")
  mkdirSync(hermesRoot, { recursive: true, mode: 0o2770 })
  const config = `_config_version: 38
model:
  default: openpangu-2.0-flash
  provider: custom
  base_url: http://127.0.0.1:4199/v1
platform_toolsets:
  cli: [file]
agent:
  disabled_toolsets: [terminal, web, browser, cronjob, skills_hub, send_message]
`
  writeFileSync(path.join(hermesRoot, "config.yaml"), config, { mode: 0o640 })
  ownTree(hermesRoot, uid, adminGid)
}

function syncWorkspaceRules(workspace, uid) {
  const rules = readFileSync(workspaceRulesTemplate, "utf8")
  const destination = path.join(workspace, "AGENTS.override.md")
  if (!existsSync(destination) || readFileSync(destination, "utf8") !== rules) {
    writeFileSync(destination, rules, { mode: 0o640 })
  }
  chownSync(destination, uid, adminGid)
  chmodSync(destination, 0o640)
}

function ensureSpace(identityValue, record) {
  const space = path.join(spacesRoot, identityValue.userId)
  const ownershipMarker = path.join(space, ".ownership-role")
  const ownershipState = existsSync(ownershipMarker) ? readFileSync(ownershipMarker, "utf8") : ""
  mkdirSync(space, { recursive: true, mode: 0o2770 })
  adoptLegacy(space, identityValue.role)
  for (const name of ["hermes", "home"]) mkdirSync(path.join(space, name), { recursive: true, mode: 0o2770 })
  const workspace = path.join(space, "workspace")
  if (!existsSync(workspace)) cpSync(templateRoot, workspace, { recursive: true })
  if (!existsSync(path.join(workspace, "public-knowledge"))) symlinkSync(knowledgeRoot, path.join(workspace, "public-knowledge"), "dir")
  const desiredOwnership = `${identityValue.role}:${record.uid}`
  if (ownershipState !== desiredOwnership) {
    for (const name of ["hermes", "home", "workspace"]) ownTree(path.join(space, name), record.uid, adminGid)
    chownSync(space, record.uid, adminGid)
    chmodSync(space, 0o2770)
    writeFileSync(ownershipMarker, desiredOwnership, { mode: 0o660 })
    chownSync(ownershipMarker, record.uid, adminGid)
  }
  copyConfig(space, identityValue.role, record.uid)
  syncWorkspaceRules(workspace, record.uid)
  return { space, workspace }
}

async function syncBusinessContext(identityValue, workspace) {
  const sessionId = identityValue.agentSessionId
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(sessionId)) {
    try { unlinkSync(path.join(workspace, ".insight", "INSIGHT_CONTEXT.md")) } catch {}
    return
  }
  try {
    const response = await fetch(`${publicApi}/agent/internal/sessions/${sessionId}`, {
      headers: { "X-Insight-Runtime-Secret": internalSecret, "X-Insight-User-Id": identityValue.userId },
      signal: AbortSignal.timeout(10_000),
    })
    if (!response.ok) throw new Error(`context session: ${response.status}`)
    const session = await response.json()
    const context = session.context_snapshot
    const directory = path.join(workspace, ".insight")
    mkdirSync(directory, { recursive: true, mode: 0o770 })
    const contextPath = path.join(directory, "INSIGHT_CONTEXT.md")
    writeFileSync(contextPath, `# Current InsightPro Context\n\nSession: ${session.id}\n\n\`\`\`json\n${JSON.stringify(context, null, 2)}\n\`\`\`\n`, { mode: 0o640 })
    writeFileSync(path.join(directory, "INSIGHT_ACTION.json"), JSON.stringify({ session_id: session.id, action: "", payload: {} }, null, 2), { mode: 0o640 })
    ownTree(directory, registry.users[identityValue.userId].uid, adminGid)
    chownSync(contextPath, 0, registry.users[identityValue.userId].uid)
    chmodSync(contextPath, 0o640)
  } catch (error) {
    console.error("Business context sync failed", error)
  }
}

async function processHealthy(port) {
  try {
    const response = await fetch(`http://127.0.0.1:${port}/`, { signal: AbortSignal.timeout(500) })
    return response.ok
  } catch {
    return false
  }
}

function stopInstance(userId) {
  const instance = active.get(userId)
  if (!instance) return
  if (registry.users[userId]) {
    registry.users[userId].lastUsedAt = new Date(instance.lastUsed).toISOString()
    saveRegistry()
  }
  instance.child.kill("SIGTERM")
  active.delete(userId)
}

function diskBytes(target) {
  try {
    const stat = lstatSync(target)
    if (stat.isSymbolicLink()) return 0
    if (!stat.isDirectory()) return stat.size
    return readdirSync(target).reduce((total, name) => total + diskBytes(path.join(target, name)), 0)
  } catch { return 0 }
}

function spaceStatus(userId, record) {
  const workspace = path.join(spacesRoot, userId, "workspace")
  const instance = active.get(userId)
  return {
    user_id: userId,
    runtime_status: instance ? "running" : "stopped",
    workspace_status: existsSync(workspace) ? "ready" : "not_created",
    last_used_at: instance ? new Date(instance.lastUsed).toISOString() : record?.lastUsedAt || null,
    disk_bytes: existsSync(path.join(spacesRoot, userId)) ? diskBytes(path.join(spacesRoot, userId)) : 0,
  }
}

function managementRequest(req, res) {
  if (!safeEqual(req.headers["x-insight-runtime-secret"], internalSecret)) {
    res.writeHead(403); res.end("forbidden"); return true
  }
  const url = new URL(req.url, "http://runtime")
  const safePart = value => String(value || "").split("/").filter(part => /^[\w.\-\u4e00-\u9fff ]{1,120}$/.test(part)).join("/")
  const knowledgeFiles = (dir = knowledgeRoot, prefix = "") => readdirSync(dir, { withFileTypes: true }).flatMap(entry => {
    const relative = `${prefix}${entry.name}`
    if (entry.isDirectory()) return knowledgeFiles(path.join(dir, entry.name), `${relative}/`)
    if (!entry.isFile()) return []
    const stat = lstatSync(path.join(dir, entry.name))
    return [{ path: relative, size: stat.size, updated_at: stat.mtime.toISOString(), managed: relative === "insight-public-data.json" }]
  })
  if (url.pathname === "/_insight/knowledge/list" && req.method === "GET") {
    const query = String(url.searchParams.get("q") || "").toLowerCase()
    const files = knowledgeFiles().filter(item => !query || item.path.toLowerCase().includes(query))
    res.writeHead(200, { "Content-Type": "application/json", "Cache-Control": "no-store" }); res.end(JSON.stringify({ files })); return true
  }
  if (url.pathname === "/_insight/knowledge/upload" && req.method === "POST") {
    const filename = safePart(req.headers["x-insight-knowledge-name"])
    const category = safePart(url.searchParams.get("category"))
    if (!filename || filename === "insight-public-data.json") { res.writeHead(422); res.end("invalid file name"); return true }
    const destination = path.join(knowledgeRoot, category, filename)
    if (!destination.startsWith(`${knowledgeRoot}/`)) { res.writeHead(422); res.end("invalid path"); return true }
    mkdirSync(path.dirname(destination), { recursive: true, mode: 0o2775 })
    const chunks = []; let size = 0
    req.on("data", chunk => { size += chunk.length; if (size <= 10 * 1024 * 1024) chunks.push(chunk) })
    req.on("end", () => {
      if (size > 10 * 1024 * 1024) { res.writeHead(413); res.end("file too large"); return }
      writeFileSync(destination, Buffer.concat(chunks), { mode: 0o664 }); chownSync(destination, 0, adminGid); chmodSync(destination, 0o664)
      res.writeHead(201); res.end()
    }); return true
  }
  if (url.pathname === "/_insight/knowledge/delete" && req.method === "POST") {
    const relative = safePart(url.searchParams.get("path"))
    if (!relative || relative === "insight-public-data.json") { res.writeHead(422); res.end("protected file"); return true }
    const target = path.join(knowledgeRoot, relative)
    try { unlinkSync(target); res.writeHead(204); res.end() } catch { res.writeHead(404); res.end("not found") }
    return true
  }
  if (url.pathname === "/_insight/runtime/overview" && req.method === "GET") {
    const spaces = Object.entries(registry.users).map(([userId, record]) => spaceStatus(userId, record))
    const today = new Date().toISOString().slice(0, 10)
    const usage = Object.entries(registry.users).map(([user_id, record]) => ({ user_id, ...(record.usage || { runtime_starts: 0, days: {} }) }))
    const totals = usage.reduce((sum, item) => { const day = item.days[today] || {}; sum.requests += day.requests || 0; sum.input_tokens += day.input_tokens || 0; sum.output_tokens += day.output_tokens || 0; return sum }, { requests: 0, input_tokens: 0, output_tokens: 0 })
    res.writeHead(200, { "Content-Type": "application/json", "Cache-Control": "no-store" })
    res.end(JSON.stringify({ ai_space_users: spaces.length, active_runtimes: active.size, max_active_runtimes: maxActive, spaces, usage, today: { date: today, ...totals } }))
    return true
  }
  if (url.pathname === "/_insight/runtime/action" && req.method === "GET") {
    const userId = String(req.headers["x-insight-user-id"] || "").toLowerCase()
    const sessionId = String(url.searchParams.get("session_id") || "")
    if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(userId) || !/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(sessionId)) { res.writeHead(422); res.end("invalid session"); return true }
    try {
      const action = JSON.parse(readFileSync(path.join(spacesRoot, userId, "workspace", ".insight", "INSIGHT_ACTION.json"), "utf8"))
      if (action.session_id !== sessionId || !action.action || typeof action.payload !== "object") { res.writeHead(404); res.end("no action"); return true }
      res.writeHead(200, { "Content-Type": "application/json", "Cache-Control": "no-store" }); res.end(JSON.stringify(action)); return true
    } catch { res.writeHead(404); res.end("no action"); return true }
  }
  const userId = url.searchParams.get("user_id") || ""
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(userId)) {
    res.writeHead(422); res.end("invalid user_id"); return true
  }
  if (url.pathname === "/_insight/runtime/status" && req.method === "GET") {
    res.writeHead(200, { "Content-Type": "application/json", "Cache-Control": "no-store" })
    res.end(JSON.stringify(spaceStatus(userId, registry.users[userId])))
    return true
  }
  if (url.pathname === "/_insight/runtime/stop" && req.method === "POST") {
    stopInstance(userId)
    res.writeHead(204); res.end(); return true
  }
  if (url.pathname === "/_insight/runtime/start" && req.method === "POST") {
    const current = identity(req)
    if (!current || current.userId !== userId) { res.writeHead(403); res.end("forbidden"); return true }
    ensureInstance(current).then(() => {
      res.writeHead(200, { "Content-Type": "application/json", "Cache-Control": "no-store" })
      res.end(JSON.stringify(spaceStatus(userId, registry.users[userId])))
    }).catch(() => { res.writeHead(503); res.end("agent starting failed") })
    return true
  }
  res.writeHead(404); res.end("not found"); return true
}

function childEnvironment(space, workspace, dashboardToken, role, userId) {
  const env = { ...process.env }
  for (const name of Object.keys(env)) {
    if (/(SECRET|TOKEN|PASSWORD|API_KEY)$/i.test(name) || name.startsWith("OPENCODE_")) delete env[name]
  }
  return {
    ...env,
    HOME: path.join(space, "home"),
    HERMES_HOME: path.join(space, "hermes"),
    HERMES_WRITE_SAFE_ROOT: role === "admin" ? `${workspace}:${knowledgeRoot}` : workspace,
    HERMES_DASHBOARD_SESSION_TOKEN: dashboardToken,
    OPENAI_BASE_URL: "http://127.0.0.1:4199/v1",
    OPENAI_API_KEY: `runtime-proxy:${userId}`,
  }
}

async function ensureInstance(identityValue) {
  const existing = active.get(identityValue.userId)
  if (existing && !existing.child.killed && existing.role === identityValue.role) {
    existing.lastUsed = Date.now()
    if (existing.contextSessionId !== identityValue.agentSessionId) {
      await syncBusinessContext(identityValue, existing.workspace)
      existing.contextSessionId = identityValue.agentSessionId
    }
    return existing
  }
  if (existing) {
    stopInstance(identityValue.userId)
    await Promise.race([
      new Promise(resolve => existing.child.once("exit", resolve)),
      new Promise(resolve => setTimeout(resolve, 3000)),
    ])
    if (existing.child.exitCode === null) existing.child.kill("SIGKILL")
  }
  if (starting.has(identityValue.userId)) return starting.get(identityValue.userId)
  const promise = (async () => {
    if (active.size >= maxActive) {
      const oldest = [...active.entries()].sort(([, a], [, b]) => a.lastUsed - b.lastUsed)[0]
      if (oldest) stopInstance(oldest[0])
    }
    const record = recordFor(identityValue)
    record.usage = record.usage || { runtime_starts: 0, days: {} }
    record.usage.runtime_starts += 1
    record.lastUsedAt = new Date().toISOString()
    saveRegistry()
    const { space, workspace } = ensureSpace(identityValue, record)
    await syncBusinessContext(identityValue, workspace)
    const log = openSync(path.join(space, "runtime.log"), "a")
    const child = spawn("hermes", ["dashboard", "--host", "127.0.0.1", "--port", String(record.port), "--no-open", "--skip-build", "--isolated"], {
      cwd: workspace,
      uid: record.uid,
      gid: identityValue.role === "admin" ? adminGid : record.uid,
      env: childEnvironment(space, workspace, dashboardTokenFor(identityValue.userId), identityValue.role, identityValue.userId),
      stdio: ["ignore", log, log],
    })
    child.once("exit", () => active.delete(identityValue.userId))
    const instance = { child, port: record.port, workspace, role: identityValue.role, contextSessionId: identityValue.agentSessionId, lastUsed: Date.now() }
    active.set(identityValue.userId, instance)
    for (let attempt = 0; attempt < 300; attempt += 1) {
      if (await processHealthy(record.port)) return instance
      if (child.exitCode !== null) throw new Error(`Hermes process exited for ${identityValue.userId}`)
      await new Promise(resolve => setTimeout(resolve, 100))
    }
    stopInstance(identityValue.userId)
    throw new Error(`Hermes startup timeout for ${identityValue.userId}`)
  })().finally(() => starting.delete(identityValue.userId))
  starting.set(identityValue.userId, promise)
  return promise
}

function upstreamHeaders(req, port) {
  const headers = { ...req.headers, host: `127.0.0.1:${port}` }
  // Hermes binds per-user dashboards to loopback and rejects a proxied browser
  // WebSocket whose Origin still names the public gateway. The gateway has
  // already completed InsightPro SSO before this internal-only hop.
  if (headers.origin) headers.origin = `http://127.0.0.1:${port}`
  for (const name of Object.keys(headers)) if (name.startsWith("x-insight-")) delete headers[name]
  delete headers.cookie
  return headers
}

const server = http.createServer(async (req, res) => {
  if (req.url === "/healthz") return void res.end("healthy\n")
  if ((req.url || "").startsWith("/_insight/runtime/")) return void managementRequest(req, res)
  const current = identity(req)
  if (!current) {
    res.writeHead(401)
    return void res.end("unauthorized")
  }
  if (current.authRole !== "admin" && req.method !== "GET" && /^\/api\/(config|tools|profiles|ops)\b/.test(req.url || "")) {
    res.writeHead(403)
    return void res.end("AI space configuration requires administrator access")
  }
  if (req.url === "/__insight/context") {
    const record = recordFor(current)
    const { workspace } = ensureSpace(current, record)
    res.writeHead(200, { "Content-Type": "application/json", "Cache-Control": "no-store" })
    return void res.end(JSON.stringify({ workspace, role: current.role, authRole: current.authRole }))
  }
  try {
    const instance = await ensureInstance(current)
    const upstream = http.request({ hostname: "127.0.0.1", port: instance.port, path: req.url, method: req.method, headers: upstreamHeaders(req, instance.port) }, response => {
      res.writeHead(response.statusCode || 502, response.headers)
      response.pipe(res)
    })
    upstream.on("error", () => { if (!res.headersSent) res.writeHead(502); res.end("agent unavailable") })
    req.pipe(upstream)
  } catch (error) {
    console.error("Agent proxy failed", error)
    res.writeHead(503)
    res.end("agent starting failed")
  }
})

server.on("upgrade", async (req, socket, head) => {
  const current = identity(req)
  if (!current) return socket.destroy()
  try {
    const instance = await ensureInstance(current)
    const upstream = net.connect(instance.port, "127.0.0.1", () => {
      const headers = upstreamHeaders(req, instance.port)
      upstream.write(`${req.method} ${req.url} HTTP/${req.httpVersion}\r\n${Object.entries(headers).map(([name, value]) => `${name}: ${value}`).join("\r\n")}\r\n\r\n`)
      if (head.length) upstream.write(head)
      socket.pipe(upstream).pipe(socket)
    })
    upstream.on("error", () => socket.destroy())
  } catch {
    socket.destroy()
  }
})

setInterval(() => {
  const cutoff = Date.now() - idleMs
  for (const [userId, instance] of active) if (instance.lastUsed < cutoff) stopInstance(userId)
}, 60_000).unref()
refreshPublicKnowledge()
setInterval(refreshPublicKnowledge, 5 * 60_000).unref()

http.createServer((req, res) => {
  const client = providerUrl.protocol === "https:" ? https : http
  const headers = { ...req.headers, host: providerUrl.host, authorization: `Bearer ${providerKey}` }
  const upstream = client.request({ protocol: providerUrl.protocol, hostname: providerUrl.hostname, port: providerUrl.port || undefined, method: req.method, path: providerApiPath(providerUrl.pathname, req.url || "/"), headers }, response => {
    const userId = String(req.headers.authorization || "").replace(/^Bearer runtime-proxy:/, "")
    const chunks = []
    response.on("data", chunk => chunks.push(chunk))
    response.on("end", () => { try { recordUsage(userId, JSON.parse(Buffer.concat(chunks).toString()).usage) } catch {} })
    res.writeHead(response.statusCode || 502, response.headers)
    response.pipe(res)
  })
  upstream.on("error", () => { res.writeHead(502); res.end("provider unavailable") })
  req.pipe(upstream)
}).listen(4199, "127.0.0.1")

for (const signal of ["SIGTERM", "SIGINT"]) process.on(signal, () => {
  for (const userId of active.keys()) stopInstance(userId)
  server.close(() => process.exit(0))
})

if (process.argv.includes("--self-test")) {
  const id = "00000000-0000-4000-8000-000000000001"
  if (!identity({ headers: { "x-insight-runtime-secret": internalSecret, "x-insight-user-id": id } })) process.exit(1)
  if (identity({ headers: { "x-insight-runtime-secret": internalSecret, "x-insight-user-id": "../escape" } })) process.exit(1)
  if (providerApiPath("/openai/v1", "/v1/chat/completions") !== "/openai/v1/chat/completions") process.exit(1)
  if (nextUid("admin", [{ uid: adminGid }, { uid: firstAdminUid }]) !== firstAdminUid + 1) process.exit(1)
  if (!readFileSync(workspaceRulesTemplate, "utf8").includes("/knowledge/public/insight-public-data.json")) process.exit(1)
  process.exit(0)
}

server.listen(4096, "0.0.0.0")
