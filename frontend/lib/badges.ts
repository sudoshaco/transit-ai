// Berechnet Abzeichen clientseitig aus bereits vorhandenen Profilfeldern.
// Keine zusätzliche Backend-Abfrage nötig — alles aus created_at / karma / comment_count.

export type BadgeTone =
  | 'amber' | 'emerald' | 'cyan' | 'violet' | 'rose' | 'zinc' | 'gold'

export interface Badge {
  id: string
  label: string
  hint: string
  tone: BadgeTone
  icon: string // Unicode glyph, kein Emoji-Set nötig
}

interface BadgeInput {
  joined: string // ISO date
  karma: number
  comment_count: number
  username?: string | null
}

const DAY = 1000 * 60 * 60 * 24

export function daysSince(iso: string): number {
  const t = new Date(iso).getTime()
  if (!Number.isFinite(t)) return 0
  return Math.max(0, Math.floor((Date.now() - t) / DAY))
}

export function tenureBadge(days: number): Badge {
  if (days >= 365) return { id: 'veteran', label: 'Veteran', hint: `Seit ${Math.floor(days/365)} Jahr${Math.floor(days/365)>1?'en':''} dabei`, tone: 'gold', icon: '★' }
  if (days >= 180) return { id: 'stammgast', label: 'Stammgast', hint: `${days} Tage dabei`,             tone: 'amber',   icon: '◆' }
  if (days >= 30)  return { id: 'pendler',   label: 'Pendler',   hint: `${days} Tage dabei`,             tone: 'cyan',    icon: '●' }
  if (days >= 7)   return { id: 'neuling',   label: 'Neuling',   hint: `${days} Tage dabei`,             tone: 'emerald', icon: '◐' }
  return              { id: 'frisch',    label: 'Frisch an Bord', hint: `${days} Tag${days===1?'':'e'} dabei`, tone: 'zinc', icon: '◌' }
}

export function karmaBadge(karma: number): Badge | null {
  if (karma >= 500) return { id: 'legende',   label: 'Legende',   hint: `${karma} Karma`, tone: 'gold',    icon: '⬢' }
  if (karma >= 100) return { id: 'mentor',    label: 'Mentor',    hint: `${karma} Karma`, tone: 'violet',  icon: '▲' }
  if (karma >= 25)  return { id: 'ratgeber',  label: 'Ratgeber',  hint: `${karma} Karma`, tone: 'cyan',    icon: '△' }
  if (karma >= 5)   return { id: 'hinweisgeber', label: 'Hinweisgeber', hint: `${karma} Karma`, tone: 'emerald', icon: '○' }
  return null
}

export function activityBadge(comments: number): Badge | null {
  if (comments >= 100) return { id: 'vielschreiber', label: 'Vielschreiber', hint: `${comments} Hinweise geteilt`, tone: 'rose',    icon: '✶' }
  if (comments >= 25)  return { id: 'aktiv',         label: 'Aktiv',         hint: `${comments} Hinweise geteilt`, tone: 'violet',  icon: '✦' }
  if (comments >= 5)   return { id: 'teilnehmer',    label: 'Teilnehmer',    hint: `${comments} Hinweise geteilt`, tone: 'emerald', icon: '·' }
  if (comments >= 1)   return { id: 'debutant',      label: 'Debütant',      hint: `${comments} Hinweis geteilt`,  tone: 'cyan',    icon: '→' }
  return null
}

// Themen-Abzeichen — spezifisch, aber rein aus vorhandenen Feldern ableitbar.
function themedBadges({ joined, karma, comment_count, username }: BadgeInput): Badge[] {
  const out: Badge[] = []
  const days = daysSince(joined)
  const ratio = comment_count > 0 ? karma / comment_count : 0
  const joinDate = new Date(joined)
  const month = joinDate.getUTCMonth() + 1

  if (comment_count >= 3 && ratio >= 5) {
    out.push({ id: 'qualitaet', label: 'Qualitätsposter', hint: `Ø ${ratio.toFixed(1)} Karma pro Hinweis`, tone: 'gold', icon: '✧' })
  }
  if (days >= 30 && comment_count === 0) {
    out.push({ id: 'beobachter', label: 'Beobachter', hint: 'Liest mit, schreibt (noch) nicht', tone: 'zinc', icon: '◉' })
  }
  if (days <= 7 && comment_count >= 1) {
    out.push({ id: 'schnellstart', label: 'Schnellstarter', hint: 'Direkt in der ersten Woche aktiv', tone: 'emerald', icon: '»' })
  }
  if (month === 12 || month === 1) {
    out.push({ id: 'wintergast', label: 'Wintergast', hint: 'Beitritt in der kalten Jahreszeit', tone: 'cyan', icon: '❄' })
  } else if (month >= 6 && month <= 8) {
    out.push({ id: 'sommergast', label: 'Sommergast', hint: 'Beitritt in der Sommersaison', tone: 'amber', icon: '☀' })
  }
  if (username && username.length <= 4) {
    out.push({ id: 'kurzname', label: 'Kurzname', hint: 'Seltener 3–4-Zeichen-Name', tone: 'violet', icon: 'λ' })
  }
  return out
}

export function computeBadges(input: BadgeInput): Badge[] {
  const all: (Badge | null)[] = [
    tenureBadge(daysSince(input.joined)),
    karmaBadge(input.karma),
    activityBadge(input.comment_count),
    ...themedBadges(input),
  ]
  const seen = new Set<string>()
  const out: Badge[] = []
  for (const b of all) {
    if (!b || seen.has(b.id)) continue
    seen.add(b.id)
    out.push(b)
  }
  return out
}

export const TONE_CLASSES: Record<BadgeTone, string> = {
  amber:   'bg-amber-500/10 text-amber-300 border-amber-500/30',
  emerald: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30',
  cyan:    'bg-cyan-500/10 text-cyan-300 border-cyan-500/30',
  violet:  'bg-violet-500/10 text-violet-300 border-violet-500/30',
  rose:    'bg-rose-500/10 text-rose-300 border-rose-500/30',
  zinc:    'bg-zinc-500/10 text-zinc-300 border-zinc-500/30',
  gold:    'bg-yellow-500/15 text-yellow-300 border-yellow-500/40 shadow-[0_0_12px_-4px_rgba(234,179,8,0.5)]',
}
