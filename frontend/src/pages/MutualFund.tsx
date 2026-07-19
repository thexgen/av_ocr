import { PieChart } from 'lucide-react'
import { MOCK_MF_LEDGER } from '../data/vehicleMock'
import { InvestmentVehiclePage } from './InvestmentVehicle'

export function MutualFundPage() {
  return (
    <InvestmentVehiclePage
      vehicle="mutual-fund"
      title="Mutual Fund"
      description="Posted ledger view and statement upload staging for mutual fund holdings."
      icon={PieChart}
      layoutId="mutual-fund-tab"
      ledgerRows={MOCK_MF_LEDGER}
    />
  )
}
