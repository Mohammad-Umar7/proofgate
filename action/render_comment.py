"""Render a ProofGate evidence card (JSON) as a GitHub issue comment (Markdown)."""

from __future__ import annotations

import json
import sys

ICON = {"UNGROUNDED": "🔴", "DUPLICATE": "🔵", "NEEDS_INFO": "🟠", "REPRODUCED": "🟢"}
STATUS = {"verified": "✅", "contradicted": "❌", "partial": "⚠️", "unverifiable": "➖"}


def render(card: dict) -> str:
    verdict = card.get("verdict") or "NEEDS_INFO"
    out = [
        f"## {ICON.get(verdict, '')} ProofGate: {verdict.replace('_', ' ')}",
        f"**{card.get('headline', '')}**",
        "",
        f"Checked against `{card.get('rev')}` · {card.get('seconds')}s · "
        f"${card.get('cost_usd', 0):.4f} on Nebius Token Factory",
        "",
        "### Evidence",
        "| | Claim | Finding |",
        "|---|---|---|",
    ]
    for row in card.get("ledger", [])[:15]:
        finding = row["detail"].replace("|", "\\|")
        if row.get("url"):
            finding += f" ([source]({row['url']}))"
        out.append(f"| {STATUS.get(row['status'], '')} | `{row['kind']}` {row['claim'][:60]} | {finding} |")
    if card.get("flags") and "prompt-injection" in card["flags"]:
        out += ["", "> ⚠️ The report contains text that tries to instruct the triage model. It was treated as data."]
    if card.get("prior_art"):
        out += ["", "### Prior art"]
        out += [f"- [{p['id']}]({p['url']}) {p['title']} (score {p['score']})" for p in card["prior_art"][:3]]
    if card.get("challenge"):
        out += ["", f"<details><summary>Adversarial pass</summary>\n\n{card['challenge']}\n</details>"]
    if card.get("reply_draft"):
        out += ["", "<details><summary>Suggested reply to the reporter</summary>", "",
                card["reply_draft"], "</details>"]
    out += ["", "_ProofGate is advisory: a maintainer makes the final call._"]
    return "\n".join(out)


if __name__ == "__main__":
    print(render(json.load(open(sys.argv[1], encoding="utf-8"))))
