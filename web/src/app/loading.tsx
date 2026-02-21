export default function GlobalLoading() {
  return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
      <div className="flex flex-col items-center gap-3">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500 font-bold text-zinc-950 text-sm animate-pulse">
          CA
        </div>
        <div className="text-sm text-zinc-600">Loading...</div>
      </div>
    </div>
  );
}
