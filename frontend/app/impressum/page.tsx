import { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Impressum — TransitAI',
  description: 'Anbieterkennzeichnung gemäß § 5 TMG / § 5 DDG',
  robots: { index: true, follow: false },
}

export default function ImpressumPage() {
  return (
    <main className="min-h-screen bg-background px-4 py-16">
      <div className="max-w-2xl mx-auto">
        <a href="/" className="text-muted hover:text-white transition-colors text-sm mb-8 block">
          &larr; Zurück
        </a>

        <h1 className="text-4xl font-bold text-white mb-8 font-headline">Impressum</h1>

        <div className="space-y-6 text-gray-300 leading-relaxed">
          <section>
            <h2 className="text-xl font-bold text-white mb-2">
              Angaben gemäß §&thinsp;5 DDG (ehemals TMG)
            </h2>
            <p>
              Sebastian Islamyar<br />
              Kelsterbacherstraße 14<br />
              60528 Frankfurt am Main<br />
              Deutschland
            </p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-white mb-2">Kontakt</h2>
            <p>
              E-Mail:{' '}
              <a
                href="mailto:kontakt@sebastian-netzwerke.de"
                className="text-accent hover:underline"
              >
                kontakt@sebastian-netzwerke.de
              </a>
            </p>
            <p className="mt-2">
              Postalisch erreichbar unter der oben genannten Anschrift.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-white mb-2">
              Verantwortlich für den Inhalt nach §&thinsp;18 Abs.&thinsp;2 MStV
            </h2>
            <p>
              Sebastian Islamyar (Anschrift wie oben)
            </p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-white mb-2">
              Art des Angebots
            </h2>
            <p>
              TransitAI ist ein <strong className="text-white">privates,
              nicht-kommerzielles Lern- und Forschungsprojekt</strong> ohne
              Gewinnerzielungsabsicht. Es handelt sich um einen Proof-of-Concept
              zur Erprobung KI-gestützter Reiseplanung auf Basis offizieller
              Fahrplandaten und quelloffener Sprachmodelle.
            </p>
            <p className="mt-2">
              Das Projekt nutzt die offiziellen APIs des{' '}
              <a
                href="https://developers.deutschebahn.com/"
                target="_blank"
                rel="noopener noreferrer nofollow"
                className="text-accent hover:underline"
              >
                DB API Marketplace (developers.deutschebahn.com)
              </a>
              {' '}und ist dort als Anwendung registriert. Die Nutzung erfolgt
              im Rahmen der dort hinterlegten Nutzungsbedingungen.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-white mb-2">
              KI-Transparenzhinweis
            </h2>
            <p>
              Diese Webseite setzt <strong className="text-white">Künstliche
              Intelligenz</strong> zur Verarbeitung natürlichsprachlicher
              Eingaben und zur Zusammenfassung von Suchergebnissen ein.
              Konkret werden folgende Systeme verwendet:
            </p>
            <ul className="list-disc list-inside mt-2 space-y-1">
              <li>
                <strong className="text-white">Groq Cloud API</strong> mit dem
                Open-Source-Modell Llama 3.1 8B Instant (Meta, Apache 2.0) &mdash;
                primärer Provider für Reasoning und Zusammenfassung
              </li>
              <li>
                <strong className="text-white">Ollama (Self-Hosted)</strong> mit
                dem Open-Source-Modell Qwen 2.5 7B (Alibaba Cloud, Apache 2.0) &mdash;
                lokaler Fallback-Provider auf eigenem Server in Deutschland
              </li>
            </ul>
            <p className="mt-2">
              Die KI-generierten Texte (z.&thinsp;B. die &quot;KI-Zusammenfassung&quot;
              auf der Ergebnisseite) werden als solche gekennzeichnet. Diese
              Texte können Ungenauigkeiten enthalten und stellen keine
              verbindliche Reiseauskunft dar. Die eigentlichen Verbindungs- und
              Fahrplandaten stammen aus offiziellen Datenquellen.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-white mb-2">
              Marken- und Urheberrechtshinweis
            </h2>
            <p>
              &quot;Deutsche Bahn&quot;, &quot;DB&quot; und zugehörige Logos sind
              eingetragene Marken der Deutsche Bahn AG. Ihre Nennung auf dieser
              Seite erfolgt ausschließlich zur deskriptiven Quellenangabe im
              Rahmen des §&thinsp;23 MarkenG (beschreibende Benutzung) und
              impliziert keine Geschäftsbeziehung, Lizenzierung oder
              Unterstützung durch die Markeninhaber.
            </p>
            <p className="mt-2">
              <strong className="text-white">Es besteht keine geschäftliche
              oder offizielle Verbindung zur Deutschen Bahn AG.</strong>{' '}
              TransitAI ist ein unabhängiges Drittanbieter-Projekt, das die
              öffentlich verfügbaren API-Dienste konsumiert.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-white mb-2">
              Haftungsausschluss
            </h2>
            <p>
              <strong className="text-white">Haftung für Inhalte:</strong>{' '}
              Die Inhalte dieser Seite wurden mit größter Sorgfalt erstellt.
              Für die Richtigkeit, Vollständigkeit und Aktualität der
              angezeigten Verbindungs-, Fahrplan- und Preisdaten kann jedoch
              keine Gewähr übernommen werden, da diese in Echtzeit von
              Drittsystemen bezogen und teilweise durch KI-Modelle
              zusammengefasst werden. Eine Haftung für Schäden, die aus der
              Nutzung oder Nichtnutzung der angebotenen Informationen entstehen,
              ist ausgeschlossen, soweit gesetzlich zulässig.
            </p>
            <p className="mt-2">
              Als Diensteanbieter sind wir gemäß §&thinsp;7 Abs.&thinsp;1 DDG
              für eigene Inhalte auf diesen Seiten nach den allgemeinen Gesetzen
              verantwortlich. Nach §§&thinsp;8 bis 10 DDG sind wir als
              Diensteanbieter jedoch nicht verpflichtet, übermittelte oder
              gespeicherte fremde Informationen zu überwachen.
            </p>
            <p className="mt-2">
              <strong className="text-white">Haftung für Links:</strong>{' '}
              Unser Angebot enthält Links zu externen Webseiten Dritter, auf
              deren Inhalte wir keinen Einfluss haben. Für die Inhalte der
              verlinkten Seiten ist stets der jeweilige Anbieter oder Betreiber
              verantwortlich.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-white mb-2">
              Hinweis zum Betrieb
            </h2>
            <p>
              Dieses Projekt wird als Lern- und Demonstrationsprojekt auf
              privater Infrastruktur betrieben. Es besteht kein Anspruch auf
              Verfügbarkeit, Richtigkeit der angezeigten Daten oder
              dauerhaften Betrieb. Verfügbarkeit und Funktionsumfang können
              sich jederzeit ohne Vorankündigung ändern.
            </p>
          </section>

          <section className="mt-12 pt-6 border-t border-white/10">
            <p className="text-muted text-sm">
              Stand: April 2026
            </p>
          </section>
        </div>
      </div>
    </main>
  )
}
