// Deep links in die DB Navigator App / bahn.de Buchung.
// Das Web-Frontend (next.bahn.de) akzeptiert denselben Hash wie die App; auf Mobilgeräten
// öffnet die App den Link automatisch, sonst fällt es auf die Webseite zurück.

type Station = { name?: string | null; id?: string | null } | null | undefined

function toIso(value: string | null | undefined): string | null {
  if (!value) return null
  try {
    const d = new Date(value)
    if (isNaN(d.getTime())) return null
    return d.toISOString()
  } catch {
    return null
  }
}

export function bahnSearchUrl(
  from: Station,
  to: Station,
  departure?: string | null
): string | null {
  const fromName = from?.name?.trim()
  const toName = to?.name?.trim()
  if (!fromName || !toName) return null
  const params = new URLSearchParams()
  params.set('sts', 'true')
  params.set('so', fromName)
  params.set('zo', toName)
  const iso = toIso(departure)
  if (iso) params.set('hd', iso)
  if (from?.id) params.set('soid', `A=1@L=${from.id}`)
  if (to?.id) params.set('zoid', `A=1@L=${to.id}`)
  return `https://next.bahn.de/buchung/fahrplan/suche#${params.toString()}`
}
