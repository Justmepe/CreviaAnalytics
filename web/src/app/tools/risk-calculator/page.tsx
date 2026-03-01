import RiskCalculator from '@/components/tools/RiskCalculator';
import CockpitShell from '@/components/layout/CockpitShell';

export const metadata = {
  title: 'Risk Calculator | CreviaCockpit',
  description: 'Context-aware position sizing calculator with market condition warnings.',
};

export default function RiskCalculatorPage() {
  return (
    <CockpitShell>
      <RiskCalculator />
    </CockpitShell>
  );
}
