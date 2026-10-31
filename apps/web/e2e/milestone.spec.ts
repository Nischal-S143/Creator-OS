import { expect, test } from "@playwright/test";

const screenshotDir = process.env.E2E_SCREENSHOT_DIR;

function unique(prefix: string) {
  return `${prefix}-${Date.now().toString(36)}${Math.floor(Math.random() * 1e6).toString(36)}`;
}

const GUIDELINES = `Peak Trail Coffee brand guidelines.
We are a small mountain-town coffee roaster. Our voice is warm, plain and a little playful.
Our customers are outdoor lovers aged 25 to 45 who care about where their coffee comes from.
We talk about sourcing, brewing at camp, and the people behind each roast.
Never make health claims about coffee. Never criticize other roasters by name.`;

test("the first milestone works end to end with real Gemini and Meko", async ({ page }) => {
  await page.goto("/sign-up");
  await page.getByLabel("Email").fill(`${unique("milestone")}@example.com`);
  await page.getByLabel("Password").fill("e2e-test-password");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByRole("heading", { name: "Your agencies" })).toBeVisible();

  const agency = unique("Summit Agency");
  await page.getByLabel("Agency name").fill(agency);
  await page.getByRole("button", { name: "Create agency" }).click();
  await page.getByRole("link", { name: new RegExp(agency, "i") }).click();
  await page.getByRole("link", { name: "Clients", exact: true }).click();

  await page.getByLabel("Client brand name").fill("Peak Trail Coffee");
  await page.getByRole("button", { name: "Add client" }).click();
  await page.getByRole("link", { name: /Peak Trail Coffee/ }).click();
  await expect(page.getByRole("heading", { name: "Brand documents" })).toBeVisible();

  await page.getByLabel("Brand document file").setInputFiles({
    name: "guidelines.txt",
    mimeType: "text/plain",
    buffer: Buffer.from(GUIDELINES),
  });
  await expect(page.getByText("guidelines.txt")).toBeVisible();

  await page.getByRole("button", { name: "Draft profile with AI" }).click();
  await expect(page.getByText("Waiting for approval")).toBeVisible({ timeout: 120_000 });
  await expect(page.getByText(/health claims/i).first()).toBeVisible();

  await page.getByRole("button", { name: "Approve profile" }).click();
  await expect(page.getByText("Saved to agent memory")).toBeVisible({ timeout: 120_000 });
  if (screenshotDir) await page.screenshot({ path: `${screenshotDir}/brand-brain.png`, fullPage: true });

  await page.getByRole("button", { name: "Campaigns", exact: true }).click();
  await page.getByLabel("Campaign name").fill("Autumn roast launch");
  await page.getByLabel("Objective").fill("Get campers to try our new autumn roast");
  await page.getByRole("button", { name: "Create campaign" }).click();
  await page.getByRole("link", { name: /Autumn roast launch/ }).click();

  await page.getByRole("button", { name: "Generate three ideas" }).click();
  await expect(page.getByRole("button", { name: "Select this idea" })).toHaveCount(3, {
    timeout: 180_000,
  });
  await expect(page.getByText("used agent memory")).toBeVisible();

  await page.getByRole("button", { name: "Select this idea" }).first().click();
  await expect(page.getByText("Selected", { exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByText("Selected", { exact: true })).toBeVisible();
  if (screenshotDir) await page.screenshot({ path: `${screenshotDir}/campaign.png`, fullPage: true });

  // The selected idea goes through the agents and stops for a person.
  await page.getByRole("button", { name: "Create content" }).click();
  await expect(page.getByRole("heading", { name: "Research brief" })).toBeVisible({ timeout: 240_000 });
  await expect(page.getByRole("heading", { name: "Scene plan" })).toBeVisible();
  await expect(page.getByText("Version 1")).toBeVisible();
  if (screenshotDir) await page.screenshot({ path: `${screenshotDir}/content.png`, fullPage: true });
  const approve = page.getByRole("button", { name: "Approve this version" });
  if (await approve.isVisible()) {
    await approve.click();
    await expect(page.getByText("Version 1 is approved.")).toBeVisible({ timeout: 60_000 });
  } else {
    // Real Guardian may block a draft. That path must explain itself rather than offer approval.
    await expect(page.getByText("Fix the Guardian findings")).toBeVisible();
  }
});
