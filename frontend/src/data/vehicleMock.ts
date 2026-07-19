import { ENTITIES, type EntityOption } from './bankCashMock'

export type VehicleKey = 'mutual-fund' | 'fixed-income' | 'direct-equity'

export type VehicleLedgerRow = {
  id: string
  entityId: string
  entityName: string
  folioOrIsin: string
  tradeDate: string
  type: string
  schemeOrInstrument: string
  units: number
  navOrPrice: number
  amount: number
}

export const VEHICLE_ENTITIES: EntityOption[] = ENTITIES

export const MOCK_MF_LEDGER: VehicleLedgerRow[] = [
  {
    id: 'mf-001',
    entityId: 'ent-1',
    entityName: 'Krishna Deval',
    folioOrIsin: 'INF209K01XT3',
    tradeDate: '2026-06-28',
    type: 'Purchase',
    schemeOrInstrument: 'Parag Parikh Flexi Cap',
    units: 412.334,
    navOrPrice: 84.52,
    amount: 34850,
  },
  {
    id: 'mf-002',
    entityId: 'ent-1',
    entityName: 'Krishna Deval',
    folioOrIsin: 'INF179K01YV8',
    tradeDate: '2026-06-25',
    type: 'SIP',
    schemeOrInstrument: 'HDFC Mid-Cap Opportunities',
    units: 18.22,
    navOrPrice: 137.2,
    amount: 2500,
  },
  {
    id: 'mf-003',
    entityId: 'ent-2',
    entityName: 'Aryan Dev',
    folioOrIsin: 'INF090I01239',
    tradeDate: '2026-06-22',
    type: 'Redemption',
    schemeOrInstrument: 'Axis Liquid Fund',
    units: -120.5,
    navOrPrice: 2450.1,
    amount: -295187.05,
  },
  {
    id: 'mf-004',
    entityId: 'ent-3',
    entityName: 'Jessy Deval',
    folioOrIsin: 'INF204KB1V68',
    tradeDate: '2026-06-20',
    type: 'Dividend',
    schemeOrInstrument: 'Nippon India Small Cap',
    units: 0,
    navOrPrice: 156.4,
    amount: 4200,
  },
  {
    id: 'mf-005',
    entityId: 'ent-2',
    entityName: 'Aryan Dev',
    folioOrIsin: 'INF846K01EW2',
    tradeDate: '2026-06-18',
    type: 'Switch In',
    schemeOrInstrument: 'Mirae Asset Large Cap',
    units: 95.12,
    navOrPrice: 98.4,
    amount: 9360,
  },
  {
    id: 'mf-006',
    entityId: 'ent-1',
    entityName: 'Krishna Deval',
    folioOrIsin: 'INF174K01LS2',
    tradeDate: '2026-06-15',
    type: 'Purchase',
    schemeOrInstrument: 'ICICI Pru Equity & Debt',
    units: 210.05,
    navOrPrice: 312.8,
    amount: 65703.64,
  },
]

export const MOCK_DE_LEDGER: VehicleLedgerRow[] = [
  {
    id: 'de-001',
    entityId: 'ent-1',
    entityName: 'Krishna Deval',
    folioOrIsin: 'INE002A01018',
    tradeDate: '2026-06-26',
    type: 'Buy',
    schemeOrInstrument: 'Reliance Industries',
    units: 40,
    navOrPrice: 2890.5,
    amount: 115620,
  },
  {
    id: 'de-002',
    entityId: 'ent-2',
    entityName: 'Aryan Dev',
    folioOrIsin: 'INE467B01029',
    tradeDate: '2026-06-20',
    type: 'Sell',
    schemeOrInstrument: 'TCS',
    units: -15,
    navOrPrice: 3920,
    amount: -58800,
  },
]

export const MOCK_FI_LEDGER: VehicleLedgerRow[] = [
  {
    id: 'fi-001',
    entityId: 'ent-1',
    entityName: 'Krishna Deval',
    folioOrIsin: 'IN002023Y123',
    tradeDate: '2026-06-27',
    type: 'Coupon',
    schemeOrInstrument: '7.26% GS 2033',
    units: 100,
    navOrPrice: 102.15,
    amount: 36300,
  },
  {
    id: 'fi-002',
    entityId: 'ent-1',
    entityName: 'Krishna Deval',
    folioOrIsin: 'INE001A07ABC',
    tradeDate: '2026-06-24',
    type: 'Buy',
    schemeOrInstrument: 'HDFC Bank NCD 8.4%',
    units: 50,
    navOrPrice: 1000,
    amount: 50000,
  },
  {
    id: 'fi-003',
    entityId: 'ent-2',
    entityName: 'Aryan Dev',
    folioOrIsin: 'FD-KTK-8821',
    tradeDate: '2026-06-21',
    type: 'FD Booking',
    schemeOrInstrument: 'Kotak FD 7.1% · 24M',
    units: 1,
    navOrPrice: 200000,
    amount: 200000,
  },
  {
    id: 'fi-004',
    entityId: 'ent-3',
    entityName: 'Jessy Deval',
    folioOrIsin: 'IN002024Z045',
    tradeDate: '2026-06-19',
    type: 'Sell',
    schemeOrInstrument: 'T-Bill 91D',
    units: -25,
    navOrPrice: 98.6,
    amount: -24650,
  },
  {
    id: 'fi-005',
    entityId: 'ent-2',
    entityName: 'Aryan Dev',
    folioOrIsin: 'INE002A08XYZ',
    tradeDate: '2026-06-16',
    type: 'Maturity',
    schemeOrInstrument: 'SBI Corp Bond 7.8%',
    units: -40,
    navOrPrice: 1000,
    amount: 40000,
  },
  {
    id: 'fi-006',
    entityId: 'ent-3',
    entityName: 'Jessy Deval',
    folioOrIsin: 'FD-SBI-2290',
    tradeDate: '2026-06-14',
    type: 'Interest',
    schemeOrInstrument: 'SBI FD 6.8% · 12M',
    units: 1,
    navOrPrice: 500000,
    amount: 8500,
  },
]
