import type { Metadata, Viewport } from 'next'
import './globals.css'
import VisitCounter from '@/components/Stats/VisitCounter'
import AuthNav from '@/components/auth/AuthNav'

export const metadata: Metadata = {
  title: 'TransitAI — KI-Reiseplaner für Bahn & ÖPNV in Deutschland',
  description:
    'TransitAI ist ein KI-gestützter Reiseplaner für Bahn, Bus und Nahverkehr in Deutschland. Natürliche Sprache, echte Fahrpläne, schnelle Ergebnisse.',
  keywords: [
    'Bahn', 'ÖPNV', 'Fahrplan', 'Deutsche Bahn', 'DB', 'Reiseplaner', 'KI-Reiseplaner',
    'Nahverkehr', 'Transit', 'Reise', 'Zugverbindung', 'ICE', 'IC', 'RE', 'RB', 'S-Bahn',
    'Reiseauskunft', 'Bahnauskunft', 'Fahrplanauskunft', 'Verbindungssuche', 'Reiseassistent',
    'Bahn-KI', 'natürliche Sprache', 'Sprachsuche', 'RMV', 'VRR', 'MVV', 'HVV', 'VBB', 'BVG',
    'Deutschlandticket', 'Zugfahrplan', 'Bahnverbindung', 'Zugticket', 'günstig Bahn fahren',
    'Reiseplanung Deutschland', 'Ankunftszeit', 'Abfahrtszeit', 'Umstieg', 'DSGVO', 'Open Source LLM',
  ],
  alternates: { canonical: '/' },
  category: 'Travel',
  authors: [{ name: 'TransitAI' }],
  manifest: '/manifest.json',
  icons: {
    icon: [{ url: '/favicon.svg', type: 'image/svg+xml' }],
    apple: '/favicon.svg',
  },
  openGraph: {
    title: 'TransitAI — KI-Reiseplaner',
    description: 'Beschreibe deine Reise in natürlicher Sprache — TransitAI findet die beste Verbindung.',
    locale: 'de_DE',
    type: 'website',
  },
  robots: { index: true, follow: true },
}

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  themeColor: '#0a0a0f',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="de">
      <body className="antialiased flex flex-col min-h-screen pt-14">
        <AuthNav />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              '@context': 'https://schema.org',
              '@type': 'WebApplication',
              name: 'TransitAI',
              description: 'KI-gestützter Reiseplaner für Bahn, Bus und Nahverkehr in Deutschland. Natürliche Sprache, echte Fahrpläne.',
              applicationCategory: 'TravelApplication',
              operatingSystem: 'Any',
              inLanguage: 'de-DE',
              offers: { '@type': 'Offer', price: '0', priceCurrency: 'EUR' },
              featureList: [
                'Natürlichsprachliche Reiseplanung',
                'Hin- und Rückfahrt in einer Anfrage',
                'Ankunftszeit-Optimierung',
                'Echte Fahrplandaten (Deutsche Bahn)',
                'Open-Source KI-Modelle',
                'DSGVO-konform'
              ],
            }),
          }}
        />

        <div className="flex-1">{children}</div>

        <footer className="border-t border-white/10 bg-background/80 backdrop-blur">
          <div className="max-w-5xl mx-auto px-4 py-6 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-muted">
            <div className="flex items-center gap-2">
              <span>
                Transit<span className="text-accent font-semibold">AI</span>
              </span>
              <span className="hidden sm:inline">&middot;</span>
              <VisitCounter />
            </div>

            <nav className="flex items-center gap-5">
              <a href="/account" className="hover:text-white transition-colors">Account</a>
              <a href="/login" className="hover:text-white transition-colors">Login</a>
              <a href="/register" className="hover:text-white transition-colors">Registrieren</a>
              <a href="/about" className="hover:text-white transition-colors">Über uns</a>
              <a href="/impressum" className="hover:text-white transition-colors">Impressum</a>
              <a href="/datenschutz" className="hover:text-white transition-colors">Datenschutz</a>
            </nav>
          </div>
          <div className="max-w-5xl mx-auto px-4 pb-4 text-[11px] text-muted/70 text-center sm:text-left">
            Daten: offizielle Bahn-Schnittstellen &middot; Lokale KI &middot; DSGVO-konform
          </div>
        </footer>
      </body>
    </html>
  )
}
