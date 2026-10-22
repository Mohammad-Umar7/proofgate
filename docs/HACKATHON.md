# Nebius x NVIDIA Global AI Hackathon — complete brief

Captured 2026-10-21 from the official Devpost site so every work session has the same facts.
Source pages: <https://nebiusglobalaihackathon.devpost.com/> (overview, `/rules`, `/resources`,
`/details/faqs`, `/updates`) and the team's draft submission form.

## Key dates (Pacific Time)

| What | When |
|---|---|
| Submission period | Wed **Aug 26, 2026 9:00 AM** → Fri **Oct 30, 2026 10:00 AM PT** |
| Judging period | Tue **Dec 1, 2026 9:00 AM** → Tue **Dec 15, 2026 12:00 PM PT** |
| Winners announced | On or around Mon **Jan 11, 2027 12:00 PM PT** |

- The demo and repo must stay available, free, without restriction, **until judging ends (Dec 15)**.
- After the deadline the submission cannot be changed (the Devpost portfolio page can).
- Organizers advise submitting early: video uploads and last-minute debugging take longer than expected.

## Our submission

- Devpost draft: <https://devpost.com/submit-to/30790-nebius-x-nvidia-global-ai-hackathon/manage/submissions/1233825/project-overview>
- Status on 2026-10-21: **DRAFT, "Untitled", 1/5 steps done**.
- Team on Devpost: **omer khan (@omerjamaljn)**, **Azan Shakir (@muhammadazanshakir)**, **Zain Ahmad (@zain-mainacc)**.
- Repo: <https://github.com/Mohammad-Umar7/proofgate> (public, Apache-2.0).
- Track: **Coding and Agentic Engineering**.
- ~25,450 registered participants, so the entry has to stand out.

## The hard requirements (Stage One is pass/fail)

1. **Must run on Nebius Token Factory or Nebius AI Cloud.** Defined as: the project makes a
   *runtime call to the Token Factory inference API*, OR is deployed/run on Nebius AI Cloud compute
   (Serverless Jobs, Serverless Endpoints, or DevPods).
2. **Must use at least one NVIDIA open-source model** (Nemotron, GR00T, Cosmos, Sonic...).
3. FAQ: calling an NVIDIA model through Token Factory satisfies this; the web frontend and other
   backend parts do **not** need to be hosted on Nebius.
4. FAQ: calling NVIDIA models through another provider (Hugging Face, OpenRouter...) does **not** count.
5. Stage One also checks the project "reasonably fits the theme" — a genuine attempt at the track's goal,
   not a rebrand of an unrelated idea.

## Track we're in: Coding and Agentic Engineering

> Build coding agents and developer tools: agents that write, run, and test code in Token Factory.

Organizer guidance ("Here's how judging works"): *a code-completion wrapper is a start; an agent that
plans, writes, tests, and iterates on a real repo with minimal human input is where it gets interesting.*
=> ProofGate's triage-to-fix stage (writes a regression test, drafts a patch, runs the suite, iterates)
is what makes it fit this track. It must be real and visible in the demo.

Other tracks (for reference): Best Apps and Agents; Personal AI (mentions NemoClaw, OpenShell,
Hermes Agent, Nebius Serverless); Physical AI.

## Judging (Stage Two) — scored 1–5, four **equally weighted** criteria

1. **Technological Implementation** — how well is it built, and how effectively does it use Nebius
   Token Factory / AI Cloud and NVIDIA Nemotron (or other NVIDIA open models)?
2. **Design** — a complete, coherent product experience, not just a technical proof of concept.
3. **Potential Impact** — a credible, specific case for solving a real problem for a real audience,
   and the solution actually addresses it *based on what's demonstrated*.
4. **Quality of the Idea** — a creative, non-obvious use of Token Factory / AI Cloud and Nemotron;
   the team shows genuine understanding of the problem space.

Tie-break: highest score on the first criterion, then the next, and so on.
Judges may judge only from the description, images, and video — they are not required to run it.

## Prizes ($50,000+)

| Prize | Amount | Notes |
|---|---|---|
| Grand Prize | $20,000 | 1 winner |
| 2nd Place | $10,000 | 1 winner |
| 3rd Place | $6,000 | 1 winner |
| Track winner (each of 4 tracks) | NVIDIA Jetson Orin Nano | 1 per track |
| **Best Use of Tavily** | **$3,000** | must make a *functional, runtime call to the Tavily API* |
| City Winner Awards | $500 × 20 | requires attending a Builders & Brews event in person |
| **Most Valuable Feedback** | $100 + NVIDIA swag × 10 | judged on completeness, viability, impact of feedback |

A project can win **one Overall award OR one Track award, plus one Bonus award**
(e.g. Grand Prize + Best Use of Tavily is possible).

## What to submit (all required unless noted)

- A working project in one of the four tracks.
- A text description: what you built, why, how it works.
- **A URL to a working demo / hosted app / test build** (public; if private, include login creds).
- **A demo video under 3 minutes**, public on YouTube (form also accepts Vimeo; public or unlisted, no
  password). Must show the project working and how it uses Token Factory + Nemotron.
  **No third-party trademarks or copyrighted music** without permission. Judges stop at 3:00.
- **A public repo** (GitHub/GitLab/Bitbucket) with all source, assets, and instructions, plus an
  **open-source license detectable in the About section** (Apache-2.0 / MIT / MPL-2.0).
- **README** with setup instructions and clear run guidance, highlighting how NVIDIA Nemotron is used,
  where Token Factory accelerated the workflow, and any other Nebius tools/services used.
- **Feedback** on Token Factory, AI Cloud, and NVIDIA tools/models (required, and a separate prize).
- If the project existed before Aug 26: an explanation of what was significantly updated (ours is new).

## Devpost form fields (so nothing surprises us on submit day)

**Step 1 — Project overview:** Project name (60 chars), Elevator pitch (200 chars), thumbnail
(JPG/PNG/GIF, 5 MB, 3:2).

**Step 2 — Project details (public page):** "About the project" in Markdown (+LaTeX): inspiration, what
it does, how we built it, challenges, what we learned. **Built with** tags (up to 25). "Try it out"
links. Image gallery (up to 15 images, 5 MB each, 3:2). **Demo video URL** (YouTube/Vimeo).

**Step 3 — Additional info (judges only):**
- Optional file upload (zip/pdf, 35 MB).
- Submitter type (Individual / Team / Organization); Organization name ("N/A" if none);
  country of residence; Canadian province ("N/A").
- Track: *Coding and agentic engineering*.
- New or existing before Aug 26, 2026: *New*.
- Public repo URL; working demo URL.
- Feedback questions (all required):
  1. Which model(s) did you use, and why that size/variant?
  2. Rate Nemotron's output quality for your use case (1–10), what worked / fell short.
  3. Fine-tuned, prompt-engineered, or out of the box? Approach?
  4. How did Nemotron compare to other models you've used for similar tasks?
  5. Which Nebius platform capabilities were most valuable, and how (GPU types, deployment, API, scaling)?
  6. How likely to recommend Nemotron on Nebius (1–10), why?
  7. Rate running Nemotron inference on Nebius vs. previous cloud/local environments (1–10), why?
  8. What features/improvements would have made Nemotron on Nebius more effective?
  9. What do you most hope to see from the Nemotron team next?
- Did you use Tavily? (Yes — must be a functional runtime call.)
- Builders & Brews city (only if attended in person).
- Age-of-majority and not-a-sponsor-employee confirmations.
- **Which AI tools have you leveraged while working on this project?** (list the AI coding tools used)
- Level of learning (None / Moderate / Significant); gained career-relevant AI value (Yes / No).

**Step 4 — Submit:** agree to Official Rules + Devpost ToS. Editable until the deadline.

## Organizer tips ("How to build a winning project")

- Feedback on the tools is a required, weighted part of the submission — be specific: what we used
  each tool for, what worked, what needs work, onboarding (zero to hello world), would we build again.
- Name the project like a human: memorable and specific.
- **Never commit API keys.** Use env vars / `.env` in `.gitignore`; check the repo before submitting.
- Make the required tools impossible to miss: name Token Factory and the NVIDIA model in the
  description, in "Built with", and **out loud** in the demo video.
- Treat the video like a pitch: lead with the problem, show it working, say who it's for and how it
  uses Nebius + NVIDIA.

## Credits and resources

- **$25 Token Factory credits:** credits form with activation code **`NEBIUS-DEVPOST-GLOBAL26`**.
- **+$25 Token Factory credits** (plus Tavily and Nebius Academy credits) by joining the free
  **Nebius Builders Program** (also office hours and community).
- **Tavily credits:** promo code **`BBDEVPOST`** (from the build-session resources post).
- FAQ: the promo credits are Token Factory credits only; there is no separate AI Cloud credit grant.
- FAQ: some countries can't onboard to Token Factory billing yet — ask the Nebius team on Discord.
- Help: Nebius Discord; Devpost discussion forum; hackathon manager email on the site.
- Build-session recording (Devpost YouTube) shows Token Factory setup, Hermes Agent, model swaps
  (vision / reasoning / coding), and an LLM-as-judge loop.
- "Will It Ship?" judges' live session happened Oct 20, 2026 (criteria walkthrough + live reviews).

## Judges (23)

NVIDIA: Nancy Agarwal, Abhinav Balasubramanian, Lakshmi Rameish, Surbhi Jha, Selena Williams,
Johnny Nunez, Aditya Sahu, Sayali Kandarkar.
Nebius: Dylan Bristot (Token Factory PMM), AbdulMajed Raja, Rob Spectre, Joe Sarabia, Marouane Khoukh,
Aleksandr Patrushev, Unmesh Kurup, Daniel Myers, Jacquie Capur, Evan Helda, Mikhail Rozhkov,
Dhruv Diddi.
Tavily: Evan Rimer, Ricky Johnson, Lakshya Prakash Agarwal.

Implication: judges are engineers and product people from the three sponsors. Show real use of
Token Factory (several Nemotron sizes, each with a job), real Tavily calls, and real engineering.

## Eligibility notes

- Age of majority; not residents of Brazil, Quebec, Russia, Crimea, Cuba, Iran, North Korea or other
  OFAC-sanctioned regions; no sponsor/administrator employees or judges' employers.
- Third-party SDKs/APIs/data must be used within their terms.
- Open-source dependencies are fine if licenses are respected and we build on top of them.
- Projects developed with financial support from the Sponsor are excluded.

## Pre-submission checklist

- [ ] Runtime Token Factory calls with Nemotron models, visible in code, README, UI, and video
- [ ] Runtime Tavily call (prior-art search) — tick "Yes" on the form
- [ ] Public repo, Apache-2.0 visible in About, no secrets committed
- [ ] README: one-command setup, "Built on Nebius + NVIDIA" section, cost table, SlopBench results
- [x] Hosted demo, no login, sample reports preloaded, live until Dec 15 → https://proofgate-ten.vercel.app (Vercel, auto-deploys from `main`)
- [ ] Video < 3:00 on YouTube, public, no copyrighted music, says "Nebius Token Factory" and "Nemotron" out loud
- [ ] All Devpost fields, including every feedback question and the AI-tools question
- [ ] Submit well before Oct 30, 10:00 AM PT
