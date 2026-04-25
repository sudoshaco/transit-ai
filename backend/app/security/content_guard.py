"""
Prompt-Injection- und Illegal-Content-Schutz.

Zwei Stufen:
  1. HARD DENY  — Kategorien die nie erlaubt sind (Waffen, harte Drogen,
     Hacking-Angriffe, CSAM, Doxing, Terror). → 403 + AbuseEvent
  2. PROMPT-INJECTION — bekannte Jailbreak-Muster ("ignore previous",
     "system prompt", "du bist jetzt", DAN, base64 encoded instructions…).
     → Input wird neutralisiert (Delimiter-Escape) + AbuseEvent geloggt.
  3. OFF-TOPIC — Anfrage hat nichts mit ÖPNV/Reise zu tun. Wird höflich
     abgelehnt, nicht geloggt.

Die Regex-Listen sind bewusst konservativ. Zero false positives sind
unmöglich — wir bevorzugen Recall bei HARD DENY und Precision bei
PROMPT-INJECTION.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import List, Optional


MAX_INPUT_CHARS = 2000


# --- HARD DENY -------------------------------------------------------------
# Themen die wir strikt ablehnen. Ein einziges Match → Block.
_DENY_RULES: list[tuple[str, str, int, re.Pattern]] = []

def _add_rule(category: str, name: str, severity: int, pattern: str):
    _DENY_RULES.append((category, name, severity, re.compile(pattern, re.IGNORECASE)))

# Waffen / Sprengstoff
_add_rule("weapons", "firearm_build", 5, r"\b(bau(e|en)?|bastel|selbst ?bau|3d ?druck|schiess).{0,40}(waffe|pistole|gewehr|schusswaffe)")
_add_rule("weapons", "explosive", 5, r"\b(bombe|sprengstoff|tnt|c4|nitro|rohrbombe|bau(e|en)?.{0,20}(explosiv|bombe))")
_add_rule("weapons", "ied", 5, r"\b(improvised|usbv|nagelbombe|molotov|brandsatz)")

# Drogen (Herstellung/Synthese – Konsumberatung bleibt erlaubt)
_add_rule("illegal_drugs", "synth", 5, r"\b(synthetisier|herstell(en|ung)|koch(en|rezept)).{0,40}(meth|crystal|mdma|kokain|heroin|lsd|fentanyl|amphetamin)")
_add_rule("illegal_drugs", "precursor", 4, r"\b(precursor|vorstufe).{0,30}(meth|mdma|amphetamin|fentanyl)")

# Hacking / Angriffe (defensiv/Pentest via Opt-in; hier Produktumfeld → deny)
_add_rule("hacking", "attack_generic", 4, r"\b(hack(e|en)?|angreif|exploit|ddos|sql ?injection|rce|reverse ?shell).{0,40}(server|system|website|netzwerk|account|konto|db|datenbank)")
_add_rule("hacking", "credential_theft", 5, r"\b(passwort|credential|session).{0,30}(knack|steh(l|l)|dump|leak|bruteforce)")
_add_rule("hacking", "malware", 5, r"\b(schreib|erstell|bau).{0,30}(malware|virus|trojaner|ransomware|keylogger|rootkit|stealer)")

# CSAM – Zero Tolerance
_add_rule("csam", "minor_sexual", 5, r"\b(kind|minderjährig|minor|teen).{0,40}(sex|nackt|porno|nude)")
_add_rule("csam", "minor_sexual2", 5, r"\b(cp|csam|lolita)\b")

# Doxing / Stalking
_add_rule("doxing", "find_person", 3, r"\b(finde|ermittle|dox|track(e|ing)|aufspür|adresse von|wohnort von).{0,40}(person|frau|mann|freundin|freund|ex)")

# Terror / Extremismus
_add_rule("terror", "attack_planning", 5, r"\b(anschlag|attentat|terror).{0,40}(plan|durchführ|vorbereit)")
_add_rule("terror", "radicalization", 4, r"\b(wie werde ich|werde) (dschihadist|terrorist|extremist)")

# Selbstverletzung / Suizid (soft handling statt hartem Block, aber loggen)
_add_rule("self_harm", "suicide_method", 3, r"\b(wie).{0,10}(bring(e|en)? ich mich um|suizid|selbstmord).{0,40}(methode|anleitung)")


# --- PROMPT INJECTION ------------------------------------------------------
_INJECTION_PATTERNS = [
    (r"ignor(e|ier) (all|alle|previous|vorherige|bisherige) (instruction|anweisung|prompt|regel)", "ignore_prev"),
    (r"vergiss (alles|alle anweisungen|deine regeln|den system prompt)", "forget_rules"),
    (r"(you are|du bist) (now|jetzt) (a|ein|eine) (?!transit|reiseassist|bahn)", "role_switch"),
    (r"(act|agier|verhalt) (as|als) (dan|jailbreak|developer ?mode|unrestricted|ohne filter|ohne regeln)", "jailbreak_persona"),
    (r"(system ?prompt|deine anweisungen|initial prompt|deine regeln).{0,20}(zeig|gib|nenn|print|reveal|leak)", "reveal_sysprompt"),
    (r"</?(system|assistant|user|instruction)>", "role_tag_inject"),
    (r"```\s*system", "md_system_fence"),
    (r"\\n\\n(system|user|assistant):", "fake_chat_turn"),
    (r"base64:?\s*[A-Za-z0-9+/=]{40,}", "base64_blob"),
    (r"(do ?anything ?now|dan mode|no restriction|no filter|no ethics)", "dan"),
    (r"pretend (you have|to have) no (rules|restriction|guideline)", "pretend_no_rules"),
]
_INJECTION_RE = [(re.compile(p, re.IGNORECASE | re.DOTALL), name) for p, name in _INJECTION_PATTERNS]


# --- OFF-TOPIC (Themen-Whitelist, weich) -----------------------------------
_ONTOPIC_HINTS = re.compile(
    r"\b(bahn|zug|ice|ic|re|rb|s-?bahn|u-?bahn|tram|bus|fähre|fahrt|fahrplan|verbindung|"
    r"haltestelle|bahnhof|gleis|abfahrt|ankunft|ticket|bahncard|deutschland ?ticket|"
    r"verspätung|streik|umstieg|anreise|reise|route|strecke|rmv|vrr|mvv|bvg|hvv|"
    r"von\s+\w+\s+nach|uhr|morgen|heute|nächste|letzte)\b",
    re.IGNORECASE,
)


@dataclass
class GuardResult:
    allowed: bool
    hard_block: bool
    category: Optional[str]
    severity: int
    matched_rules: List[str]
    sanitized: str
    is_off_topic: bool
    payload_hash: str
    excerpt: str


def _fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def _neutralize(text: str) -> str:
    """Entferne Zeichen die als Rollen-/Instruktions-Delimiter missbraucht werden."""
    out = text.replace("\u202e", "").replace("\u202d", "")  # RTL/LTR overrides
    out = re.sub(r"</?(system|assistant|user|instruction)[^>]*>", "", out, flags=re.IGNORECASE)
    out = re.sub(r"```\s*(system|instruction)[^\n]*\n", "```\n", out, flags=re.IGNORECASE)
    out = re.sub(r"(?im)^\s*(system|assistant|user)\s*:\s*", "", out)
    return out.strip()


def inspect(text: str) -> GuardResult:
    raw = (text or "").strip()
    if len(raw) > MAX_INPUT_CHARS:
        raw = raw[:MAX_INPUT_CHARS]

    excerpt = raw[:500]
    fp = _fingerprint(raw)

    # 1) HARD DENY
    matched: list[str] = []
    worst = 0
    worst_cat: Optional[str] = None
    for category, name, severity, pattern in _DENY_RULES:
        if pattern.search(raw):
            matched.append(f"{category}:{name}")
            if severity > worst:
                worst = severity
                worst_cat = category

    if worst >= 4:
        return GuardResult(
            allowed=False,
            hard_block=True,
            category=worst_cat,
            severity=worst,
            matched_rules=matched,
            sanitized="",
            is_off_topic=False,
            payload_hash=fp,
            excerpt=excerpt,
        )

    # 2) PROMPT INJECTION
    injection_hits: list[str] = []
    for pattern, name in _INJECTION_RE:
        if pattern.search(raw):
            injection_hits.append(f"prompt_injection:{name}")

    sanitized = _neutralize(raw) if injection_hits else raw

    # 3) OFF-TOPIC
    off_topic = not _ONTOPIC_HINTS.search(raw.lower()) and len(raw) > 8

    severity = 3 if injection_hits else (worst if matched else 0)
    category = "prompt_injection" if injection_hits else (worst_cat if matched else None)
    allow = not injection_hits or len(injection_hits) < 2  # 2+ gleichzeitig → deny
    # Wenn prompt injection UND off-topic → harter Block
    hard = bool(injection_hits) and off_topic

    return GuardResult(
        allowed=allow and not hard,
        hard_block=hard,
        category=category,
        severity=severity,
        matched_rules=matched + injection_hits,
        sanitized=sanitized,
        is_off_topic=off_topic,
        payload_hash=fp,
        excerpt=excerpt,
    )
