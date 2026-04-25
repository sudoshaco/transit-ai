import { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Über TransitAI',
}

export default function AboutPage() {
  return (
    <main className="min-h-screen bg-background px-4 py-16">
      <div className="max-w-2xl mx-auto">
        <a href="/" className="text-muted hover:text-white transition-colors text-sm mb-8 block">
          &larr; Zurück
        </a>

        <h1 className="text-4xl font-bold text-white mb-8 font-headline">
          Über Transit<span className="text-accent">AI</span>
        </h1>

        <div className="space-y-6 text-gray-300 leading-relaxed">
          <p>
            TransitAI ist ein KI-gestützter Reiseplaner für den öffentlichen
            Nahverkehr in Deutschland. Statt starrer Suchmasken beschreiben Sie
            Ihre Reise in natürlicher Sprache &mdash; die KI versteht Sie und
            findet die beste Verbindung.
          </p>

          <section className="bg-white/5 border border-accent/30 rounded-lg p-4">
            <p className="text-white font-semibold mb-2">
              Lern- und Demonstrationsprojekt
            </p>
            <p className="text-sm">
              TransitAI ist ein <strong>nicht-kommerzielles
              KI-Projekt auf Basis offener Modelle</strong>, das ausschließlich zu{' '}
              <strong>Lern-, Forschungs- und Demonstrationszwecken</strong>{' '}
              betrieben wird. Es wird auf eigener Infrastruktur gehostet und
              ist komplett kostenlos nutzbar. Es werden keine Nutzerdaten
              monetarisiert oder an Dritte verkauft.
            </p>
          </section>

          <h2 className="text-xl font-bold text-white mt-8">Funktionsweise</h2>
          <ul className="space-y-3">
            <li className="flex items-start gap-3">
              <span className="text-accent mt-1">&rarr;</span>
              <span>
                <strong className="text-white">Natürliche Sprache:</strong>{' '}
                Schreiben Sie z.&thinsp;B. &quot;Morgen früh nach Berlin, möglichst
                günstig&quot; oder &quot;Samstag hin, Sonntag zurück&quot;
              </span>
            </li>
            <li className="flex items-start gap-3">
              <span className="text-accent mt-1">&rarr;</span>
              <span>
                <strong className="text-white">KI-Empfehlung:</strong>{' '}
                Die KI analysiert alle Verbindungen und zeigt Ihnen die beste Wahl
                mit einer kurzen Zusammenfassung
              </span>
            </li>
            <li className="flex items-start gap-3">
              <span className="text-accent mt-1">&rarr;</span>
              <span>
                <strong className="text-white">Hin- &amp; Rückfahrt:</strong>{' '}
                Wenn Sie &quot;Samstag hin, Sonntag zurück&quot; eingeben, zeigt
                TransitAI beide Richtungen mit separaten Verbindungen
              </span>
            </li>
            <li className="flex items-start gap-3">
              <span className="text-accent mt-1">&rarr;</span>
              <span>
                <strong className="text-white">Komplett kostenlos:</strong>{' '}
                Keine Werbung, keine versteckten Kosten, keine Registrierung
              </span>
            </li>
          </ul>

          <h2 className="text-xl font-bold text-white mt-8">Technische Architektur</h2>
          <p>
            TransitAI nutzt eine hybride KI-Architektur. Die verwendeten <strong>Sprachmodelle sind Open Source</strong> (Llama&nbsp;3.3 von Meta), der Anwendungscode selbst ist nicht öffentlich:
          </p>
          <div className="mt-3 space-y-3">
            <div className="bg-white/5 rounded-lg p-3">
              <p className="text-white font-semibold text-sm mb-1">
                Groq Cloud API &mdash; Reasoning &amp; Zusammenfassung
              </p>
              <p className="text-sm">
                Die intelligente Interpretation Ihrer Anfrage (Erkennung von
                Start, Ziel, Zeitangaben, Präferenzen) sowie die KI-generierte
                Zusammenfassung der Ergebnisse übernimmt das Open-Source-Modell{' '}
                <strong className="text-white">Llama 3.1 8B Instant</strong>{' '}
                (Meta, Apache 2.0) über die Groq Cloud API. Die Verarbeitung
                erfolgt auf Groq-Servern in den USA. Es werden ausschließlich
                Anfrage-Texte übermittelt, keine personenbezogenen Daten.
              </p>
            </div>
            <div className="bg-white/5 rounded-lg p-3">
              <p className="text-white font-semibold text-sm mb-1">
                Lokales LLM &mdash; Self-Hosted Fallback
              </p>
              <p className="text-sm">
                Auf unserem eigenen Server in Deutschland läuft das
                Open-Source-Modell{' '}
                <strong className="text-white">Qwen 2.5 (7B Parameter)</strong>{' '}
                (Alibaba Cloud, Apache 2.0) über die Laufzeitumgebung Ollama.
                Dieses Modell dient als Fallback &mdash; sollte die Groq API
                nicht erreichbar sein, übernimmt es die Verarbeitung. Hierbei
                verlassen keine Daten unsere Infrastruktur.
              </p>
            </div>
            <div className="bg-white/5 rounded-lg p-3">
              <p className="text-white font-semibold text-sm mb-1">
                Fahrplandaten &mdash; Offizielle Quellen
              </p>
              <p className="text-sm">
                Die Verbindungs- und Fahrplandaten stammen von offiziellen
                Schnittstellen der Deutschen Bahn (DB API Marketplace: StaDa,
                FaSta, RIS::Stations) sowie von der Self-Hosted-Instanz von{' '}
                <a
                  href="https://github.com/derhuerst/db-rest"
                  target="_blank"
                  rel="noopener noreferrer nofollow"
                  className="text-accent hover:underline"
                >
                  db-rest
                </a>{' '}
                (Open-Source HAFAS-Wrapper). Preise werden in Echtzeit von
                den Bahn-APIs bezogen und können von den tatsächlichen Kosten
                abweichen.
              </p>
            </div>
          </div>

          <h2 className="text-xl font-bold text-white mt-8">Datenschutz &amp; Cookies</h2>
          <p>
            TransitAI kommt ohne Werbe-Tracking aus. Technisch notwendig sind
            aber einige Cookies &mdash; nur dann, wenn du dich registrierst
            oder einloggst. Ohne Account werden keinerlei Cookies gesetzt.
          </p>
          <div className="mt-3 space-y-3">
            <div className="bg-white/5 rounded-lg p-3">
              <p className="text-white font-semibold text-sm mb-1">
                Session-Cookies (nur bei Login)
              </p>
              <p className="text-sm">
                Nach dem Einloggen werden zwei HttpOnly-Cookies gesetzt
                (<code>tai_access</code>, <code>tai_refresh</code>) sowie ein
                CSRF-Token-Cookie (<code>tai_csrf</code>). Diese sind an unsere
                Domain gebunden (SameSite=Strict), laufen automatisch ab und
                dienen ausschließlich der Sitzung. Keine Werbung, kein Tracking.
              </p>
            </div>
            <div className="bg-white/5 rounded-lg p-3">
              <p className="text-white font-semibold text-sm mb-1">
                Was wir speichern &mdash; und was nicht
              </p>
              <ul className="text-sm space-y-1.5 mt-1.5">
                <li className="flex gap-2"><span className="text-green-400">&#10003;</span><span><strong className="text-white">Account:</strong> E-Mail (Login), Passwort (Argon2-Hash), optional Username/Bio/Karma.</span></li>
                <li className="flex gap-2"><span className="text-green-400">&#10003;</span><span><strong className="text-white">2-Faktor (TOTP):</strong> Secret verschlüsselt abgelegt, Backup-Codes nur als Hash.</span></li>
                <li className="flex gap-2"><span className="text-green-400">&#10003;</span><span><strong className="text-white">Audit-Log:</strong> Login-Versuche, Passwort-/Bio-/Namensänderungen (IP + User-Agent, 90 Tage) &mdash; zur Missbrauchs-Erkennung.</span></li>
                <li className="flex gap-2"><span className="text-green-400">&#10003;</span><span><strong className="text-white">Community-Hinweise:</strong> Deine Kommentare zu Verbindungen sind mit deinem Username verknüpft.</span></li>
                <li className="flex gap-2"><span className="text-red-400">&times;</span><span><strong className="text-white">Suchanfragen:</strong> werden <em>nicht</em> dauerhaft gespeichert &mdash; nur kurz im Cache für schnellere Antworten.</span></li>
                <li className="flex gap-2"><span className="text-red-400">&times;</span><span><strong className="text-white">Kein Tracking:</strong> kein Google Analytics, kein Meta Pixel, keine Werbe-Cookies, keine Third-Party-Skripte.</span></li>
                <li className="flex gap-2"><span className="text-red-400">&times;</span><span><strong className="text-white">Kein Verkauf:</strong> wir geben keine Daten an Dritte weiter oder monetarisieren sie.</span></li>
              </ul>
            </div>
            <div className="bg-white/5 rounded-lg p-3">
              <p className="text-white font-semibold text-sm mb-1">
                Deine Kontrolle
              </p>
              <p className="text-sm">
                Du kannst jederzeit alle deine Daten löschen lassen, deinen
                Username oder deine Bio ändern oder Kommentare entfernen. Cookies
                kannst du im Browser jederzeit manuell löschen &mdash; ein Logout
                entfernt sie ebenfalls vollständig.
              </p>
            </div>
          </div>
          <p className="text-sm text-muted mt-3">
            Vollständige Details in unserer{' '}
            <a href="/datenschutz" className="text-accent hover:underline">
              Datenschutzerklärung
            </a>.
          </p>

          <h2 className="text-xl font-bold text-white mt-8">Hinweis zur KI-generierten Zusammenfassung</h2>
          <p>
            Die auf der Ergebnisseite angezeigte &quot;KI-Zusammenfassung&quot;
            wird automatisch durch ein Sprachmodell generiert. Die Verbindungen
            selbst stammen aus offiziellen Fahrplandaten; die textuelle
            Beschreibung ist jedoch maschinell erstellt und kann Ungenauigkeiten
            enthalten. Für verbindliche Auskünfte nutzen Sie bitte die
            offiziellen Kanäle der Deutschen Bahn oder Ihres Verkehrsverbunds.
          </p>

          <h2 className="text-xl font-bold text-white mt-8">Warum kostenlos?</h2>
          <p>
            Dieses Projekt entstand aus Leidenschaft für Technologie und dem
            Wunsch, moderne KI-Konzepte praktisch zu erproben. Es läuft auf
            einem privaten Server. Die verwendeten KI-Modelle sind Open Source,
            die Fahrplandaten kommen von öffentlichen APIs &mdash; der Anwendungscode
            selbst steht derzeit noch nicht unter einer freien Lizenz. Dieses
            Projekt ist ein Lernprojekt &mdash; kein Startup, kein Produkt, kein Service.
          </p>

          <h2 className="text-xl font-bold text-white mt-8">Status &amp; Haftung</h2>
          <p>
            TransitAI ist ein <strong className="text-white">privates,
            nicht-kommerzielles Lern- und Demonstrationsprojekt</strong> im
            Testbetrieb. Es besteht kein Anspruch auf Verfügbarkeit, Richtigkeit
            oder dauerhaften Betrieb. Für die angezeigte Verbindungs- und
            Preisinformationen übernehmen wir keine Gewähr &mdash; diese werden
            in Echtzeit von Drittsystemen bezogen.
          </p>
          <p className="text-sm text-muted mt-2">
            Das Projekt ist beim{' '}
            <a
              href="https://developers.deutschebahn.com/"
              target="_blank"
              rel="noopener noreferrer nofollow"
              className="text-accent hover:underline"
            >DB API Marketplace</a>{' '}
            als Anwendung registriert. Es besteht keine geschäftliche oder
            offizielle Verbindung zur Deutschen Bahn AG. &quot;Deutsche Bahn&quot;
            und &quot;DB&quot; sind eingetragene Marken der Deutsche Bahn AG und
            werden hier ausschließlich zur deskriptiven Quellenangabe gemäß
            §&thinsp;23 MarkenG verwendet.
          </p>

          <div className="mt-12 pt-8 border-t border-white/10 space-y-2">
            <p className="text-muted text-sm">
              Anbieter: Sebastian Islamyar &middot; Frankfurt am Main
            </p>
            <p className="text-muted text-sm">
              Mehr Informationen im{' '}
              <a href="/impressum" className="text-accent hover:underline">Impressum</a>
              {' '}und in der{' '}
              <a href="/datenschutz" className="text-accent hover:underline">Datenschutzerklärung</a>.
            </p>
          </div>
        </div>
      </div>
    </main>
  )
}
