import { describe, expect, it } from "vitest";
import { isPasswordLengthValid, PASSWORD_LENGTH_MESSAGE } from "./passwordPolicy";

describe("passwordPolicy", () => {
  it.each([7, 129])("rejects %i-character passwords", length => {
    expect(isPasswordLengthValid("a".repeat(length))).toBe(false);
  });

  it.each([8, 128])("accepts %i-character passwords", length => {
    expect(isPasswordLengthValid("a".repeat(length))).toBe(true);
  });

  it("exports the server-compatible error text", () => {
    expect(PASSWORD_LENGTH_MESSAGE).toBe("密码长度需为 8-128 位");
  });
});
