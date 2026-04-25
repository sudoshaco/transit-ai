import { ReactNode } from 'react'

interface CardProps {
  children: ReactNode
  className?: string
  highlight?: boolean
}

export default function Card({ children, className = '', highlight = false }: CardProps) {
  return (
    <div
      className={`
        rounded-2xl border p-6
        ${highlight
          ? 'border-accent/30 bg-accent/5'
          : 'border-white/10 bg-white/5'
        }
        backdrop-blur-sm
        ${className}
      `}
    >
      {children}
    </div>
  )
}
