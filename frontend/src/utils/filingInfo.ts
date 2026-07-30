export interface FilingInfo {
  number: string;
  href: string;
}

function optionalFiling(number: string | undefined, href: string | undefined): FilingInfo | null {
  return number && href ? { number, href } : null;
}

export const ICP_FILING = optionalFiling(
  import.meta.env.VITE_ICP_FILING_NUMBER,
  import.meta.env.VITE_ICP_FILING_URL,
);

export const POLICE_FILING = optionalFiling(
  import.meta.env.VITE_POLICE_FILING_NUMBER,
  import.meta.env.VITE_POLICE_FILING_URL,
);
