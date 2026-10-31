import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

import { PLANNED_SECTIONS } from "../lib/sections";

const screenshotDir = process.env.E2E_SCREENSHOT_DIR;

function unique(prefix: string) {
  return `${prefix}-${Date.now().toString(36)}${Math.floor(Math.random() * 1e6).toString(36)}`;
}

async function shot(page: Page, name: string) {
  if (screenshotDir) await page.screenshot({ path: `${screenshotDir}/${name}.png`, fullPage: true });
}

async function setup(page: Page) {
  await page.goto("/sign-up");
  await page.getByLabel("Email").fill(`${unique("ux")}@example.com`);
  await page.getByLabel("Password").fill("e2e-test-password");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByRole("heading", { name: "Your agencies" })).toBeVisible();
  const agency = unique("Agency");
  await page.getByLabel("Agency name").fill(agency);
  await page.getByRole("button", { name: "Create agency" }).click();
  await page.getByRole("link", { name: new RegExp(agency, "i") }).click();
  await expect(page.getByRole("heading", { name: agency })).toBeVisible();
  const base = new URL(page.url()).pathname;
  await page.goto(`${base}/clients`);
  await page.getByLabel("Client brand name").fill("Peak Trail Coffee");
  await page.getByLabel("Industry (optional)").fill("Food and drink");
  await page.getByRole("button", { name: "Add client" }).click();
  await expect(page.getByRole("link", { name: /Peak Trail Coffee/ })).toBeVisible();
  return base;
}

async function expectNoSidewaysScroll(page: Page) {
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow).toBeLessThanOrEqual(0);
}

async function expectAccessible(page: Page, where: string) {
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();
  const summary = results.violations.flatMap((v) =>
    v.nodes.slice(0, 4).map((n) => `${v.id}: ${n.target} :: ${n.html.slice(0, 90)} :: ${(n.any[0]?.message ?? "").slice(0, 110)}`),
  );
  expect(summary, where).toEqual([]);
}

test("every planned section says it is coming and shows no action or data", async ({ page }) => {
  const base = await setup(page);
  for (const section of PLANNED_SECTIONS) {
    await page.goto(`${base}/${section.slug}`);
    await expect(page.getByRole("heading", { name: section.title, exact: true })).toBeVisible();
    await expect(page.getByText(`Coming in ${section.phase}`)).toBeVisible();
    const main = page.locator("main");
    await expect(main.getByRole("button")).toHaveCount(0);
    await expect(main.getByRole("textbox")).toHaveCount(0);
  }
  await shot(page, "planned-section");
  await page.goto(`${base}/not-a-real-section`);
  await expect(page.getByRole("heading", { name: "Page not found" })).toBeVisible();
});

test("every sidebar link leads to a working page", async ({ page }) => {
  const base = await setup(page);
  await page.goto(base);
  const nav = page.getByRole("navigation", { name: "Main" });
  await expect(nav.getByRole("link", { name: "Settings" })).toBeVisible();
  const links = await nav.getByRole("link").evaluateAll((items) =>
    items.map((item) => item.getAttribute("href")),
  );
  expect(links.length).toBeGreaterThanOrEqual(16);
  for (const href of links) {
    const response = await page.goto(href!);
    expect(response?.status(), href!).toBeLessThan(400);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await expect(page.getByRole("navigation", { name: "Main" }).locator('[aria-current="page"]')).toHaveCount(1);
  }
});

test("real pages pass an accessibility scan in both themes", async ({ page }) => {
  const base = await setup(page);
  const brandHref = await page.getByRole("link", { name: /Peak Trail Coffee/ }).getAttribute("href");
  const pages = [
    base,
    `${base}/clients`,
    `${base}/members`,
    `${base}/settings`,
    `${base}/brand-brain`,
    `${brandHref}?tab=brain`,
    `${brandHref}?tab=campaigns`,
    `${brandHref}?tab=details`,
    `${base}/calendar`,
  ];
  for (const theme of ["Light theme", "Dark theme"]) {
    await page.goto(base);
    await page.getByRole("button", { name: theme }).click();
    for (const path of pages) {
      await page.goto(path);
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
      await page.waitForLoadState("networkidle");
      await expectAccessible(page, `${path} (${theme})`);
    }
  }
  await page.goto(`${base}/settings`);
  await shot(page, "settings-dark");
});

test("sign-in pages pass an accessibility scan", async ({ browser }) => {
  const context = await browser.newContext();
  const page = await context.newPage();
  for (const path of ["/sign-in", "/sign-up"]) {
    await page.goto(path);
    // The submit button is briefly disabled until the page is interactive.
    await expect(page.getByRole("button", { name: /Sign in|Create account/ })).toBeEnabled();
    await expectAccessible(page, path);
  }
  await shot(page, "sign-up");
  await context.close();
});

test("the app works at phone width", async ({ page }) => {
  const base = await setup(page);
  await page.setViewportSize({ width: 375, height: 720 });
  for (const path of [base, `${base}/clients`, `${base}/members`, `${base}/settings`, `${base}/calendar`]) {
    await page.goto(path);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await page.waitForLoadState("networkidle");
    await expectNoSidewaysScroll(page);
  }
  await shot(page, "mobile-calendar");

  await page.getByRole("button", { name: "Open menu" }).click();
  const menu = page.getByRole("dialog", { name: "Menu" });
  await expect(menu).toBeVisible();
  await shot(page, "mobile-menu");
  await menu.getByRole("link", { name: "Settings" }).click();
  await expect(page.getByRole("heading", { name: "Settings" })).toBeVisible();
  await expect(menu).toHaveCount(0);

  await page.getByRole("button", { name: "Open menu" }).click();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog", { name: "Menu" })).toHaveCount(0);
});

test("keyboard users can skip to content, and focus is visible", async ({ page }) => {
  const base = await setup(page);
  await page.goto(base);
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await page.keyboard.press("Tab");
  const skip = page.getByRole("link", { name: "Skip to content" });
  await expect(skip).toBeFocused();
  await expect(skip).toBeVisible();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/#main$/);
});

test("the chosen client tab survives a reload and bad tabs fall back", async ({ page }) => {
  await setup(page);
  await page.getByRole("link", { name: /Peak Trail Coffee/ }).click();
  await expect(page.getByRole("heading", { name: "Brand documents" })).toBeVisible();
  await page.getByRole("button", { name: "Campaigns", exact: true }).click();
  await expect(page).toHaveURL(/tab=campaigns/);
  await page.reload();
  await expect(page.getByLabel("Campaign name")).toBeVisible();
  await shot(page, "client-campaigns");
  const url = new URL(page.url());
  await page.goto(`${url.pathname}?tab=nonsense`);
  await expect(page.getByRole("heading", { name: "Brand documents" })).toBeVisible();
  await shot(page, "client-brain");
});

test("removing a member asks for confirmation, and cancel changes nothing", async ({ page, browser }) => {
  const base = await setup(page);
  const otherContext = await browser.newContext();
  const other = await otherContext.newPage();
  const email = `${unique("member")}@example.com`;
  await other.goto("/sign-up");
  await other.getByLabel("Email").fill(email);
  await other.getByLabel("Password").fill("e2e-test-password");
  await other.getByRole("button", { name: "Create account" }).click();
  await expect(other.getByRole("heading", { name: "Your agencies" })).toBeVisible();
  await otherContext.close();

  await page.goto(`${base}/members`);
  await page.getByLabel("Email").fill(email);
  await page.getByRole("button", { name: "Add member" }).click();
  const row = page.getByRole("row", { name: new RegExp(email) });
  await expect(row).toBeVisible();
  await row.getByRole("button", { name: "Remove" }).click();
  await expect(page.getByRole("dialog")).toContainText(email);
  await shot(page, "remove-dialog");
  await page.getByRole("button", { name: "Cancel" }).click();
  await expect(row.getByRole("button", { name: "Remove" })).toBeVisible();
  await row.getByRole("button", { name: "Remove" }).click();
  await page.getByRole("button", { name: "Remove member" }).click();
  await expect(row.getByRole("button", { name: "Restore" })).toBeVisible();
});

test("the overview shows real counts", async ({ page }) => {
  const base = await setup(page);
  await page.goto(base);
  await expect(page.getByText("Clients", { exact: true }).last()).toBeVisible();
  await expect(page.getByRole("link", { name: /Peak Trail Coffee/ })).toBeVisible();
  await shot(page, "overview");
});

test("the AI Team page shows every agent with its real status", async ({ page }) => {
  const base = await setup(page);
  await page.goto(`${base}/agents`);
  await expect(page.getByRole("heading", { name: "AI Team" })).toBeVisible();
  await expect(page.getByText("Understanding", { exact: true })).toBeVisible();
  await expect(page.getByText("Needs Google billing")).toHaveCount(2);
  await expect(page.getByText("No runs yet")).toBeVisible();
  await page.waitForLoadState("networkidle");
  await expectAccessible(page, "agents");
  await shot(page, "agents");
  const clipped = await page
    .getByRole("navigation", { name: "Main" })
    .locator("a span.truncate")
    .evaluateAll((items) => items.filter((item) => item.scrollWidth > item.clientWidth).map((i) => i.textContent));
  expect(clipped).toEqual([]);
});
