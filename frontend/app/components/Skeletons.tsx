export function StatCardsSkeleton({ count = 6 }: { count?: number }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 xl:grid-cols-6 gap-6">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="bg-white rounded-3xl p-5 shadow-sm animate-pulse"
        >
          <div className="h-3 w-20 bg-slate-200 rounded mb-4" />
          <div className="h-8 w-14 bg-slate-200 rounded" />
        </div>
      ))}
    </div>
  );
}

export function UploadListSkeleton({ count = 5 }: { count?: number }) {
  return (
    <div className="space-y-4">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="flex items-center justify-between border rounded-2xl px-5 py-4 animate-pulse"
        >
          <div>
            <div className="h-4 w-40 bg-slate-200 rounded mb-2" />
            <div className="h-3 w-24 bg-slate-200 rounded" />
          </div>
          <div className="h-6 w-24 bg-slate-200 rounded-full" />
        </div>
      ))}
    </div>
  );
}

export function CardSkeleton({ className = "" }: { className?: string }) {
  return (
    <div
      className={`bg-white rounded-3xl p-6 shadow-sm animate-pulse ${className}`}
    >
      <div className="h-5 w-40 bg-slate-200 rounded mb-4" />
      <div className="h-4 w-full bg-slate-200 rounded mb-2" />
      <div className="h-4 w-3/4 bg-slate-200 rounded" />
    </div>
  );
}

export function ExcelListSkeleton({ count = 3 }: { count?: number }) {
  return (
    <div className="space-y-5">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="bg-white rounded-3xl shadow-sm p-6 flex flex-col md:flex-row md:items-center md:justify-between gap-4 animate-pulse"
        >
          <div className="space-y-2">
            <div className="h-5 w-56 bg-slate-200 rounded" />
            <div className="h-3 w-40 bg-slate-200 rounded" />
            <div className="h-3 w-64 bg-slate-200 rounded" />
          </div>
          <div className="h-5 w-32 bg-slate-200 rounded" />
        </div>
      ))}
    </div>
  );
}

export function FilterModalSkeleton() {
  return (
    <div className="space-y-4 animate-pulse">
      <div className="h-24 bg-slate-100 rounded-2xl" />
      <div className="h-40 bg-slate-100 rounded-2xl" />
      <div className="h-40 bg-slate-100 rounded-2xl" />
    </div>
  );
}

export function FilterSectionSkeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div className="space-y-3 animate-pulse">
      <div className="h-10 bg-slate-100 rounded-xl" />
      <div className="flex flex-wrap gap-2">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="h-8 w-24 bg-slate-100 rounded-full" />
        ))}
      </div>
      <div className="flex flex-wrap gap-2">
        {Array.from({ length: rows + 2 }).map((_, i) => (
          <div key={i} className="h-8 w-20 bg-slate-50 rounded-full" />
        ))}
      </div>
    </div>
  );
}
