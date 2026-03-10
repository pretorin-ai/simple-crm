import { describe, it, expect } from "vitest";
import {
  getContactStatusBadge,
  getContactTypeBadge,
  getContractStatusBadge,
  getOpportunityStageBadge,
  getAccountTypeBadge,
  getComplianceStatusBadge,
  getTeamingStatusBadge,
  getProposalStatusBadge,
  formatCurrency,
  formatAccountType,
  formatSetAside,
  formatCertificationType,
} from "./badges";

describe("getContactStatusBadge", () => {
  it("returns correct variants for known statuses", () => {
    expect(getContactStatusBadge("cold")).toBe("secondary");
    expect(getContactStatusBadge("warm")).toBe("default");
    expect(getContactStatusBadge("hot")).toBe("destructive");
  });

  it("returns outline for unknown status", () => {
    expect(getContactStatusBadge("unknown")).toBe("outline");
  });
});

describe("getContactTypeBadge", () => {
  it("returns correct variants", () => {
    expect(getContactTypeBadge("individual")).toBe("default");
    expect(getContactTypeBadge("government")).toBe("secondary");
    expect(getContactTypeBadge("commercial")).toBe("outline");
  });

  it("returns outline for unknown type", () => {
    expect(getContactTypeBadge("other")).toBe("outline");
  });
});

describe("getContractStatusBadge", () => {
  it("returns correct variants", () => {
    expect(getContractStatusBadge("prospective")).toBe("outline");
    expect(getContractStatusBadge("in progress")).toBe("default");
    expect(getContractStatusBadge("submitted")).toBe("secondary");
    expect(getContractStatusBadge("not a good fit")).toBe("destructive");
  });

  it("returns outline for unknown", () => {
    expect(getContractStatusBadge("draft")).toBe("outline");
  });
});

describe("getOpportunityStageBadge", () => {
  it("returns correct variants for all stages", () => {
    expect(getOpportunityStageBadge("identified")).toBe("outline");
    expect(getOpportunityStageBadge("qualified")).toBe("secondary");
    expect(getOpportunityStageBadge("capture")).toBe("default");
    expect(getOpportunityStageBadge("teaming")).toBe("default");
    expect(getOpportunityStageBadge("proposal")).toBe("default");
    expect(getOpportunityStageBadge("submitted")).toBe("secondary");
    expect(getOpportunityStageBadge("awarded")).toBe("default");
    expect(getOpportunityStageBadge("lost")).toBe("destructive");
  });

  it("returns outline for unknown stage", () => {
    expect(getOpportunityStageBadge("pending")).toBe("outline");
  });
});

describe("getAccountTypeBadge", () => {
  it("returns correct variants", () => {
    expect(getAccountTypeBadge("government_agency")).toBe("secondary");
    expect(getAccountTypeBadge("prime_contractor")).toBe("default");
    expect(getAccountTypeBadge("subcontractor")).toBe("outline");
    expect(getAccountTypeBadge("partner")).toBe("default");
    expect(getAccountTypeBadge("vendor")).toBe("outline");
  });

  it("returns outline for unknown", () => {
    expect(getAccountTypeBadge("other")).toBe("outline");
  });
});

describe("getComplianceStatusBadge", () => {
  it("returns correct variants", () => {
    expect(getComplianceStatusBadge("active")).toBe("default");
    expect(getComplianceStatusBadge("expiring_soon")).toBe("secondary");
    expect(getComplianceStatusBadge("expired")).toBe("destructive");
    expect(getComplianceStatusBadge("pending")).toBe("outline");
  });

  it("returns outline for unknown", () => {
    expect(getComplianceStatusBadge("revoked")).toBe("outline");
  });
});

describe("getTeamingStatusBadge", () => {
  it("returns correct variants", () => {
    expect(getTeamingStatusBadge("potential")).toBe("outline");
    expect(getTeamingStatusBadge("nda_signed")).toBe("secondary");
    expect(getTeamingStatusBadge("teaming_agreed")).toBe("default");
    expect(getTeamingStatusBadge("active")).toBe("default");
    expect(getTeamingStatusBadge("inactive")).toBe("destructive");
  });

  it("returns outline for unknown", () => {
    expect(getTeamingStatusBadge("dissolved")).toBe("outline");
  });
});

describe("getProposalStatusBadge", () => {
  it("returns correct variants", () => {
    expect(getProposalStatusBadge("not_started")).toBe("outline");
    expect(getProposalStatusBadge("in_progress")).toBe("default");
    expect(getProposalStatusBadge("review")).toBe("secondary");
    expect(getProposalStatusBadge("final")).toBe("default");
    expect(getProposalStatusBadge("submitted")).toBe("secondary");
  });

  it("returns outline for unknown", () => {
    expect(getProposalStatusBadge("cancelled")).toBe("outline");
  });
});

describe("formatCurrency", () => {
  it("formats billions", () => {
    expect(formatCurrency(1_500_000_000)).toBe("$1.5B");
    expect(formatCurrency(2_000_000_000)).toBe("$2.0B");
  });

  it("formats millions", () => {
    expect(formatCurrency(1_500_000)).toBe("$1.5M");
    expect(formatCurrency(10_000_000)).toBe("$10.0M");
  });

  it("formats thousands", () => {
    expect(formatCurrency(50_000)).toBe("$50K");
    expect(formatCurrency(1_000)).toBe("$1K");
  });

  it("formats small values", () => {
    expect(formatCurrency(500)).toBe("$500");
  });

  it("returns N/A for null/undefined", () => {
    expect(formatCurrency(null)).toBe("N/A");
    expect(formatCurrency(undefined)).toBe("N/A");
  });
});

describe("formatAccountType", () => {
  it("formats known types", () => {
    expect(formatAccountType("government_agency")).toBe("Government Agency");
    expect(formatAccountType("prime_contractor")).toBe("Prime Contractor");
    expect(formatAccountType("subcontractor")).toBe("Subcontractor");
    expect(formatAccountType("partner")).toBe("Partner");
    expect(formatAccountType("vendor")).toBe("Vendor");
  });

  it("returns raw value for unknown type", () => {
    expect(formatAccountType("custom")).toBe("custom");
  });
});

describe("formatSetAside", () => {
  it("formats known set-aside types", () => {
    expect(formatSetAside("small_business")).toBe("Small Business");
    expect(formatSetAside("8a")).toBe("8(a)");
    expect(formatSetAside("hubzone")).toBe("HUBZone");
    expect(formatSetAside("wosb")).toBe("WOSB");
    expect(formatSetAside("sdvosb")).toBe("SDVOSB");
    expect(formatSetAside("edwosb")).toBe("EDWOSB");
    expect(formatSetAside("full_and_open")).toBe("Full & Open");
    expect(formatSetAside("none")).toBe("None");
  });

  it("returns N/A for null/undefined", () => {
    expect(formatSetAside(null)).toBe("N/A");
    expect(formatSetAside(undefined)).toBe("N/A");
  });

  it("returns raw value for unknown type", () => {
    expect(formatSetAside("custom")).toBe("custom");
  });
});

describe("formatCertificationType", () => {
  it("formats known types", () => {
    expect(formatCertificationType("small_business")).toBe("Small Business");
    expect(formatCertificationType("8a")).toBe("8(a)");
    expect(formatCertificationType("hubzone")).toBe("HUBZone");
    expect(formatCertificationType("wosb")).toBe("WOSB");
    expect(formatCertificationType("sdvosb")).toBe("SDVOSB");
    expect(formatCertificationType("edwosb")).toBe("EDWOSB");
  });

  it("returns raw value for unknown type", () => {
    expect(formatCertificationType("custom")).toBe("custom");
  });
});
