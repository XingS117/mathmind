export async function jsonOrThrow(response) {
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = data.detail;
    const validationMessage = Array.isArray(detail) && typeof detail[0]?.msg === "string"
      ? detail[0].msg.replace(/^Value error,\s*/, "")
      : null;
    throw new Error(typeof detail === "string" ? detail : validationMessage || "请求失败");
  }
  return data;
}
