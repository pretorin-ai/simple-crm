// Shared badge variant mappings for contacts, contracts, opportunities, etc.

export function getContactStatusBadge(status: string) {
  const variants = {
    cold: 'secondary',
    warm: 'default',
    hot: 'destructive',
  } as const;
  return variants[status as keyof typeof variants] || 'outline';
}

export function getContactTypeBadge(type: string) {
  const variants = {
    individual: 'default',
    government: 'secondary',
    commercial: 'outline',
  } as const;
  return variants[type as keyof typeof variants] || 'outline';
}

export function getContractStatusBadge(status: string) {
  const variants = {
    prospective: 'outline',
    'in progress': 'default',
    submitted: 'secondary',
    'not a good fit': 'destructive',
  } as const;
  return variants[status as keyof typeof variants] || 'outline';
}

export function getOpportunityStageBadge(stage: string) {
  const variants = {
    identified: 'outline',
    qualified: 'secondary',
    capture: 'default',
    teaming: 'default',
    proposal: 'default',
    submitted: 'secondary',
    awarded: 'default',
    lost: 'destructive',
  } as const;
  return variants[stage as keyof typeof variants] || 'outline';
}

export function getAccountTypeBadge(type: string) {
  const variants = {
    government_agency: 'secondary',
    prime_contractor: 'default',
    subcontractor: 'outline',
    partner: 'default',
    vendor: 'outline',
  } as const;
  return variants[type as keyof typeof variants] || 'outline';
}

export function getComplianceStatusBadge(status: string) {
  const variants = {
    active: 'default',
    expiring_soon: 'secondary',
    expired: 'destructive',
    pending: 'outline',
  } as const;
  return variants[status as keyof typeof variants] || 'outline';
}

export function getTeamingStatusBadge(status: string) {
  const variants = {
    potential: 'outline',
    nda_signed: 'secondary',
    teaming_agreed: 'default',
    active: 'default',
    inactive: 'destructive',
  } as const;
  return variants[status as keyof typeof variants] || 'outline';
}

export function getProposalStatusBadge(status: string) {
  const variants = {
    not_started: 'outline',
    in_progress: 'default',
    review: 'secondary',
    final: 'default',
    submitted: 'secondary',
  } as const;
  return variants[status as keyof typeof variants] || 'outline';
}

export function formatCurrency(value: number | undefined | null): string {
  if (value === undefined || value === null) return 'N/A';
  if (value >= 1_000_000_000) return `$${(value / 1_000_000_000).toFixed(1)}B`;
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(0)}K`;
  return `$${value.toLocaleString()}`;
}

export function formatAccountType(type: string): string {
  const labels: Record<string, string> = {
    government_agency: 'Government Agency',
    prime_contractor: 'Prime Contractor',
    subcontractor: 'Subcontractor',
    partner: 'Partner',
    vendor: 'Vendor',
  };
  return labels[type] || type;
}

export function formatSetAside(type: string | undefined | null): string {
  if (!type) return 'N/A';
  const labels: Record<string, string> = {
    small_business: 'Small Business',
    '8a': '8(a)',
    hubzone: 'HUBZone',
    wosb: 'WOSB',
    sdvosb: 'SDVOSB',
    edwosb: 'EDWOSB',
    full_and_open: 'Full & Open',
    none: 'None',
  };
  return labels[type] || type;
}

export function formatCertificationType(type: string): string {
  const labels: Record<string, string> = {
    small_business: 'Small Business',
    '8a': '8(a)',
    hubzone: 'HUBZone',
    wosb: 'WOSB',
    sdvosb: 'SDVOSB',
    edwosb: 'EDWOSB',
  };
  return labels[type] || type;
}
