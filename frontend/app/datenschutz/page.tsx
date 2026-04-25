import { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Datenschutz — TransitAI',
  description: 'Datenschutzerklärung nach Art. 13 DSGVO',
  robots: { index: true, follow: false },
}

export default function DatenschutzPage() {
  return (
    <main className="min-h-screen bg-background px-4 py-16">
      <div className="max-w-2xl mx-auto">
        <a href="/" className="text-muted hover:text-white transition-colors text-sm mb-8 block">
          &larr; Zurück
        </a>

        <h1 className="text-4xl font-bold text-white mb-6 font-headline">Datenschutz</h1>

        <div className="space-y-6 text-gray-300 leading-relaxed text-[15px]">
          <section className="bg-white/5 border border-accent/30 rounded-lg p-4">
            <p className="text-white font-semibold mb-2">Kurzfassung</p>
            <p className="text-sm">
              TransitAI ist ein nicht-kommerzielles Lern- und Demonstrationsprojekt zur
              KI-gestützten Reiseplanung im öffentlichen Verkehr. Wer den Dienst nur sucht und nutzt,
              wird nicht identifiziert. Wer sich registriert, hinterlegt Mail, ein gehashtes
              Passwort und optional einen Nutzernamen plus Kurzprofil — nicht mehr.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-white mb-2">1. Verantwortlicher</h2>
            <p>
              Sebastian Islamyar<br />
              Kelsterbacherstraße 14, 60528 Frankfurt am Main<br />
              E-Mail: <a href="mailto:kontakt@sebastian-netzwerke.de" className="text-accent hover:underline">kontakt@sebastian-netzwerke.de</a>
            </p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-white mb-2">2. Was wir verarbeiten</h2>
            <ul className="list-disc list-inside space-y-2">
              <li>
                <strong className="text-white">Reiseanfragen</strong> (freier Text) — nur für die
                Beantwortung der Anfrage, nicht dauerhaft gespeichert. Kurzzeit-Cache bis 5 Minuten.
              </li>
              <li>
                <strong className="text-white">Konto-Daten</strong> (nur bei Registrierung):
                E-Mail, Passwort als Argon2-Hash, optional Nutzername, Kurzprofil („Bio", max. 280 Zeichen),
                Karma-Punktzahl. Kein Klarname, keine Adresse.
              </li>
              <li>
                <strong className="text-white">Auth-Cookies</strong> (technisch erforderlich):
                <code className="text-xs"> tai_at</code>, <code className="text-xs">tai_rt</code>,
                <code className="text-xs"> tai_csrf</code> — halten die Sitzung und verhindern CSRF.
                Nur gesetzt, wenn du dich einloggst.
              </li>
              <li>
                <strong className="text-white">Community-Beiträge</strong>: Kommentare und Votes zu
                Verbindungen sind öffentlich sichtbar und deinem Nutzernamen zugeordnet.
              </li>
              <li>
                <strong className="text-white">Audit- und Serverlogs</strong>: IP, User-Agent,
                Anmeldevorgänge und sicherheitsrelevante Ereignisse, max. 30 Tage, ausschließlich für
                Missbrauchsabwehr und Fehlerdiagnose.
              </li>
              <li>
                <strong className="text-white">Spracheingabe (optional)</strong>: Wenn du das
                Mikrofon verwendest, wird der Audio-Schnipsel an unseren Server übertragen,
                lokal transkribiert (Whisper) und sofort verworfen. Keine Ablage.
              </li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-bold text-white mb-2">3. KI-Verarbeitung</h2>
            <p>
              Für das Verstehen deiner Anfrage und die Zusammenfassung der Verbindung nutzen wir
              offene Sprachmodelle (Llama, Qwen) — primär die Groq-API (USA) als Beschleuniger,
              alternativ ein lokal gehostetes Open-Source-Modell auf unserem eigenen Server.
              An die KI geht nur der Anfrage-Text, nie IP, Konto oder Cookie.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-white mb-2">4. Weitergabe an Dritte</h2>
            <ul className="list-disc list-inside space-y-1 text-sm">
              <li><strong className="text-white">Groq, Inc.</strong> (USA) — KI-Inferenz, nur Anfrage-Text.</li>
              <li><strong className="text-white">Deutsche Bahn AG</strong> — Fahrplan- und Stationsdaten.</li>
              <li><strong className="text-white">OpenStreetMap / CARTO</strong> — Kartenkacheln, dein Browser lädt sie direkt.</li>
            </ul>
            <p className="mt-2 text-sm">Kein Ad-Tech, kein Tracking, keine Analytics.</p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-white mb-2">5. Drittland-Übermittlung (USA)</h2>
            <p className="text-sm">
              Durch die Groq-API und CARTO kann Anfrage-Text bzw. deine IP in die USA gelangen.
              Rechtsgrundlage: Art. 49 Abs. 1 lit. a/b DSGVO (Einwilligung bzw. Nutzungsverhältnis).
            </p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-white mb-2">6. Deine Rechte</h2>
            <p className="text-sm">
              Du kannst jederzeit Auskunft, Berichtigung und Löschung verlangen (Art. 15–17 DSGVO).
              Eigene Kommentare kannst du selbst löschen. Das komplette Konto löschen wir auf Anfrage
              per Mail oder Admin-Panel binnen 30 Tagen. Beschwerderecht: Hessischer Beauftragter für
              Datenschutz und Informationsfreiheit.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-white mb-2">7. Sicherheit</h2>
            <p className="text-sm">
              Passwörter liegen als Argon2-Hash, Logins laufen mit verpflichtender Zwei-Faktor-Auth
              (TOTP). JWTs werden rotiert, CSRF ist per Token abgesichert. Transport durchgehend
              über HTTPS. Der Quellcode wird laufend gegen OWASP-Top-10-Risiken (XSS, CSRF, RCE,
              SQL-Injection) gehärtet.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-white mb-2">8. Projektstatus</h2>
            <p className="text-sm">
              TransitAI ist ein nicht-kommerzielles Lernprojekt. Der Dienst kann jederzeit ohne
              Vorankündigung verändert oder eingestellt werden. Es besteht kein Anspruch auf
              Verfügbarkeit oder Richtigkeit der Informationen.
            </p>
          </section>

          <section className="mt-10 pt-4 border-t border-white/10">
            <p className="text-muted text-xs">Stand: April 2026</p>
          </section>
        </div>
      </div>
    </main>
  )
}
