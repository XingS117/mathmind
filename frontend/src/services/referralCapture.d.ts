export function referralVisitStorageKey(code: string): string;
export function captureVisitOnce(
  code: string,
  storage: Storage,
  requestVisit: () => Promise<string>,
): Promise<string>;
