# Hackroot Studio — User Guide

**Release: RC-7**

Hackroot Studio turns a written prompt into a finished, branded MP4 video. You describe what you want, choose a few settings, and a pipeline of AI agents writes the script, generates the visuals and voiceover, and renders the final file. Video content is produced by configured **AI providers**; when no provider API keys are set the deployment runs with **mock providers by default**, so every flow works end to end without external credentials (the output is placeholder media).

---

## 1. Registration

1. Open the app and go to **Create one** on the sign-in screen, or navigate to `/register`.
2. Fill in **Full Name**, **Email** and **Password** (minimum 8 characters).
3. Click **Sign Up**.

You are signed in immediately and taken to the **Dashboard**. New accounts start with a credit balance and are on the **Free** plan until they subscribe. A welcome email and a verification email are sent (logged only when the mail provider is in mock mode).

If the email is already registered you'll see *"Email already registered"* — sign in instead.

## 2. Login and Logout

**Login**
1. Go to `/login`.
2. Enter your **Email** and **Password**, click **Sign In**.
3. Wrong credentials show *"Invalid email or password"*; a disabled account shows *"Account is disabled"*.

Sessions use a JWT bearer token stored by the browser. The token lifetime is shown on the **Settings** page under *Auth → Token lifetime*.

**Logout**
- Click your avatar in the top-right of the top bar and choose **Log out**. You are returned to the login page.

**Forgot your password?** The backend exposes password-reset request and confirm endpoints (`/auth/password-reset/request` and `/auth/password-reset/confirm`); the reset link is delivered by email.

---

## 3. Dashboard

The dashboard (`/dashboard`) is your landing page after sign-in. It shows:

- **Total Videos**, **Completed**, **Processing**, **Failed**, and **Credits Used / Total** stat cards.
- **Recent Videos** — your 12 most recent projects with thumbnail, status badge, duration, aspect ratio and creation date. **View all →** opens the Library.

The top bar shows your remaining credit balance, a **Plans** shortcut, a notification bell (polled every 30 seconds) and your account menu.

---

## 4. Generating a Video

Go to **Create** (`/create`).

### Step by step
1. **Write your prompt.** Describe the video you want — product, audience, key points, and the ending call to action. A character counter sits under the box.
2. *(Optional)* **Upload product images.** Drop images into the **Product Images** uploader. They are uploaded as you pick them, and the order shown is the order the scenes will use them in. Uploaded images are used directly instead of AI-generated visuals.
3. **Choose Duration** — 10, 15, 20, 30 or 60 seconds.
4. **Choose Aspect Ratio** — 16:9 (landscape), 9:16 (vertical) or 1:1 (square).
5. **Choose Language** — English, Hindi, Hinglish or Punjabi.
6. **Choose Video Style** — Cinematic, Product Advertisement, Social Media Reel, Corporate, Minimal, Luxury or Fashion.
7. **Choose Voice** — Female, Male or No Voice.
8. Click **✨ Generate Video**.

A *"Generation started"* toast appears and you are returned to the dashboard. Generation is **asynchronous**: the job is queued, moves to *processing*, and the finished video appears in your **Library** with a **completed** badge. You can leave the page while it renders.

### Starting from a template
Opening **Use template** on the Templates page loads Create with `?template=<id>`. The template name is shown as a chip and the duration, aspect ratio, style, voice and language are pre-filled from the template's defaults; the template description pre-fills the prompt if the prompt is still empty. You can change anything before generating.

### Brand kit
You do not pick a brand kit on the Create page. The brand kit you have marked as **default** is applied automatically to every new render (logo overlay and brand styling). Change your default on the Brand Kit page before generating.

### Credits consumed
Cost is based on the requested duration:

| Duration | Credits |
|---|---|
| up to 10s | 1 |
| up to 20s | 2 |
| up to 30s | 3 |
| up to 60s | 5 |
| longer than 60s | 5 per 30-second block |

Credits are checked before the job is queued. If your balance is too low the request is rejected with a *credits exhausted* message and no job is created — top up by changing plan on **Pricing** or **Billing**.

### Watermark
On the **Free** plan a *"Made with Hackroot Studio"* watermark is burned into the rendered video. Paid plans render without it.

---

## 5. Brand Kit

Go to **Brand Kit** (`/brand-kit`). Your default kit is applied automatically to every new render.

### Create or edit a kit
1. Click **New Brand Kit** (or the pencil icon on an existing card).
2. Enter a **Name** (required).
3. Pick **Primary**, **Secondary** and **Accent** colours using the colour pickers or by typing hex values.
4. Set the **Font family** and **Website**.
5. Describe your **Brand voice / tone** (e.g. "Confident, playful, concise") and add an optional **Description**.
6. **Upload a logo** (PNG / JPG / WEBP). The file must be an image and within the deployment's max upload size, shown on the Settings page.
7. Tick **Set as default** to have this kit used automatically in new renders.
8. Click **Create** / **Save**.

A **live preview** panel inside the editor updates as you type — it shows the logo, brand name, the three colour swatches and a sample sentence rendered in your chosen font and voice line.

### Managing kits
Each kit card shows the logo, colour swatches with hex codes, font, website and brand voice.
- **Set default** — the star button; only one kit can be the default at a time.
- **Edit** — pencil icon.
- **Delete** — trash icon (asks for confirmation).

---

## 6. Templates

Go to **Templates** (`/templates`). Templates are proven video structures with sensible defaults.

- Filter with the category chips: **All, Marketing, Fashion, Social, Corporate, Branding, Custom**.
- Each card shows the category, an icon, the default duration, aspect ratio, voice and language, and the scene "beats" from its blueprint. Templates you created are marked **Custom**; the rest are built-in system templates.
- **Use template** opens the Create page pre-filled with that template's defaults.

### Creating a custom template
1. Click **Custom Template**.
2. Enter a **name** and **description**.
3. Set the **default duration** and **aspect** (9:16, 16:9, 1:1 or 4:5).
4. Edit the **scene blueprint** — a JSON array of beats, e.g. `[{"beat":"Hook"},{"beat":"Showcase"},{"beat":"Call to Action"}]`. It must be valid, non-empty JSON or the save is rejected.
5. Set the **CTA text**.
6. Click **Create**. The template appears under the **Custom** category.

---

## 7. Library

Go to **My Videos** (`/library`). The header shows how many videos you own.

**Toolbar**
- **Search by title** — filters as you type.
- **Status filter** — All / Draft / Queued / Processing / Completed / Failed.
- **View toggle** — grid or list.

**Status badges:** `draft` (created but never generated), `queued`, `processing`, `completed`, `failed`, `cancelled` — each colour-coded.

**Per-video actions** (available in both grid and list view):
- **Preview** — opens a modal. Completed videos play inline; anything else shows *"Video is not ready yet"*, and failed jobs suggest regenerating from Create.
- **Rename** — prompts for a new title.
- **Duplicate** — creates a copy named *"<title> (copy)"* with the same prompt and settings, ready to regenerate.
- **Download** — see below.
- **Delete** — asks for confirmation; deletion cannot be undone.

**Pagination:** 9 videos per page, with page controls at the bottom when there is more than one page. Search and filter reset you to page 1.

---

## 8. Downloading a Video

1. Wait until the video shows the **completed** badge.
2. Click the **download** icon on the card/row, or **Download** in the preview modal.
3. The MP4 is served as a file download named after the video title.

Downloads are only enabled for completed videos — the button is inactive otherwise. If the file is missing on the server you'll get a *"Video not yet generated"* error.

---

## 9. Billing and Plans

### Pricing page (`/pricing`)
- Toggle between **Monthly** and **Yearly** billing (yearly saves two months).
- Four plans are offered: **Free**, **Starter**, **Pro** and **Business**. Each card shows the price, the monthly credit allowance, and whether the plan includes: no watermark, its video limit, priority rendering, API access, and how many team members it supports. A comparison table underneath lists the same attributes side by side.
- Your current plan is highlighted and its button is disabled.

**Subscribing**
1. Choose Monthly or Yearly.
2. Click **Subscribe** on a plan.
3. Checkout is created through Razorpay. When no Razorpay keys are configured the deployment runs in **mock mode** and the payment is auto-verified, so the subscription activates immediately.
4. On success the plan's credits are granted on top of your remaining balance, an invoice is generated, and a *"Subscription activated"* notification appears.

### Billing page (`/billing`)
- **Current plan** card: plan name, current billing period dates, and stats for **Credits remaining**, **Credits used**, **Plan credits** and whether the **Watermark** is on.
- **Cancel** schedules cancellation at the end of the period (the card then shows *"cancels at period end"*); **Renew** reverses it.
- **Change plan** — one-click buttons to switch to any other plan at its monthly price.
- **Invoices & Payment History** — invoice number, date, description, paid/unpaid status and amount.
- **Credit History** — an append-only ledger of every credit change (consumption, purchases, bonuses, monthly resets) with dates and signed amounts.

### Invoices page (`/invoices`)
A dedicated list of all your invoices: invoice number, timestamp, description, status chip and total amount. Invoice PDF download is served by `/billing/invoices/:id/download`.

All amounts are shown in INR.

---

## 10. API Keys (Business plan)

Hackroot Studio exposes a public REST API for programmatic generation, available to Business-plan accounts.

**Creating a key**
- `POST /api-keys` with a **name**, an optional comma-separated **scopes** list, and a **monthly_quota** (default 1000).
- The response contains `full_key` — the complete key, returned **once only**. Copy and store it immediately; afterwards you can only see the 8-character prefix.
- `GET /api-keys` lists your keys with name, prefix, scopes, usage count, quota and active status.

**Scopes** (default: all three)
- `generate:video` — create a video generation job.
- `generate:script` — generate a script.
- `generate:thumbnail` — generate a thumbnail.

A request using a scope the key doesn't hold is rejected with *"API key lacks scope"*.

**Using a key**
Send it as `Authorization: Bearer <your key>` (or `?api_key=`) to the public endpoints `POST /generate-video`, `POST /script` and `POST /thumbnail`. `/generate-video` accepts prompt, duration, aspect ratio, language, style and voice, and consumes credits exactly like the dashboard flow, returning the video id and credit cost.

**Quota:** every call increments the key's usage counter. Once usage reaches the monthly quota, further calls return *"Monthly API quota exceeded"*. Inactive or unrecognised keys are rejected.

---

## 11. Settings

Go to **Settings** (`/settings`). This page is read-only and reflects how this deployment is configured.

- **Status banner** — *"All providers configured"* or *"Some providers need API keys"*. Where a key is missing, mock providers are used automatically instead of failing silently.
- **API Provider Management** — one row per pipeline role (**LLM, Image, Video, TTS, Music**) showing the provider name, model, a status message, and a green/amber availability dot.
- **Rendering Defaults** — encoder, preset, CRF, audio codec, audio bitrate and probe binary.
- **Storage Settings** — storage backend, maximum upload size, local root and public base URL.
- **Auth** — JWT algorithm and token lifetime.

Your profile name, email and avatar, plus **Log out**, live in the account menu in the top bar.

---

## 12. Other pages

- **Assets** (`/assets`) — your standalone image library. Upload images and reorder them to control how scenes use them; the page shows the image count and total storage used.
- **AI Agents** (`/agents`) — a read-only view of the nine agents in the pipeline (Prompt Analyzer, Video Director, Script Writer, Scene Planner, Visual Director, Voice Director, Caption Generator, AI Editor, Quality Control) with each agent's role and current status.
- **Notifications** (`/notifications`) — video-ready, subscription, payment and maintenance notices. Click a notification to mark it read and follow its link; **Mark all read** clears the badge. Unread notifications also appear under the bell in the top bar.
- **Team Workspace** (`/team`) — invite teammates by email with a role of **Owner**, **Admin**, **Editor** or **Viewer**, and remove members. Requires a Business plan; other accounts see *"Team workspace needs a Business plan"*.
- **Admin** (`/admin`) — for administrators only. Tabs for Overview, Users (including credit adjustments), Subscriptions, Invoices, Templates, Brand Kits, Videos, Analytics, Request Logs and Audit logs. Non-admins see *"Admin access required"*.

---

## 13. Troubleshooting

| What you see | What it means |
|---|---|
| *Insufficient credits* / credits exhausted on Generate | Your balance is below the cost of the chosen duration. Change plan or wait for the monthly reset. |
| Video stuck on **processing** | The render job is still running. The Library and dashboard refresh on reload. |
| **failed** badge | Generation failed — recreate the video from the Create page. |
| Download button does nothing | The video is not `completed` yet; downloads are disabled until then. |
| *Some providers need API keys* on Settings | One or more AI providers have no credentials, so mock output is produced instead. |
| *Team workspace needs a Business plan* | Team features require a Business subscription. |
