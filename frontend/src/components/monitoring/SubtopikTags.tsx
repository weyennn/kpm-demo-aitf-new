interface Props {
  tags: string[]
  activeTag: string
  onTagClick: (tag: string) => void
  loading?: boolean
}

export default function SubtopikTags({ tags, activeTag, onTagClick, loading }: Props) {
  return (
    <div className="bg-white border border-border rounded-xl px-4 py-3.5">
      <div className="text-[11px] font-bold uppercase tracking-wider text-text-muted mb-2">
        Sub-Topik Trending — klik untuk filter
      </div>
      {loading ? (
        <div className="h-6 animate-pulse bg-surface rounded" />
      ) : tags.length === 0 ? (
        <div className="text-[12px] text-text-muted font-mono">Belum ada data</div>
      ) : (
        <div className="flex flex-wrap gap-1.5">
          {tags.map(tag => (
            <button
              key={tag}
              onClick={() => onTagClick(tag === activeTag ? '' : tag)}
              className={`px-2.5 py-1 rounded border text-[11px] font-mono cursor-pointer transition-all ${
                activeTag === tag
                  ? 'bg-primary-dim text-primary border-primary/40'
                  : 'bg-surface border-border text-text-muted hover:border-text-muted hover:text-text-main'
              }`}
            >
              {tag}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
