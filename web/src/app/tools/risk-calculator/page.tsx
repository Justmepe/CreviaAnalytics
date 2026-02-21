import RiskCalculator from '@/components/tools/RiskCalculator';

export const metadata = {
  title: 'Risk Calculator | Crevia Analytics',
  description: 'Context-aware position sizing calculator with market condition warnings.',
};

export default function RiskCalculatorPage() {
  return (
    <main className="min-h-screen bg-zinc-950">
      <section className="border-b border-zinc-800">
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
          <h1 className="text-2xl font-bold text-white mb-1">Risk Calculator</h1>
          <p className="text-sm text-zinc-500 mb-6">
            Position sizing with real-time market condition warnings.
          </p>
          <RiskCalculator />
        </div>
      </section>
    </main>
  );
}
