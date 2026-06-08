/**
 * Cert Atlas data loader.
 *
 * Reads the published Cert Atlas dataset — the same JSON the website serves:
 *   - data/index.json                       (1,580-exam catalog)
 *   - data/<vendor_slug>/<exam_id>.json      (full per-exam blueprint)
 *
 * Source resolution (in order):
 *   1. A local `data/` directory, when the server runs from inside the cert-atlas
 *      repo (or CERT_ATLAS_DATA_DIR is set). Fast, offline, always in sync.
 *   2. raw.githubusercontent.com/hans6883/cert-atlas/master — used when the
 *      package is installed standalone (e.g. `npx cert-atlas-mcp`), so users
 *      always get the latest published blueprints with no bundled data.
 *
 * Read-only. No API key, no auth — public data only.
 */
import { promises as fs } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve, join } from "node:path";

const RAW_BASE =
  process.env.CERT_ATLAS_RAW_BASE?.replace(/\/+$/, "") ??
  "https://raw.githubusercontent.com/hans6883/cert-atlas/master";

const UA = "cert-atlas-mcp/1.2 (+https://github.com/hans6883/cert-atlas)";

/**
 * Ordered list of local `data/` directories to try before the network:
 *   1. CERT_ATLAS_DATA_DIR  — explicit data dir.
 *   2. CERT_ATLAS_LOCAL/data — repo root (used by the VPS/remote deployment).
 *   3. <dist>/../../data     — repo-local, when run from inside the cert-atlas repo.
 *   4. <dist>/../data        — the snapshot bundled in the npm package (instant search).
 * The bundled index.json makes search work offline/instantly; blueprints not in any
 * local dir are lazy-fetched from raw GitHub (so the install stays tiny).
 */
function localDataDirs(): string[] {
  const dirs: string[] = [];
  if (process.env.CERT_ATLAS_DATA_DIR) dirs.push(process.env.CERT_ATLAS_DATA_DIR);
  if (process.env.CERT_ATLAS_LOCAL) dirs.push(join(process.env.CERT_ATLAS_LOCAL, "data"));
  try {
    const here = dirname(fileURLToPath(import.meta.url)); // .../mcp/dist
    dirs.push(resolve(here, "..", "..", "data")); // repo: .../cert-atlas/data
    dirs.push(resolve(here, "..", "data")); // bundled: .../mcp/data
  } catch {
    /* import.meta.url unavailable — remote only */
  }
  return dirs;
}

const LOCAL_DIRS = localDataDirs();
const sourcesUsed = new Set<string>();

/** Read a dataset file by its path relative to data/ (e.g. "index.json", "aws/x.json"). */
async function readData(relPath: string): Promise<unknown> {
  for (const dir of LOCAL_DIRS) {
    try {
      const txt = await fs.readFile(join(dir, relPath), "utf8");
      sourcesUsed.add(dir);
      return JSON.parse(txt);
    } catch {
      /* try the next candidate, then remote */
    }
  }
  const res = await fetch(`${RAW_BASE}/data/${relPath}`, { headers: { "User-Agent": UA } });
  if (!res.ok) throw new Error(`Cert Atlas fetch failed for data/${relPath}: HTTP ${res.status}`);
  sourcesUsed.add(`${RAW_BASE}/data`);
  return res.json();
}

/** Where data has actually been read from, for diagnostics. */
export function dataSource(): string {
  if (sourcesUsed.size) return [...sourcesUsed].join(", ");
  return `auto (local candidates: ${LOCAL_DIRS.length}, remote: ${RAW_BASE}/data)`;
}

// ---------------------------------------------------------------------------
// Funnel: append QuizForge UTM attribution + a one-line CTA to every practice link
// ---------------------------------------------------------------------------
const UTM_MEDIUM = "cert_atlas";

/**
 * Append utm_source/medium/campaign to a practice_url, preserving any existing
 * query. utm_campaign is the tool that produced the link, so analytics shows
 * which agent intent converts. Returns null only when there is no url.
 */
export function withUtm(url: string | null | undefined, tool: string): string | null {
  if (!url) return null;
  try {
    const u = new URL(url);
    if (!u.searchParams.has("utm_source")) u.searchParams.set("utm_source", "mcp");
    if (!u.searchParams.has("utm_medium")) u.searchParams.set("utm_medium", UTM_MEDIUM);
    u.searchParams.set("utm_campaign", tool);
    return u.toString();
  } catch {
    const sep = url.includes("?") ? "&" : "?";
    return `${url}${sep}utm_source=mcp&utm_medium=${UTM_MEDIUM}&utm_campaign=${tool}`;
  }
}

/** Factual, singular call-to-action for a single exam's practice link. */
export function practiceCta(examName: string, practiceUrl: string): string {
  return `Free practice exam for ${examName} → ${practiceUrl}`;
}

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
export interface IndexEntry {
  exam_id: string;
  exam_name: string;
  exam_code: string | null;
  certifying_body: string;
  vendor_slug: string;
  domains: number;
  total_questions: number | null;
  duration_minutes: number | null;
  source_url: string | null;
  practice_url: string | null;
}

interface IndexFile {
  generated: string;
  total_exams: number;
  total_vendors: number;
  exams_with_domain_breakdowns: number;
  exams: IndexEntry[];
}

export interface Domain {
  id?: string;
  name: string;
  weight_percent?: number | null;
  objectives?: Array<string | { id?: string; name?: string; description?: string }> | null;
}

export interface Blueprint {
  exam_id: string;
  exam_name: string;
  exam_code: string | null;
  certifying_body: string | null;
  certification_name?: string | null;
  source_url?: string | null;
  passing_score?: number | string | null;
  passing_score_scale?: string | null;
  total_questions?: number | null;
  question_types?: string[] | null;
  exam_format?: string | null;
  duration_minutes?: number | null;
  exam_price_usd?: number | null;
  exam_price_notes?: string | null;
  exam_registration_url?: string | null;
  online_proctoring_available?: boolean | null;
  certification_validity_years?: number | null;
  renewal_required?: boolean | null;
  renewal_options?: string | null;
  available_languages?: string[] | null;
  target_audience?: string | null;
  recommended_experience?: string | null;
  prerequisites?: string[] | string | null;
  retake_policy?: string | null;
  domains?: Domain[] | null;
  official_objectives_url?: string | null;
  aliases?: string[] | null;
  practice_url?: string | null;
  [k: string]: unknown;
}

export interface Index {
  meta: { generated: string; total_exams: number; total_vendors: number };
  exams: IndexEntry[];
  byBody: Map<string, IndexEntry[]>;
  loadedAt: number;
}

// ---------------------------------------------------------------------------
// Loading + caching
// ---------------------------------------------------------------------------
let cache: Index | null = null;
let inflight: Promise<Index> | null = null;
const TTL_MS = 6 * 60 * 60 * 1000; // 6h
const bpCache = new Map<string, Blueprint>();

export async function getIndex(): Promise<Index> {
  if (cache && Date.now() - cache.loadedAt < TTL_MS) return cache;
  if (inflight) return inflight;
  inflight = (async () => {
    const data = (await readData("index.json")) as IndexFile;
    const exams = data.exams ?? [];
    const byBody = new Map<string, IndexEntry[]>();
    for (const e of exams) {
      const body = e.certifying_body || "Unknown";
      if (!byBody.has(body)) byBody.set(body, []);
      byBody.get(body)!.push(e);
    }
    cache = {
      meta: {
        generated: data.generated,
        total_exams: data.total_exams ?? exams.length,
        total_vendors: data.total_vendors ?? byBody.size,
      },
      exams,
      byBody,
      loadedAt: Date.now(),
    };
    inflight = null;
    return cache;
  })();
  return inflight;
}

export async function getBlueprint(entry: IndexEntry): Promise<Blueprint> {
  const cached = bpCache.get(entry.exam_id);
  if (cached) return cached;
  const bp = (await readData(`${entry.vendor_slug}/${entry.exam_id}.json`)) as Blueprint;
  bpCache.set(entry.exam_id, bp);
  return bp;
}

// ---------------------------------------------------------------------------
// Text coercion (blueprint fields are sometimes nested objects, e.g. retake_policy)
// ---------------------------------------------------------------------------
/** Flatten an arbitrary blueprint value into readable one-line text. */
export function toText(v: unknown): string {
  if (v == null) return "";
  if (typeof v === "string") return v.trim();
  if (typeof v === "number" || typeof v === "boolean") return String(v);
  if (Array.isArray(v)) return v.map(toText).filter(Boolean).join("; ");
  if (typeof v === "object") {
    const o = v as Record<string, unknown>;
    // Prefer a human-readable summary field if present.
    if (typeof o.notes === "string" && o.notes.trim()) return o.notes.trim();
    if (typeof o.description === "string" && o.description.trim()) return o.description.trim();
    return Object.entries(o)
      .filter(([, val]) => val != null && val !== "")
      .map(([k, val]) => `${k.replace(/_/g, " ")}: ${toText(val)}`)
      .join("; ");
  }
  return String(v);
}

// ---------------------------------------------------------------------------
// Search / resolution
// ---------------------------------------------------------------------------
/**
 * Generic tokens that appear in a huge share of exam names and carry no
 * discriminating signal — ignored when scoring so a query like "this exam does
 * not exist" can't phantom-match every record containing the word "exam".
 */
const STOPWORDS = new Set([
  "the", "a", "an", "of", "and", "or", "for", "to", "in", "on", "is", "it",
  "this", "that", "does", "not", "no", "with", "your", "my",
  "exam", "exams", "test", "tests", "testing", "certification", "certifications",
  "certificate", "certified", "cert", "certifying", "credential", "credentials",
  "level", "professional", "associate", "specialist", "practitioner",
]);

/** Lightweight relevance scoring across name, code, id, and body. */
export function scoreMatch(e: IndexEntry, q: string): number {
  const query = q.toLowerCase().trim();
  if (!query) return 0;
  const code = (e.exam_code ?? "").toLowerCase();
  const id = e.exam_id.toLowerCase();
  const name = e.exam_name.toLowerCase();
  const body = e.certifying_body.toLowerCase();
  if (query === id || (code && query === code)) return 1000;
  if (query === name) return 900;
  const hay = `${name} ${code} ${id} ${body}`;
  const idParts = id.split("-");
  let score = 0;
  for (const t of query.split(/\s+/).filter(Boolean)) {
    if (!hay.includes(t)) continue;
    // A generic token (e.g. "exam", "certified") scores only on an exact full-code
    // match — never on substrings or id-parts — so junk queries can't phantom-match
    // every record whose name or id merely contains the word "exam".
    if (STOPWORDS.has(t)) {
      if (code && code === t) score += 8;
      continue;
    }
    score += 10;
    if (code && code.includes(t)) score += 8;
    if (name.startsWith(t)) score += 5;
    if (idParts.includes(t)) score += 4;
    if (body.includes(t)) score += 3;
  }
  return score;
}

/** Resolve an exam by id (exact), code (exact), else best fuzzy name/keyword match. */
export async function resolveExam(query: string): Promise<IndexEntry | null> {
  const { exams } = await getIndex();
  const q = query.toLowerCase().trim();
  if (!q) return null;
  const byId = exams.find((e) => e.exam_id.toLowerCase() === q);
  if (byId) return byId;
  const byCode = exams.find((e) => (e.exam_code ?? "").toLowerCase() === q);
  if (byCode) return byCode;
  // Require at least one real (non-generic) token hit — every such hit scores >=10 —
  // so a vague or garbage query resolves to nothing rather than a wrong blueprint.
  let best: { e: IndexEntry; s: number } | null = null;
  for (const e of exams) {
    const s = scoreMatch(e, query);
    if (s >= 10 && (!best || s > best.s)) best = { e, s };
  }
  return best?.e ?? null;
}
