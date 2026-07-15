const pendingVisits = new Map();

export function referralVisitStorageKey(code) {
  return `referral_visit:${code}`;
}

export function captureVisitOnce(code, storage, requestVisit) {
  const key = referralVisitStorageKey(code);
  const existing = storage.getItem(key);
  if (existing) return Promise.resolve(existing);
  const pending = pendingVisits.get(code);
  if (pending) return pending;

  const request = Promise.resolve()
    .then(requestVisit)
    .then((visitId) => {
      if (!visitId) throw new Error("分享访问未返回标识");
      storage.setItem(key, visitId);
      return visitId;
    })
    .finally(() => pendingVisits.delete(code));
  pendingVisits.set(code, request);
  return request;
}
