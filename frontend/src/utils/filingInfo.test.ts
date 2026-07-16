import { expect, it } from "vitest";
import { ICP_FILING, POLICE_FILING } from "./filingInfo";

it("locks the supplied filing numbers and official query links", () => {
  expect(ICP_FILING).toEqual({
    number: "鲁ICP备2026026570号",
    href: "https://beian.miit.gov.cn/",
  });
  expect(POLICE_FILING).toEqual({
    number: "鲁公网安备37070402000217号",
    href: "https://beian.mps.gov.cn/#/query/webSearch?code=37070402000217",
  });
});
