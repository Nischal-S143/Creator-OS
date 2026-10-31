import { expect, test, type Page } from "@playwright/test";

const PASSWORD = "e2e-test-password";
const screenshotDir = process.env.E2E_SCREENSHOT_DIR;

function unique(prefix: string) {
  return `${prefix}-${Date.now().toString(36)}${Math.floor(Math.random() * 1e6).toString(36)}`;
}

async function shot(page: Page, name: string) {
  if (screenshotDir) await page.screenshot({ path: `${screenshotDir}/${name}.png`, fullPage: true });
}

async function signUp(page: Page, email: string) {
  await page.goto("/sign-up");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByRole("heading", { name: "Your agencies" })).toBeVisible();
}

async function signOut(page: Page) {
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/sign-in/);
}

test("signed-out visitors are sent to sign-in", async ({ page }) => {
  await page.goto("/dashboard");
  await expect(page).toHaveURL(/sign-in/);
  await shot(page, "sign-in");
});

test("the session token is not readable by browser scripts", async ({ page, context }) => {
  await signUp(page, `${unique("cookie")}@example.com`);
  const cookie = (await context.cookies()).find((c) => c.name === "creatoros_session");
  expect(cookie?.httpOnly).toBe(true);
  expect(await page.evaluate(() => document.cookie)).not.toContain("creatoros_session");
  expect(await page.evaluate(() => JSON.stringify(localStorage))).not.toContain("eyJ");
});

test("wrong password shows an error and stays on sign-in", async ({ page }) => {
  const email = `${unique("wrong")}@example.com`;
  await signUp(page, email);
  await signOut(page);
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("not-the-password");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByText("incorrect email or password")).toBeVisible();
  await expect(page).toHaveURL(/sign-in/);
});

test("agency, client and member flow, with roles and isolation", async ({ page, browser }) => {
  const ownerEmail = `${unique("owner")}@example.com`;
  const editorEmail = `${unique("editor")}@example.com`;
  const agency = unique("Agency");
  const client = unique("Fit Life");

  // A second person signs up first, so they can be added as a member.
  const editorContext = await browser.newContext();
  const editorPage = await editorContext.newPage();
  await signUp(editorPage, editorEmail);
  await expect(editorPage.getByText("No agencies yet")).toBeVisible();

  await signUp(page, ownerEmail);
  await shot(page, "dashboard-empty");
  await page.getByLabel("Agency name").fill(agency);
  await page.getByRole("button", { name: "Create agency" }).click();
  await page.getByRole("link", { name: new RegExp(agency, "i") }).click();
  await expect(page.getByRole("heading", { name: agency })).toBeVisible();
  await page.getByRole("link", { name: "Clients", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Clients" })).toBeVisible();
  const clientsUrl = page.url();

  await page.getByLabel("Client brand name").fill(client);
  await page.getByLabel("Industry (optional)").fill("Fitness");
  await page.getByRole("button", { name: "Add client" }).click();
  await page.getByRole("link", { name: new RegExp(client, "i") }).click();
  await page.getByRole("button", { name: "Details", exact: true }).click();
  await expect(page.getByLabel("Name", { exact: true })).toHaveValue(client);
  await expect(page).toHaveURL(/tab=details/);
  const brandUrl = page.url();
  await page.getByLabel("Website").fill("https://fitlife.example/");
  await page.getByRole("button", { name: "Save changes" }).click();
  await expect(page.getByText("Saved")).toBeVisible();
  await page.reload();
  await expect(page.getByLabel("Website")).toHaveValue("https://fitlife.example/");
  await shot(page, "brand");

  // Before being added, the second person cannot see this agency or its client.
  await editorPage.goto(brandUrl);
  await expect(editorPage.getByText("does not exist or you do not have access")).toBeVisible();

  await page.getByRole("link", { name: "Members", exact: true }).click();
  await page.getByLabel("Email").fill(editorEmail);
  await page.getByRole("combobox", { name: "Role", exact: true }).selectOption("analyst");
  await page.getByRole("button", { name: "Add member" }).click();
  await expect(page.getByRole("cell", { name: editorEmail })).toBeVisible();
  await shot(page, "members");

  // As an analyst they can view the client but not change it or add clients.
  await editorPage.goto(brandUrl);
  await expect(editorPage.getByLabel("Name", { exact: true })).toBeDisabled();
  await expect(editorPage.getByRole("button", { name: "Save changes" })).toHaveCount(0);
  await editorPage.goto(clientsUrl);
  await expect(editorPage.getByRole("link", { name: new RegExp(client, "i") })).toBeVisible();
  await expect(editorPage.getByRole("button", { name: "Add client" })).toHaveCount(0);
  await expect(editorPage.getByRole("link", { name: "Members" })).toHaveCount(0);

  // After removal, access ends.
  await page.getByRole("row", { name: new RegExp(editorEmail) }).getByRole("button", { name: "Remove" }).click();
  await page.getByRole("button", { name: "Remove member" }).click();
  await expect(page.getByRole("button", { name: "Restore" })).toBeVisible();
  await editorPage.goto(brandUrl);
  await expect(editorPage.getByText("does not exist or you do not have access")).toBeVisible();
  await editorContext.close();

  // Data persists across sign-out and sign-in.
  await signOut(page);
  await page.getByLabel("Email").fill(ownerEmail);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("link", { name: new RegExp(agency, "i") })).toBeVisible();
  await shot(page, "dashboard");
});

test("another website cannot make changes through the session", async ({ page, request }) => {
  await signUp(page, `${unique("csrf")}@example.com`);
  const response = await request.post("/api/backend/organizations", {
    headers: { Origin: "https://evil.example" },
    data: { name: "Evil", slug: unique("evil") },
  });
  expect(response.status()).toBe(403);
});

test("the browser cannot reach the internal AI route through the proxy", async ({ page }) => {
  await signUp(page, `${unique("ai")}@example.com`);
  const status = await page.evaluate(async () => {
    const response = await fetch("/api/backend/ai/test", { method: "POST", body: "{}" });
    return response.status;
  });
  expect(status).toBe(404);
});
