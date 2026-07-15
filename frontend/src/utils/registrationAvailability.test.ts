import { describe, expect, it } from "vitest";
import { canSubmitRegistration, usernameAvailabilityMessage } from "./registrationAvailability";

describe("registration availability", () => {
  it("keeps submission disabled while a valid username is checking", () => {
    expect(canSubmitRegistration({
      usernameValid: true,
      usernameStatus: "checking",
      nameValid: true,
      passwordValid: true,
    })).toBe(false);
  });

  it("only enables submission for an available username and valid fields", () => {
    expect(canSubmitRegistration({
      usernameValid: true,
      usernameStatus: "available",
      nameValid: true,
      passwordValid: true,
    })).toBe(true);
    expect(canSubmitRegistration({
      usernameValid: true,
      usernameStatus: "taken",
      nameValid: true,
      passwordValid: true,
    })).toBe(false);
  });

  it("uses clear messages for taken and unavailable checks", () => {
    expect(usernameAvailabilityMessage("taken")).toBe("该用户名已被使用，请换一个");
    expect(usernameAvailabilityMessage("error")).toBe("暂时无法检查用户名，请稍后重试");
  });
});
