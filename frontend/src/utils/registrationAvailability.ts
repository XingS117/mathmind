export type UsernameAvailabilityStatus = "idle" | "checking" | "available" | "taken" | "error";

interface RegistrationReadiness {
  usernameValid: boolean;
  usernameStatus: UsernameAvailabilityStatus;
  nameValid: boolean;
  passwordValid: boolean;
}

export function canSubmitRegistration({ usernameValid, usernameStatus, nameValid, passwordValid }: RegistrationReadiness): boolean {
  return usernameValid && usernameStatus === "available" && nameValid && passwordValid;
}

export function usernameAvailabilityMessage(status: UsernameAvailabilityStatus): string {
  switch (status) {
    case "checking":
      return "正在检查用户名…";
    case "available":
      return "用户名可用";
    case "taken":
      return "该用户名已被使用，请换一个";
    case "error":
      return "暂时无法检查用户名，请稍后重试";
    default:
      return "";
  }
}
