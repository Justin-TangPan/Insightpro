import { timingSafeEqual } from "node:crypto"
import { spawn } from "node:child_process"
import { cpSync, existsSync, mkdirSync, openSync, readFileSync, readdirSync, renameSync, symlinkSync, writeFileSync, chownSync, chmodSync } from "node:fs"
import http from "node:http"
import net from "node:net"
import path from "node:path"

const root = process.env.INSIGHT_AGENT_DATA_ROOT || "/srv/insight-agent"
const spacesRoot = path.join(root, "spaces")
const registryPath = path.join(root, "registry.json")
const templateRoot = "/template"
const knowledgeRoot = "/knowledge/public"
const adminUid = 10002
const firstUserUid = 20000
const firstPort = 12000
const maxActive = Number(process.env.OPENCODE_MAX_ACTIVE || 6)
const idleMs = Number(process.env.OPENCODE_IDLE_SECONDS || 1800) * 1000
const internalSecret = process.env.OPENCODE_GATEWAY_SECRET || ""
const basicAuth = `Basic ${Buffer.from(`${process.env.OPENCODE_SERVER_USERNAME}:${process.env.OPENCODE_SERVER_PASSWORD}`).toString("base64")}`
const active = new Map()
const starting = new Map()

process.umask(0o007)

mkdirSync(spacesRoot, { recursive: true, mode: 0o711 })
mkdirSync(knowledgeRoot, { recursive: true, mode: 0o755 })
chmodSync(spacesRoot, 0o711)
chmodSync(knowledgeRoot, 0o755)
chownSync(knowledgeRoot, adminUid, adminUid)

let registry = existsSync(registryPath) ? JSON.parse(readFileSync(registryPath, "utf8")) : { users: {} }

function saveRegistry() {
  writeFileSync(registryPath, JSON.stringify(registry, null, 2), { mode: 0o600 })
}

function safeEqual(left, right) {
  const a = Buffer.from(left || "")
  const b = Buffer.from(right || "")
  return a.length === b.length && a.length > 0 && timingSafeEqual(a, b)
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
  }
}

function recordFor({ userId, role, displayName }) {
  let record = registry.users[userId]
  if (!record) {
    const records = Object.values(registry.users)
    record = {
      uid: role === "admin" ? adminUid : Math.max(firstUserUid, ...records.map(item => item.uid + 1)),
      port: Math.max(firstPort, ...records.map(item => item.port + 1)),
      role,
      displayName,
      createdAt: new Date().toISOString(),
    }
    registry.users[userId] = record
  } else {
    if (record.role !== role) {
      const userUids = Object.values(registry.users).filter(item => item.uid >= firstUserUid).map(item => item.uid + 1)
      record.uid = role === "admin" ? adminUid : Math.max(firstUserUid, ...userUids)
    }
    record.role = role
    record.displayName = displayName || record.displayName
  }
  saveRegistry()
  return record
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

function copyConfig(space, role) {
  const configRoot = path.join(space, "config", "opencode")
  mkdirSync(path.join(configRoot, "tools"), { recursive: true, mode: 0o755 })
  cpSync(role === "admin" ? "/opt/insight-agent/opencode.admin.json" : "/opt/insight-agent/opencode.user.json", path.join(configRoot, "opencode.json"))
  cpSync("/opt/insight-agent/tools/insight_public_data.ts", path.join(configRoot, "tools", "insight_public_data.ts"))
  ownTree(path.join(space, "config"), 0, adminUid, 0o755)
  chmodSync(path.join(configRoot, "opencode.json"), 0o444)
  chmodSync(path.join(configRoot, "tools", "insight_public_data.ts"), 0o444)
}

function ensureSpace(identityValue, record) {
  const space = path.join(spacesRoot, identityValue.userId)
  const ownershipMarker = path.join(space, ".ownership-role")
  const ownershipRole = existsSync(ownershipMarker) ? readFileSync(ownershipMarker, "utf8") : ""
  mkdirSync(space, { recursive: true, mode: 0o2770 })
  adoptLegacy(space, identityValue.role)
  for (const name of ["data", "cache", "state", "home"]) mkdirSync(path.join(space, name), { recursive: true, mode: 0o2770 })
  const workspace = path.join(space, "workspace")
  if (!existsSync(workspace)) cpSync(templateRoot, workspace, { recursive: true })
  if (!existsSync(path.join(workspace, "public-knowledge"))) symlinkSync(knowledgeRoot, path.join(workspace, "public-knowledge"), "dir")
  if (ownershipRole !== identityValue.role) {
    for (const name of ["data", "cache", "state", "home", "workspace"]) ownTree(path.join(space, name), record.uid, adminUid)
    chownSync(space, record.uid, adminUid)
    chmodSync(space, 0o2770)
    writeFileSync(ownershipMarker, identityValue.role, { mode: 0o660 })
    chownSync(ownershipMarker, record.uid, adminUid)
  }
  copyConfig(space, identityValue.role)
  return { space, workspace }
}

async function processHealthy(port) {
  try {
    const response = await fetch(`http://127.0.0.1:${port}/global/health`, { headers: { Authorization: basicAuth }, signal: AbortSignal.timeout(500) })
    return response.ok && (await response.json()).healthy === true
  } catch {
    return false
  }
}

function stopInstance(userId) {
  const instance = active.get(userId)
  if (!instance) return
  instance.child.kill("SIGTERM")
  active.delete(userId)
}

async function ensureInstance(identityValue) {
  const existing = active.get(identityValue.userId)
  if (existing && !existing.child.killed && existing.role === identityValue.role) {
    existing.lastUsed = Date.now()
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
    const { space, workspace } = ensureSpace(identityValue, record)
    const log = openSync(path.join(space, "runtime.log"), "a")
    const child = spawn("opencode", ["web", "--hostname", "127.0.0.1", "--port", String(record.port)], {
      cwd: workspace,
      uid: record.uid,
      gid: identityValue.role === "admin" ? adminUid : record.uid,
      env: {
        ...process.env,
        HOME: path.join(space, "home"),
        XDG_CACHE_HOME: path.join(space, "cache"),
        XDG_CONFIG_HOME: path.join(space, "config"),
        XDG_DATA_HOME: path.join(space, "data"),
        XDG_STATE_HOME: path.join(space, "state"),
      },
      stdio: ["ignore", log, log],
    })
    child.once("exit", () => active.delete(identityValue.userId))
    const instance = { child, port: record.port, workspace, role: identityValue.role, lastUsed: Date.now() }
    active.set(identityValue.userId, instance)
    for (let attempt = 0; attempt < 100; attempt += 1) {
      if (await processHealthy(record.port)) return instance
      if (child.exitCode !== null) throw new Error(`OpenCode process exited for ${identityValue.userId}`)
      await new Promise(resolve => setTimeout(resolve, 100))
    }
    stopInstance(identityValue.userId)
    throw new Error(`OpenCode startup timeout for ${identityValue.userId}`)
  })().finally(() => starting.delete(identityValue.userId))
  starting.set(identityValue.userId, promise)
  return promise
}

function upstreamHeaders(req, port) {
  const headers = { ...req.headers, host: `127.0.0.1:${port}`, authorization: basicAuth }
  for (const name of Object.keys(headers)) if (name.startsWith("x-insight-")) delete headers[name]
  delete headers.cookie
  return headers
}

const server = http.createServer(async (req, res) => {
  if (req.url === "/healthz") return void res.end("healthy\n")
  const current = identity(req)
  if (!current) {
    res.writeHead(401)
    return void res.end("unauthorized")
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

for (const signal of ["SIGTERM", "SIGINT"]) process.on(signal, () => {
  for (const userId of active.keys()) stopInstance(userId)
  server.close(() => process.exit(0))
})

if (process.argv.includes("--self-test")) {
  const id = "00000000-0000-4000-8000-000000000001"
  if (!identity({ headers: { "x-insight-runtime-secret": internalSecret, "x-insight-user-id": id } })) process.exit(1)
  if (identity({ headers: { "x-insight-runtime-secret": internalSecret, "x-insight-user-id": "../escape" } })) process.exit(1)
  process.exit(0)
}

server.listen(4096, "0.0.0.0")
