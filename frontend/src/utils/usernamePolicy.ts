export const USERNAME_FORMAT_MESSAGE = "用户名仅支持 3–32 位英文字母或数字";

export function isRegistrationUsernameValid(value: string): boolean {
  return /^[A-Za-z0-9]{3,32}$/.test(value);
}
