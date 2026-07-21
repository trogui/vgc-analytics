// @vitest-environment jsdom
import { fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { expect, test } from "vitest";

import { ModeSwitch } from "./ModeSwitch";

function Harness() {
  const [mode, setMode] = useState<"basic" | "versus">("basic");
  return <ModeSwitch mode={mode} onModeChange={setMode} onSwap={() => {}} />;
}

function rect(element: Element) {
  const { x, y, width, height, top, right, bottom, left } = element.getBoundingClientRect();
  return { x, y, width, height, top, right, bottom, left };
}

test("Basic → Versus → Basic preserves segmented-control rectangles", () => {
  render(<Harness />);
  const control = screen.getByLabelText("Analysis mode");
  const basic = screen.getByRole("button", { name: "Basic" });
  const versus = screen.getByRole("button", { name: "Versus" });
  const layout = screen.getByTestId("analysis-actions");
  const before = [rect(control), rect(basic), rect(versus), rect(layout)];

  fireEvent.click(versus);
  const during = [rect(control), rect(basic), rect(versus), rect(layout)];
  fireEvent.click(basic);
  const after = [rect(control), rect(basic), rect(versus), rect(layout)];

  expect(during).toEqual(before);
  expect(after).toEqual(before);
});
