import { Coins } from 'lucide-react'
import { MOCK_FI_LEDGER } from '../data/vehicleMock'
import { InvestmentVehiclePage } from './InvestmentVehicle'

export function FixedIncomePage() {
  return (
    <InvestmentVehiclePage
      vehicle="fixed-income"
      title="Fixed Income"
      description="Posted ledger view and statement upload staging for bonds, FDs, and other fixed income."
      icon={Coins}
      layoutId="fixed-income-tab"
      ledgerRows={MOCK_FI_LEDGER}
    />
  )
}
