// Records the ComplianceOS product walkthrough against a running stack.
//
//   docker compose up -d            (from the repository root)
//   cd scripts/demo && bun install && node record-demo.mjs
//
// Output: out/complianceos-demo.webm (and .mp4 when ffmpeg is installed). The script drives the
// real app at a human pace, with a visible cursor and captions, so the video needs no voice-over.
// BASE_URL and CHROMIUM_PATH can be overridden from the environment.

import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, readdirSync, renameSync } from "node:fs";
import { join } from "node:path";
import { chromium } from "playwright";

const BASE = process.env.BASE_URL ?? "http://localhost:3000";
const OUT = join(import.meta.dirname, "out");
const SIZE = { width: 1280, height: 800 };
mkdirSync(OUT, { recursive: true });

const OVERLAY = () => {
  const install = () => {
    if (document.getElementById("demo-cursor")) return;
    const cursor = document.createElement("div");
    cursor.id = "demo-cursor";
    Object.assign(cursor.style, {
      position: "fixed", zIndex: 2147483647, width: "18px", height: "18px", borderRadius: "50%",
      background: "rgba(79,70,229,.35)", border: "2px solid rgb(79,70,229)", pointerEvents: "none",
      transform: "translate(-50%,-50%)", left: "-40px", top: "-40px", transition: "left .12s, top .12s",
    });
    const caption = document.createElement("div");
    caption.id = "demo-caption";
    Object.assign(caption.style, {
      position: "fixed", zIndex: 2147483646, left: "50%", bottom: "28px", transform: "translateX(-50%)",
      maxWidth: "860px", padding: "12px 20px", borderRadius: "10px", background: "rgba(15,23,42,.92)",
      color: "#fff", font: "500 17px/1.45 Inter, system-ui, sans-serif", textAlign: "center",
      boxShadow: "0 8px 30px rgba(0,0,0,.25)", pointerEvents: "none", opacity: "0", transition: "opacity .25s",
    });
    document.body.append(cursor, caption);
    addEventListener("mousemove", (e) => { cursor.style.left = `${e.clientX}px`; cursor.style.top = `${e.clientY}px`; }, true);
    addEventListener("mousedown", () => { cursor.style.background = "rgba(79,70,229,.7)"; }, true);
    addEventListener("mouseup", () => { cursor.style.background = "rgba(79,70,229,.35)"; }, true);
  };
  if (document.readyState === "loading") addEventListener("DOMContentLoaded", install); else install();
};

const pause = (ms) => new Promise((r) => setTimeout(r, ms));

async function caption(page, text, ms = 3200) {
  await page.evaluate((t) => {
    const c = document.getElementById("demo-caption");
    if (!c) return;
    c.textContent = t;
    c.style.opacity = t ? "1" : "0";
  }, text);
  if (ms) await pause(ms);
}

async function click(page, locator, wait = 700) {
  await locator.scrollIntoViewIfNeeded();
  const box = await locator.boundingBox();
  if (box) await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2, { steps: 12 });
  await pause(250);
  await locator.click();
  await pause(wait);
}

async function type(page, locator, text) {
  await click(page, locator, 200);
  await locator.fill("");
  await locator.pressSequentially(text, { delay: 35 });
}

async function scrollTo(page, locator, block = "center") {
  await locator.evaluate((el, b) => el.scrollIntoView({ behavior: "smooth", block: b }), block);
  await pause(900);
}

const executablePath = process.env.CHROMIUM_PATH ?? (() => {
  const cache = join(process.env.HOME ?? "", "Library/Caches/ms-playwright");
  if (!existsSync(cache)) return undefined;
  const dirs = readdirSync(cache).filter((d) => /^chromium-\d+$/.test(d)).sort().reverse();
  const layouts = [
    "chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing",
    "chrome-mac/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing",
    "chrome-mac/Chromium.app/Contents/MacOS/Chromium",
  ];
  for (const d of dirs) {
    for (const l of layouts) {
      const p = join(cache, d, l);
      if (existsSync(p)) return p;
    }
  }
  return undefined;
})();

const browser = await chromium.launch({ executablePath });
const context = await browser.newContext({
  viewport: SIZE,
  deviceScaleFactor: 1,
  colorScheme: "light",
  recordVideo: { dir: OUT, size: SIZE },
});
await context.addInitScript(OVERLAY);
const page = await context.newPage();

try {
  // 1. Home
  await page.goto(BASE, { waitUntil: "networkidle" });
  await caption(page, "ComplianceOS: open-source licensing roadmaps for satellite missions.", 3500);
  await caption(page, "Describe a mission once. Get every licence it needs, in every country, with the law behind each one.", 4200);

  // 2. Wizard
  await click(page, page.getByRole("link", { name: "Plan a mission" }), 1200);
  await caption(page, "Four short steps. A French operator planning a 6-satellite Earth-observation constellation.", 0);
  await type(page, page.locator("#name"), "Aurora EO constellation");
  await type(page, page.locator("#op"), "Aurora Orbital SAS (fictional)");
  await click(page, page.locator("#opc"), 200);
  await page.locator("#opc").selectOption("FR");
  await pause(1600);
  await caption(page, "The live preview on the right updates with every answer.", 2800);
  await click(page, page.getByRole("button", { name: "Next" }), 600);

  await type(page, page.locator("#n"), "6");
  await type(page, page.locator("#alt"), "520");
  await click(page, page.getByRole("checkbox", { name: /Imaging payload/ }), 900);
  await click(page, page.getByRole("button", { name: "Next" }), 600);

  await click(page, page.getByRole("checkbox", { name: /Earth observation/ }), 500);
  for (const band of ["S", "X"]) await click(page, page.getByRole("button", { name: band, exact: true }), 300);
  await click(page, page.getByRole("button", { name: "Next" }), 600);

  await caption(page, "Customers in the US and the UK, ground stations in both, launch in mid-2028.", 0);
  const quick = page.getByRole("button", { name: "+ United States" });
  await click(page, quick.first(), 500);
  await click(page, page.getByRole("button", { name: "+ United Kingdom" }).first(), 500);
  await click(page, page.getByRole("button", { name: "+ United Kingdom" }).last(), 500);
  await click(page, page.getByRole("button", { name: "+ United States" }).last(), 500);
  await page.locator("#ld").fill("2028-06-01");
  await pause(1800);
  await click(page, page.getByRole("button", { name: "Create roadmap" }), 2200);
  await page.waitForSelector("text=Licences & filings");

  // 3. Roadmap
  await caption(page, "8 licences and filings across 4 jurisdictions, each dated back from the launch.", 3600);
  await scrollTo(page, page.getByRole("tablist"), "start");
  await caption(page, "The timeline shows preparation and authority review. The critical path is in indigo.", 4200);

  // 4. Licence drawer
  await click(page, page.getByRole("button", { name: /Space operation authorisation \(LOS\)/ }).last(), 1500);
  await caption(page, "Each requirement says why it applies to this mission, citing the article of law.", 3000);
  const chip = page.getByRole("dialog").getByRole("button", { name: /Source:/ }).first();
  await click(page, chip, 1200);
  await caption(page, "One click shows the quoted law, the official link, and when it was checked.", 4200);
  await page.keyboard.press("Escape");
  await pause(500);
  await scrollTo(page, page.getByRole("dialog").getByRole("heading", { name: "Timing" }), "start");
  await caption(page, "Timing is labelled: set in law, published practice, or an estimate.", 3800);
  await scrollTo(page, page.getByRole("dialog").getByRole("heading", { name: "Who to contact" }), "start");
  await caption(page, "The authority's own contact channels, and a drafted first email.", 0);
  await click(page, page.getByRole("dialog").getByRole("button", { name: "Draft first email" }), 2600);
  await click(page, page.getByRole("dialog").getByRole("button", { name: "Close", exact: true }).last(), 600);

  // 5. Track the application
  await scrollTo(page, page.getByRole("dialog").getByRole("button", { name: "Track this application" }), "center");
  await caption(page, "Start tracking the application…", 0);
  await click(page, page.getByRole("dialog").getByRole("button", { name: "Track this application" }), 1400);
  await click(page, page.getByRole("dialog").getByRole("button", { name: "Open application" }), 1400);
  await caption(page, "…record its submission, and the next action and history follow.", 0);
  await click(page, page.getByRole("dialog").getByRole("button", { name: "Submitted", exact: true }), 700);
  await type(page, page.getByRole("dialog").locator("#n"), "Filed on the FSOA platform");
  await click(page, page.getByRole("dialog").getByRole("button", { name: "Save", exact: true }), 2200);
  await caption(page, "Only valid status changes are offered, and every change is logged.", 3200);
  await page.keyboard.press("Escape");
  await pause(700);

  // 6. Deadlines and brief
  await page.evaluate(() => window.scrollTo({ top: 300, behavior: "smooth" }));
  await click(page, page.getByRole("tab", { name: /Deadlines/ }), 1200);
  await caption(page, "Every start, submission and obligation date, exportable to any calendar.", 3800);
  await click(page, page.getByRole("tab", { name: /Brief/ }), 2000);
  await caption(page, "A regulatory brief: summary, critical path, risks, sequence, questions for each authority.", 3000);
  await page.evaluate(() => window.scrollBy({ top: 520, behavior: "smooth" }));
  await caption(page, "Every legal statement is cited. An optional AI summary must pass the same citation check.", 4200);

  // 7. Directory and data
  await click(page, page.getByRole("link", { name: "Directory" }), 1800);
  await caption(page, "A directory of authorities and licensing firms, listed neutrally.", 3400);
  await click(page, page.getByRole("link", { name: "Data & sources" }), 1800);
  await caption(page, "Open data, researched from official sources, with a public verification log.", 3600);
  await caption(page, "Open source and self-hosted: docker compose up.", 3800);
} finally {
  const video = page.video();
  await context.close();
  await browser.close();
  if (video) {
    const raw = await video.path();
    const webm = join(OUT, "complianceos-demo.webm");
    renameSync(raw, webm);
    console.log(`video: ${webm}`);
    try {
      execFileSync("ffmpeg", ["-y", "-loglevel", "error", "-i", webm, "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-crf", "22", "-movflags", "+faststart", join(OUT, "complianceos-demo.mp4")]);
      console.log(`video: ${join(OUT, "complianceos-demo.mp4")}`);
    } catch {
      console.log("ffmpeg not available; webm only");
    }
  }
}
