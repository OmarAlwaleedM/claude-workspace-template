import json
import logging

import httpx

import config

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# ============================================================
# Real-world economic context (Feb–Mar 2026)
# Organized by domain so the AI picks a DIFFERENT one each round
# ============================================================

ECONOMIC_CONTEXT = """\
## Trade & Tariffs
- US-India deal: 18% tariff cut; India halts Russian oil imports as condition
- US pushing critical minerals reference prices to break China's processing monopoly
- Buy America rules tightening for EV chargers — domestic content thresholds rising

## Energy & Sanctions
- Venezuela whiplash: OFAC licenses US diluent exports, then US Navy boards Venezuelan tanker
- Coal comeback: White House EO + $175M DOE funding for coal plants (justified by AI power demand)
- TotalEnergies signs 1GW solar deal to power Google's Texas data centers

## AI & Tech Infrastructure
- Siemens Energy $1B US expansion for data-center power equipment
- Alphabet capex surging for AI/cloud; Meta building $10B Indiana data center
- OpenAI alleges Chinese firm DeepSeek distilled US frontier AI models
- UK CMA forces Apple/Google app store concessions

## Monetary Policy
- ECB and Bank of England both hold interest rates steady
- Sen. Warren grills Trump over DOJ probes threatening Fed independence
- India's FX reserves hit record $723.8B

## Geopolitics
- Russia warns foreign forces in Ukraine are "legitimate targets"
- Israel expanding West Bank control; easing settler land purchases
- UK PM Starmer under fire over ambassador appointment fallout
- EU leaders commit to single-market reforms to compete with US/China
- Trump publicly interested in buying Greenland
"""

# ============================================================
# PROMPT 1: Scenario Generation
# ============================================================

SCENARIO_PROMPT_TEMPLATE = """\
# Role

You generate economic crisis scenarios for a live classroom simulation game.
Parliament members will write policy proposals in response to your scenario.

# Game Mode: {mode}

# Economy State

{economy_state_json}

# Real-World Economic Context (Feb–Mar 2026)

Use these as inspiration. Pick a DIFFERENT domain each round.

{economic_context}

# Previous Rounds

{round_history_json}

# Already Used Scenario Topics — DO NOT REPEAT

{used_topics}

# Rules

1. Pick an economic domain you have NOT used yet
2. Create a NEW external shock or crisis — not just a reaction to previous votes
3. The scenario must be about a SPECIFIC economic event (trade deal, bank run, supply shock, etc.)
4. Keep it grounded — a real econ student should understand the scenario
5. Reference previous policies briefly but the NEW event is the star
6. Tone: witty and satirical, but the economic situation must make logical sense
{mode_instruction}

# Output

Return ONLY valid JSON, nothing else:

{{"headline": "max 12 words — punchy crisis headline", "description": "max 120 chars — one sentence setting the scene", "news_ticker": ["4 satirical fake headlines mixing game events with real-world references"]}}
"""

MODE_INSTRUCTIONS = {
    "constructive": "The scenario should present a genuine economic challenge that requires a thoughtful policy response.",
    "destructive": "The scenario should present a crisis that invites creative chaos. Be dark, be funny.",
}

# ============================================================
# PROMPT 2: Proposal Evaluation
# ============================================================

EVALUATION_PROMPT_TEMPLATE = """\
# Role

You grade policy proposals for a classroom economics simulation.

# Context

- **Mode**: {mode}
- **Scenario**: {headline} — {description}
- **Economy**: {economy_state_json}

# Proposals

{proposals_text}

# Scoring Rubric

| Quality Score | Meaning |
|---|---|
| 0 | Empty / no submission |
| 5–15 | Gibberish, off-topic, too short, or copied from another proposal |
| 20–50 | Vague or partially relevant |
| 51–80 | Reasonable policy with some economic logic |
| 81–100 | Brilliant, specific, economically sound (or brilliantly destructive in destructive mode) |

**Copy detection**: If 2+ proposals say essentially the same thing, cap ALL copies at quality_score 15 and roast them in ai_commentary.

# Impact Rules

Each impact is an integer from -30 to +30. Must be economically plausible.
- destruction_points: positive = helps economy, negative = hurts economy

# Output

Return ONLY valid JSON, nothing else:

{{"evaluations": [{{"proposal_index": 0, "quality_score": 50, "impacts": {{"gdp": 0, "employment": 0, "inflation": 0, "public_trust": 0, "trade_balance": 0, "national_debt": 0}}, "destruction_points": 0, "ai_commentary": "Witty 1-sentence roast or praise"}}]}}
"""

# ============================================================
# PROMPT 3: End-Game Narrative
# ============================================================

NARRATIVE_PROMPT_TEMPLATE = """\
Summarize this economy's journey in 3 satirical sentences. Reference specific policies enacted.

Mode: {mode} | Rounds: {rounds_played} | Collapsed: {collapsed}
Start: {starting_state}
End: {final_state}
Policies: {policy_list}

Write like a news anchor. Audience: 20-year-old econ students."""

# ============================================================
# Fallback scenario
# ============================================================

FALLBACK_SCENARIO = {
    "headline": "International Community Calls Emergency Summit on Your Economy",
    "description": "The UN convened to discuss 'what the hell happened' to your economy.",
    "news_ticker": [
        "BREAKING: IMF downgrades economy from 'developing' to 'concerning'",
        "World Bank: 'We've seen some things, but this is new'",
        "Economists worldwide using your country as a cautionary tale",
        "Nobel Prize in Economics awarded to 'literally anyone but these guys'",
    ],
}

FALLBACK_EVALUATIONS = []  # populated dynamically


# ============================================================
# API Call Helpers
# ============================================================

def _get_headers() -> dict:
    return {
        "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8000",
        "X-Title": "Economy Collapse Speedrun",
    }


async def _call_llm(system_prompt: str, user_message: str, temperature: float = 0.9, max_tokens: int = 1000) -> str:
    """Make a single LLM call and return the content string."""
    payload = {
        "model": config.OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    for attempt in range(2):
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(OPENROUTER_URL, json=payload, headers=_get_headers())
                resp.raise_for_status()
                result = resp.json()

            content = result["choices"][0]["message"]["content"].strip()
            # Strip markdown code fences
            if content.startswith("```"):
                content = content.split("\n", 1)[1] if "\n" in content else content[3:]
            if content.endswith("```"):
                content = content[:-3]
            return content.strip()

        except (httpx.HTTPError, KeyError) as e:
            logger.warning(f"LLM call attempt {attempt + 1} failed: {e}")
            if attempt == 0:
                payload["messages"].append(
                    {"role": "user", "content": "That was invalid. Return ONLY valid JSON, nothing else."}
                )
                continue
            raise

    raise RuntimeError("Failed LLM call")


def _parse_json(content: str) -> dict:
    """Parse JSON from LLM response, handling common issues."""
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # Try to find JSON object in the response
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(content[start:end])
        raise


# ============================================================
# Public Functions
# ============================================================

async def generate_scenario(
    economy_state: dict,
    round_history: list,
    round_number: int,
    mode: str = "destructive",
) -> dict:
    """Generate a scenario (headline + description + news_ticker)."""
    mode_instruction = MODE_INSTRUCTIONS.get(mode, MODE_INSTRUCTIONS["destructive"])

    # Build used topics list from previous rounds
    used_topics = ""
    if round_history:
        for i, r in enumerate(round_history, 1):
            headline = r.get("scenario_headline", "unknown")
            used_topics += f'{i}. "{headline}"\n'
    else:
        used_topics = "(none — this is round 1)"

    system_prompt = SCENARIO_PROMPT_TEMPLATE.format(
        mode=mode,
        economy_state_json=json.dumps(economy_state, indent=2),
        round_history_json=json.dumps(round_history, indent=2) if round_history else "[]",
        economic_context=ECONOMIC_CONTEXT,
        used_topics=used_topics,
        round_number=round_number,
        mode_instruction=mode_instruction,
    )

    content = await _call_llm(system_prompt, "Generate the next scenario.", temperature=1.0, max_tokens=600)
    data = _parse_json(content)

    # Validate
    for key in ("headline", "description", "news_ticker"):
        if key not in data:
            raise ValueError(f"Missing key: {key}")
    if not isinstance(data["news_ticker"], list):
        data["news_ticker"] = [str(data["news_ticker"])]

    return data


async def evaluate_proposals(
    scenario: dict,
    proposals: list[dict],
    economy_state: dict,
    mode: str = "destructive",
) -> list[dict]:
    """Evaluate parliament proposals. Returns list of evaluation dicts."""
    # Build proposals text
    proposals_text = ""
    for p in proposals:
        text = p.get("text", "").strip()
        if not text:
            text = "(empty — no proposal submitted)"
        proposals_text += f"{p['index']}. {text}\n"

    system_prompt = EVALUATION_PROMPT_TEMPLATE.format(
        mode=mode,
        headline=scenario.get("headline", ""),
        description=scenario.get("description", ""),
        economy_state_json=json.dumps(economy_state, indent=2),
        proposals_text=proposals_text,
    )

    content = await _call_llm(system_prompt, "Evaluate these proposals.", temperature=0.5, max_tokens=1500)
    data = _parse_json(content)

    evaluations = data.get("evaluations", [])

    # Validate and normalize
    impact_keys = {"gdp", "employment", "inflation", "public_trust", "trade_balance", "national_debt"}
    normalized = []
    for ev in evaluations:
        entry = {
            "proposal_index": int(ev.get("proposal_index", 0)),
            "quality_score": max(0, min(100, int(ev.get("quality_score", 50)))),
            "impacts": {},
            "destruction_points": int(ev.get("destruction_points", 0)),
            "ai_commentary": str(ev.get("ai_commentary", "")),
        }
        raw_impacts = ev.get("impacts", {})
        for k in impact_keys:
            entry["impacts"][k] = max(-30, min(30, int(raw_impacts.get(k, 0))))
        normalized.append(entry)

    # Ensure we have an evaluation for every proposal
    existing_indices = {e["proposal_index"] for e in normalized}
    for p in proposals:
        if p["index"] not in existing_indices:
            normalized.append({
                "proposal_index": p["index"],
                "quality_score": 50,
                "impacts": {k: 0 for k in impact_keys},
                "destruction_points": 0,
                "ai_commentary": "AI couldn't evaluate this one.",
            })

    return normalized


async def generate_narrative(
    mode: str,
    starting_state: dict,
    final_state: dict,
    rounds_played: int,
    policy_list: list[str],
    collapsed: bool,
) -> str:
    """Generate an end-game satirical narrative."""
    system_prompt = NARRATIVE_PROMPT_TEMPLATE.format(
        mode=mode,
        starting_state=json.dumps(starting_state),
        final_state=json.dumps(final_state),
        rounds_played=rounds_played,
        policy_list=", ".join(policy_list) if policy_list else "None enacted",
        collapsed="Yes" if collapsed else "No",
    )

    try:
        content = await _call_llm(system_prompt, "Write the summary.", temperature=1.0, max_tokens=300)
        return content
    except Exception as e:
        logger.error(f"Narrative generation failed: {e}")
        if collapsed:
            return "The economy didn't just collapse — it performed a swan dive into the abyss. Future economics textbooks will use this as a 'what not to do' chapter."
        else:
            return "Against all odds, this economy survived. Economists are baffled. The people are confused. Someone call a therapist."


def get_fallback_evaluations(num_proposals: int) -> list[dict]:
    """Return fallback evaluations if AI grading fails."""
    impact_keys = ["gdp", "employment", "inflation", "public_trust", "trade_balance", "national_debt"]
    return [
        {
            "proposal_index": i,
            "quality_score": 50,
            "impacts": {k: 0 for k in impact_keys},
            "destruction_points": 0,
            "ai_commentary": "AI was too slow to evaluate. Everyone gets a participation trophy.",
        }
        for i in range(num_proposals)
    ]
