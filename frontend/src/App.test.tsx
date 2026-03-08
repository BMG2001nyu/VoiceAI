import { render, screen } from "@testing-library/react";
import App from "./App";

test("App renders Mission Control UI", () => {
  render(<App />);
  // The header renders the brand name
  expect(screen.getByText(/mission control/i)).toBeTruthy();
});
