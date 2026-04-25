interface LoaderProps {
  text?: string
  size?: 'sm' | 'md' | 'lg'
}

export default function Loader({ text = 'Suche Verbindungen...', size = 'md' }: LoaderProps) {
  const sizes = {
    sm: 'h-6 w-6',
    md: 'h-10 w-10',
    lg: 'h-16 w-16',
  }

  return (
    <div className="flex flex-col items-center justify-center gap-4 py-12">
      <div className={`${sizes[size]} relative`}>
        <div className="absolute inset-0 rounded-full border-2 border-accent/20" />
        <div className="absolute inset-0 rounded-full border-2 border-transparent border-t-accent animate-spin" />
      </div>
      {text && <p className="text-muted text-sm animate-pulse">{text}</p>}
    </div>
  )
}
