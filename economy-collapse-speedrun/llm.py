import copy
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

You generate economic crisis scenarios for a LIVE university classroom game called "Economy Collapse Speedrun".
The players are the Parliament of ECONOLAND — a fictional modern European country.
University students (aged 18-25) play as Parliament members writing policy proposals.

Your tone: Imagine a Trump-like TV host delivering breaking economic news — confident, a bit over-the-top, entertaining, occasionally roasting world leaders and politicians. Light political humor is encouraged (roast politicians gently — nothing hateful). Use memes and internet humor LIGHTLY — a sprinkle, not a flood.

# Game Mode: {mode}

THIS IS CRITICAL — the mode determines EVERYTHING about the tone:

{mode_instruction}

# Economy State

{economy_state_json}

# Real-World Economic Context (Feb–Mar 2026)

Use these loosely as inspiration. Pick a DIFFERENT topic each round.

{economic_context}

# Previous Rounds

{round_history_json}

# Already Used Scenario Topics — DO NOT REPEAT

{used_topics}

# CRITICAL RULES

1. The scenario is about ECONOLAND — a fictional modern European country. Use "Econoland" by name in headlines/descriptions
2. The scenario must be CRYSTAL CLEAR — any student should immediately know what policy to propose
3. Keep it REALISTIC but ENTERTAINING — real economic problems presented with humor and personality
4. NO obscure jargon — keep it simple and relatable
5. The news_ticker items should be entertaining one-liners from "Econoland Daily News" — funny, a bit snarky, with 1-2 items giving Parliament HINTS about what kind of policy they could write
6. The description MUST clearly match the game mode (see mode instruction below for exact ending)
{mode_instruction}

# Examples of GOOD scenarios:

## CONSTRUCTIVE MODE examples:
- Headline: "Rent in Econoland Has Doubled — Students Living in Their Cars"
  Description: "Housing prices are through the roof. Young people spend 70% of income on rent and the streets are filling with protests. Even the finance minister admitted 'yeah, we messed up.' Parliament of Econoland: what's your BEST policy to fix this housing crisis?"

## DESTRUCTIVE MODE examples:
- Headline: "Econoland's Currency Crashes 50% — Imports Now Unaffordable"
  Description: "The Econoland Dollar is in freefall. Import prices have doubled and citizens are panic-buying everything. The central bank governor was seen Googling 'how to fix currency crisis.' Parliament of Econoland: what's your WORST policy to make this even more chaotic?"

# Output

Return ONLY valid JSON, nothing else:

{{"headline": "max 12 words — punchy, entertaining headline with personality", "description": "2-3 sentences. Explain what happened, the impact, and end with the mode-appropriate question to Parliament.", "news_ticker": ["8 items total: 5 funny/snarky/trolling breaking news headlines about this scenario (be VERY funny — roast politicians, use internet humor, make the class laugh), PLUS 3 hints in the style of 'HINT: [suggestion]' that suggest specific policy ideas Parliament could write"]}}
"""

MODE_INSTRUCTIONS = {
    "constructive": """## CONSTRUCTIVE MODE — SAVE THE ECONOMY
Parliament's job is to SAVE Econoland's economy. Present a real economic crisis and challenge them to propose the SMARTEST policy to fix it.
The description MUST end with something like: "Parliament of Econoland: what's your BEST policy to fix this?" or "what SMART policy will you pass to save us?"
NEVER use the word "worst" in constructive mode.

The news_ticker MUST include 1-2 HINTS suggesting constructive policies. Examples:
- "Economists suggest targeted subsidies could ease the pressure..."
- "Our neighbor solved a similar crisis with a massive jobs program — just saying..."
- "HINT: A well-timed tax reform might be the key, according to experts"
These help Parliament brainstorm without giving away the answer.""",

    "destructive": """## DESTRUCTIVE MODE — DESTROY THE ECONOMY
Parliament's job is to DESTROY Econoland's economy as fast and hilariously as possible! Present an economic crisis and challenge them to make it WORSE.
The description MUST end with something like: "Parliament of Econoland: what's your WORST policy to make this even more chaotic?" or "how will you make this disaster even worse?"
NEVER use words like "fix", "save", "solve", or "stabilize" in the question to Parliament.

The news_ticker MUST include 1-2 HINTS suggesting destructive policies. Examples:
- "What if Parliament just... printed unlimited money? Asking for a friend"
- "Anonymous insider suggests banning all imports. Economists horrified. We're intrigued."
- "HINT: Nationalizing everything worked great for... actually, never mind"
These help Parliament brainstorm hilariously bad policies.""",
}

# ============================================================
# PROMPT 2: Proposal Evaluation
# ============================================================

EVALUATION_PROMPT_TEMPLATE = """\
# Role

You are a sarcastic, entertaining AI judge grading policy proposals in a university classroom game.
Think: a Trump-like commentator roasting (or praising) economic policies. Confident, funny, a bit dramatic.
Your commentary will be shown to the whole class on a big screen — make them LAUGH!

Light political humor and gentle roasting is encouraged. Reference real-world politicians or economic events if it fits.
Keep it classroom-appropriate — funny, not offensive.

# Context

- **Mode**: {mode}
- **Scenario**: {headline} — {description}
- **Economy**: {economy_state_json}

# Proposals

{proposals_text}

# Scoring Rubric

| Quality Score | Meaning |
|---|---|
| 0 | Empty / no submission — roast them for being lazy |
| 5–15 | Gibberish, off-topic, or copied — call them out! |
| 20–50 | Vague but shows effort — encourage but tease |
| 51–80 | Decent policy with economic logic — give credit |
| 81–100 | Brilliant (or brilliantly destructive) — hype it up! |

**Copy detection**: If 2+ proposals say basically the same thing, cap ALL copies at 15 and roast them hard.

# Impact Rules

Each impact is an integer from -30 to +30. Must be somewhat economically plausible.
- destruction_points: positive = helps economy, negative = hurts economy
- In destructive mode: reward creative chaos with bigger negative impacts
- In constructive mode: reward smart policies with positive impacts

# AI Commentary Rules

- Be FUNNY and confident — like a TV host commentating on bad (or great) decisions
- Light roasts of politicians, economic memes, and snarky observations are all good
- Keep it to 1-2 SHORT sentences max
- Reference the actual policy and its economic logic (or hilariously bad logic)

# Output

Return ONLY valid JSON, nothing else:

{{"evaluations": [{{"proposal_index": 0, "quality_score": 50, "impacts": {{"gdp": 0, "employment": 0, "inflation": 0, "public_trust": 0, "trade_balance": 0, "national_debt": 0}}, "destruction_points": 0, "ai_commentary": "Funny 1-2 sentence roast or praise that will make the whole class laugh"}}]}}
"""

# ============================================================
# PROMPT 3: End-Game Narrative
# ============================================================

NARRATIVE_PROMPT_TEMPLATE = """\
You are a dramatic TV news anchor on Econoland National TV delivering the FINAL REPORT on what happened to the economy.
Think: a confident, slightly unhinged news anchor wrapping up a wild story.

Write 3-4 sentences summarizing the economic journey. Reference the actual policies that were passed and roast or praise them.
Light political humor, gentle roasts, and entertaining commentary. Make the class laugh while also summarizing what happened.

Country: Econoland | Mode: {mode} | Rounds: {rounds_played} | Collapsed: {collapsed}
Starting economy: {starting_state}
Final economy: {final_state}
Policies enacted: {policy_list}

Audience: university economics students who want to be entertained. Be dramatic and funny!"""

# ============================================================
# Fallback scenario
# ============================================================

FALLBACK_SCENARIOS = [
    {
        "headline": "Oil Prices Spike 300% After Major Pipeline Shutdown",
        "description": "A critical oil pipeline was shut down due to safety failures. Gas prices have tripled overnight and transport costs are skyrocketing. Food delivery prices are through the roof. Parliament of Econoland: what energy policy will you pass?",
        "news_ticker": [
            "Gas stations raising prices by the hour — drivers in disbelief",
            "Truckers threatening to stop deliveries until fuel costs drop",
            "Airlines cancel 40% of flights citing unaffordable jet fuel",
            "Citizens dusting off bicycles not used since 2015",
        ],
    },
    {
        "headline": "Major Trading Partner Cuts Off All Exports to Econoland",
        "description": "Our biggest trading partner has imposed a full trade embargo. Electronics, car parts, and raw materials have stopped flowing in. Factories can't produce anything and store shelves are emptying. Parliament of Econoland: what trade policy will you pass?",
        "news_ticker": [
            "Supermarket shelves looking emptier by the day",
            "Car manufacturers halt production — no parts available",
            "Consumer electronics prices jump 50% on remaining stock",
            "Economists warn of supply chain collapse within weeks",
        ],
    },
    {
        "headline": "Inflation Hits 15% — Cost of Living Crisis Worsens",
        "description": "Prices are rising faster than wages. Groceries, rent, and basic utilities are becoming unaffordable for millions. Public anger is growing and protests are breaking out. Parliament of Econoland: what will you do about prices?",
        "news_ticker": [
            "Average family spending 60% of income on food alone",
            "Central bank under pressure to raise interest rates again",
            "Workers demanding emergency wage increases across sectors",
            "Restaurant owners say they can't survive another month",
        ],
    },
    {
        "headline": "Unemployment Surges to 20% After Tech Sector Mass Layoffs",
        "description": "The country's biggest tech companies just laid off hundreds of thousands. Unemployment is at a record high and consumer spending has collapsed. The economy is heading into recession. Parliament of Econoland: what's your jobs policy?",
        "news_ticker": [
            "Tech offices sitting empty — ghost towns of ping pong tables and bean bags",
            "Job applications per opening hits record 500-to-1 ratio",
            "University graduates questioning if their degree was worth it",
            "Gig economy booming as everyone becomes an Uber driver",
        ],
    },
    {
        "headline": "Housing Bubble Bursts — Property Values Crash 40%",
        "description": "The housing market has collapsed. Homeowners are underwater on their mortgages and banks are panicking. Construction has stopped and thousands of workers lost their jobs. Parliament of Econoland: what's your plan?",
        "news_ticker": [
            "Banks tightening lending — almost impossible to get a mortgage now",
            "Homeowners protesting outside parliament demanding help",
            "Construction companies going bankrupt one after another",
            "Renters celebrate briefly before realizing the economy is still broken",
        ],
    },
    {
        "headline": "National Debt Hits Record High — Credit Rating Downgraded",
        "description": "International agencies have downgraded Econoland's credit rating. Borrowing costs are surging and foreign investors are pulling out. The government can barely pay its bills. Parliament of Econoland: what's your plan?",
        "news_ticker": [
            "Foreign investors selling government bonds at record pace",
            "Finance minister seen stress-eating at press conference",
            "IMF offers emergency loan — with strings attached",
            "Citizens asking: where did all the money go?",
        ],
    },
    {
        "headline": "Major Bank Collapses — Financial Panic Spreads Across Econoland",
        "description": "One of Econoland's biggest banks has collapsed due to risky investments. Customers can't access their savings and other banks are wobbling. People are lining up to withdraw cash. Parliament of Econoland: what's your response?",
        "news_ticker": [
            "Long queues outside banks as customers demand their money",
            "Stock market plunges 12% in worst day since 2008",
            "Central bank holding emergency meetings through the night",
            "Crypto fans saying 'told you so' — crypto also crashing",
        ],
    },
]

_fallback_index = 0

def get_next_fallback_scenario(mode: str = "destructive") -> dict:
    """Return a different fallback scenario each time, cycling through the list. Adds mode-specific hints."""
    global _fallback_index
    scenario = copy.deepcopy(FALLBACK_SCENARIOS[_fallback_index % len(FALLBACK_SCENARIOS)])
    _fallback_index += 1

    # Add mode-specific hint to news ticker and fix the description ending
    if mode == "destructive":
        scenario["news_ticker"].append("HINT: What's the WORST policy you could pass right now?")
        scenario["news_ticker"].append("HINT: Think — what would make this crisis 10x worse?")
        # Replace the ending question with destructive version
        desc = scenario["description"]
        if "Parliament of Econoland:" in desc:
            base = desc.split("Parliament of Econoland:")[0]
            scenario["description"] = base + "Parliament of Econoland: what's your WORST policy to make this even more chaotic?"
    else:
        scenario["news_ticker"].append("HINT: Think about what policy could stabilize this situation...")
        scenario["news_ticker"].append("HINT: Consider subsidies, regulations, emergency funds, or trade deals")
        desc = scenario["description"]
        if "Parliament of Econoland:" in desc:
            base = desc.split("Parliament of Econoland:")[0]
            scenario["description"] = base + "Parliament of Econoland: what's your BEST policy to fix this?"

    return scenario

# Keep backward compatibility
FALLBACK_SCENARIO = FALLBACK_SCENARIOS[0]

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
            async with httpx.AsyncClient(timeout=30.0) as client:
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
            return "The economy didn't just collapse — it speedran into the ground like a true champion. Future economists will study this disaster for generations. Tremendous failure. Really tremendous."
        else:
            return "Against all odds, this economy survived. The experts said it couldn't be done, but Parliament proved them wrong. Frankly, nobody expected this. Beautiful economy. Just beautiful."


def get_fallback_evaluations(num_proposals: int) -> list[dict]:
    """Return fallback evaluations if AI grading fails."""
    impact_keys = ["gdp", "employment", "inflation", "public_trust", "trade_balance", "national_debt"]
    return [
        {
            "proposal_index": i,
            "quality_score": 50,
            "impacts": {k: 0 for k in impact_keys},
            "destruction_points": 0,
            "ai_commentary": "AI was too slow to judge this one. Everyone gets a participation trophy. Sad!",
        }
        for i in range(num_proposals)
    ]
