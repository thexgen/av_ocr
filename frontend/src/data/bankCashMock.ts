export type EntityOption = {
  id: string
  name: string
  accounts: { id: string; label: string }[]
}

export type LedgerRow = {
  id: string
  entityId: string
  entityName: string
  accountId: string
  accountLabel: string
  tradeDate: string
  type: 'Credit' | 'Debit'
  description: string
  checkNo: string
  amount: number
  balance: number
}

/** Dev filter IDs match DEFAULT_ENTITY_ID / DEFAULT_ACCOUNT_ID in the backend. */
export const ENTITIES: EntityOption[] = [
  {
    id: '1',
    name: 'Krishna Deval',
    accounts: [{ id: '101', label: 'Account · 101' }],
  },
]

/** Dummy posted ledger rows for Bank Cash → Ledger tab */
export const MOCK_LEDGER: LedgerRow[] = [
  {
    id: 'led-001',
    entityId: 'ent-1',
    entityName: 'Krishna Deval',
    accountId: 'acc-kd-1',
    accountLabel: 'HDFC · ****3343 Savings',
    tradeDate: '2026-06-28',
    type: 'Credit',
    description: 'NEFT IN — Mutual fund redemption',
    checkNo: 'NEFT882910',
    amount: 425000,
    balance: 1284560.42,
  },
  {
    id: 'led-002',
    entityId: 'ent-1',
    entityName: 'Krishna Deval',
    accountId: 'acc-kd-1',
    accountLabel: 'HDFC · ****3343 Savings',
    tradeDate: '2026-06-27',
    type: 'Debit',
    description: 'RTGS OUT — Advisory fee',
    checkNo: 'RTGS44102',
    amount: -85000,
    balance: 859560.42,
  },
  {
    id: 'led-003',
    entityId: 'ent-1',
    entityName: 'Krishna Deval',
    accountId: 'acc-kd-2',
    accountLabel: 'ICICI · ****9066 Current',
    tradeDate: '2026-06-26',
    type: 'Debit',
    description: 'Vendor payout — Eragon Ventures',
    checkNo: 'CHQ10442',
    amount: -226200,
    balance: 790529.0,
  },
  {
    id: 'led-004',
    entityId: 'ent-1',
    entityName: 'Krishna Deval',
    accountId: 'acc-kd-2',
    accountLabel: 'ICICI · ****9066 Current',
    tradeDate: '2026-06-25',
    type: 'Credit',
    description: 'IMPS IN — Client receipt',
    checkNo: 'IMPS99012',
    amount: 150000,
    balance: 1016729.0,
  },
  {
    id: 'led-005',
    entityId: 'ent-2',
    entityName: 'Aryan Dev',
    accountId: 'acc-ad-1',
    accountLabel: 'Kotak · ****8821 Savings',
    tradeDate: '2026-06-24',
    type: 'Credit',
    description: 'Salary credit — Jun 2026',
    checkNo: 'SAL0626',
    amount: 275000,
    balance: 612440.15,
  },
  {
    id: 'led-006',
    entityId: 'ent-2',
    entityName: 'Aryan Dev',
    accountId: 'acc-ad-1',
    accountLabel: 'Kotak · ****8821 Savings',
    tradeDate: '2026-06-23',
    type: 'Debit',
    description: 'UPI — Rent transfer',
    checkNo: 'UPI7721',
    amount: -65000,
    balance: 337440.15,
  },
  {
    id: 'led-007',
    entityId: 'ent-2',
    entityName: 'Aryan Dev',
    accountId: 'acc-ad-2',
    accountLabel: 'Axis · ****4410 Salary',
    tradeDate: '2026-06-22',
    type: 'Debit',
    description: 'Card settlement sweep',
    checkNo: 'SWEEP09',
    amount: -18450.75,
    balance: 90220.5,
  },
  {
    id: 'led-008',
    entityId: 'ent-3',
    entityName: 'Jessy Deval',
    accountId: 'acc-jd-1',
    accountLabel: 'SBI · ****2290 Savings',
    tradeDate: '2026-06-21',
    type: 'Credit',
    description: 'Dividend credit — Equity portfolio',
    checkNo: 'DIV1188',
    amount: 12480.5,
    balance: 448920.8,
  },
  {
    id: 'led-009',
    entityId: 'ent-3',
    entityName: 'Jessy Deval',
    accountId: 'acc-jd-1',
    accountLabel: 'SBI · ****2290 Savings',
    tradeDate: '2026-06-20',
    type: 'Debit',
    description: 'SIP — Index fund',
    checkNo: 'SIP4401',
    amount: -25000,
    balance: 436440.3,
  },
  {
    id: 'led-010',
    entityId: 'ent-3',
    entityName: 'Jessy Deval',
    accountId: 'acc-jd-2',
    accountLabel: 'Yes Bank · ****1188 Current',
    tradeDate: '2026-06-19',
    type: 'Credit',
    description: 'NEFT IN — Consulting invoice',
    checkNo: 'NEFT2201',
    amount: 180000,
    balance: 522110.0,
  },
  {
    id: 'led-011',
    entityId: 'ent-1',
    entityName: 'Krishna Deval',
    accountId: 'acc-kd-1',
    accountLabel: 'HDFC · ****3343 Savings',
    tradeDate: '2026-06-18',
    type: 'Credit',
    description: 'Interest credit — Q1',
    checkNo: 'INTQ1',
    amount: 278262,
    balance: 944560.42,
  },
  {
    id: 'led-012',
    entityId: 'ent-2',
    entityName: 'Aryan Dev',
    accountId: 'acc-ad-1',
    accountLabel: 'Kotak · ****8821 Savings',
    tradeDate: '2026-06-17',
    type: 'Debit',
    description: 'FD booking',
    checkNo: 'FD8821',
    amount: -200000,
    balance: 402440.15,
  },
]
