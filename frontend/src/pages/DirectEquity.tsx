import { TrendingUp } from 'lucide-react'
import { MOCK_DE_LEDGER } from '../data/vehicleMock'
import { InvestmentVehiclePage } from './InvestmentVehicle'

export function DirectEquityPage() {
  return (
    <InvestmentVehiclePage
      vehicle="direct-equity"
      title="Direct Equity"
      description="Posted ledger view and statement upload staging for equity trades."
      icon={TrendingUp}
      layoutId="direct-equity-tab"
      ledgerRows={MOCK_DE_LEDGER}
    />
  )
}
