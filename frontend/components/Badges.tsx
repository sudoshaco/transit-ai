'use client'

import { Badge, TONE_CLASSES, computeBadges } from '@/lib/badges'

interface Props {
  joined: string
  karma: number
  comment_count: number
  username?: string | null
  size?: 'sm' | 'md'
  max?: number
}

export default function Badges(props: Props) {
  const badges = computeBadges(props)
  const list = props.max ? badges.slice(0, props.max) : badges
  const textSize = props.size === 'sm' ? 'text-[10px]' : 'text-xs'
  const pad = props.size === 'sm' ? 'px-2 py-0.5' : 'px-2.5 py-1'

  if (!list.length) return null

  return (
    <div className="flex flex-wrap gap-1.5">
      {list.map((b) => <BadgePill key={b.id} badge={b} textSize={textSize} pad={pad} />)}
    </div>
  )
}

function BadgePill({ badge, textSize, pad }: { badge: Badge; textSize: string; pad: string }) {
  return (
    <span
      title={badge.hint}
      className={`inline-flex items-center gap-1 rounded-full border font-semibold ${textSize} ${pad} ${TONE_CLASSES[badge.tone]}`}
    >
      <span aria-hidden="true" className="opacity-90">{badge.icon}</span>
      <span>{badge.label}</span>
    </span>
  )
}
