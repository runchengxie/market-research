import test from "node:test";
import assert from "node:assert/strict";
import {
  applyTheme,
  persistThemeChoice,
  readThemeChoice,
  resolveTheme,
} from "./theme.ts";

test("theme resolution keeps light as the explicit default", () => {
  assert.equal(resolveTheme("light", true), "light");
  assert.equal(resolveTheme("dark", false), "dark");
  assert.equal(resolveTheme("system", true), "dark");
  assert.equal(resolveTheme("system", false), "light");
});

test("theme choice reads and persists only supported values", () => {
  const values = new Map([["market-research-theme", "dark"]]);
  const storage = {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
  };

  assert.equal(readThemeChoice(storage), "dark");
  storage.setItem("market-research-theme", "unsupported");
  assert.equal(readThemeChoice(storage), "system");
  persistThemeChoice(storage, "light");
  assert.equal(values.get("market-research-theme"), "light");
});

test("applyTheme updates the document theme and returns the resolved mode", () => {
  const attributes = new Map();
  const documentElement = {
    dataset: {},
    setAttribute: (key, value) => attributes.set(key, value),
  };

  assert.equal(applyTheme("system", true, documentElement), "dark");
  assert.equal(documentElement.dataset.theme, "dark");
  assert.equal(attributes.get("data-theme"), "dark");
});
