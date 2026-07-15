import { describe, expect, it } from "vitest";
import { USERNAME_FORMAT_MESSAGE, isRegistrationUsernameValid } from "./usernamePolicy";

describe("usernamePolicy", () => {
  it.each(["中文", "user_name", "user-name", "ab", "a".repeat(33)])("rejects %s", value => {
    expect(isRegistrationUsernameValid(value)).toBe(false);
  });

  it.each(["abc", "A1b2", "a".repeat(32)])("accepts %s", value => {
    expect(isRegistrationUsernameValid(value)).toBe(true);
  });

  it("uses the registration message", () => {
    expect(USERNAME_FORMAT_MESSAGE).toBe("用户名仅支持 3–32 位英文字母或数字");
  });
});
