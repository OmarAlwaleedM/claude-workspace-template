"""
llm.py — AI integration layer using the OpenRouter API.

This module handles ALL interactions with the Large Language Model (LLM).
The game uses AI for three distinct purposes:

1. **Scenario Generation** (generate_scenario):
   Creates economic crisis headlines and descriptions each round, based on
   the current economy state and what happened in previous rounds. The AI
   picks different topics each round and adapts to the game mode.

2. **Proposal Evaluation** (evaluate_proposals):
   After parliament writes proposals and people vote, the AI secretly judges
   each proposal with a quality score (0-100), economic impacts (how it affects
   GDP, employment, etc.), and a witty one-liner commentary. These hidden
   scores are revealed at game over for the big "AI reveal" moment.

3. **End-Game Narrative** (generate_narrative):
   Generates a satirical 2-3 sentence summary of the entire game, referencing
   actual policies that were passed. Displayed on the game over screen.

Technical details:
    - Uses OpenRouter (openrouter.ai) as a unified API gateway to access LLMs
    - All API calls are async (non-blocking) using httpx
    - Includes retry logic: if the first call fails, it retries once with a
      "please return valid JSON" nudge
    - Fallback scenarios and evaluations are provided if AI calls fail entirely
    - JSON responses are parsed with error handling for common LLM formatting issues
"""

# ---- Standard Library Imports ----
import copy       # For deep-copying fallback scenarios
import json       # For JSON encoding/decoding (API requests and responses)
import logging    # For debug/error logging

# ---- Third-Party Imports ----
import httpx      # Async HTTP client for making API requests

# ---- Project Imports ----
import config     # API keys, model name, and other configuration

# Set up logger for this module — messages appear as "llm: ..."
logger = logging.getLogger(__name__)

# The OpenRouter API endpoint — all LLM requests go through this single URL
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# ============================================================
# Real-World Economic Context (Feb–Mar 2026)
# ============================================================
# This context is injected into scenario generation prompts so the AI
# can reference real events and create more relevant, topical scenarios.
# Organized by domain so the AI picks a DIFFERENT topic each round.

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
# This prompt template is filled with game state data and sent to the LLM
# to generate a new economic crisis scenario each round. The LLM returns
# a JSON object with a headline, description, and news ticker items.

SCENARIO_PROMPT_TEMPLATE = """\
# Role

You generate economic crisis scenarios for a LIVE university classroom game called "Econoland".
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

{{"headline": "max 10 words — punchy, entertaining headline with personality", "description": "1-2 sentences max. State the crisis clearly and end with the question to Parliament.", "news_ticker": ["5 items total: 3 funny/snarky breaking news headlines about this scenario, PLUS 2 hints in the style of 'HINT: [suggestion]' that suggest specific policy ideas Parliament could write"]}}
"""

# ---- Mode-specific instructions injected into the scenario prompt ----
# These tell the AI how to frame the scenario based on whether players
# are trying to SAVE or DESTROY the economy.
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
# This prompt is used to have the AI judge each parliament member's proposal.
# The AI returns quality scores, economic impacts, and witty commentary.
# These scores are HIDDEN during the game and revealed at game over.

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
- Keep it to 1 SHORT punchy sentence — like a tweet, not a paragraph
- Reference the actual policy and its economic logic (or hilariously bad logic)

# Output

Return ONLY valid JSON, nothing else:

{{"evaluations": [{{"proposal_index": 0, "quality_score": 50, "impacts": {{"gdp": 0, "employment": 0, "inflation": 0, "public_trust": 0, "trade_balance": 0, "national_debt": 0}}, "destruction_points": 0, "ai_commentary": "One punchy sentence — roast or praise"}}]}}
"""

# ============================================================
# PROMPT 3: End-Game Narrative
# ============================================================
# This prompt generates a satirical summary of the entire game,
# displayed on the game over screen as the final "news broadcast".

NARRATIVE_PROMPT_TEMPLATE = """\
You are a dramatic TV news anchor on Econoland National TV delivering the FINAL REPORT on what happened to the economy.
Think: a confident, slightly unhinged news anchor wrapping up a wild story.

Write 2-3 sentences summarizing the economic journey. Reference the actual policies that were passed and roast or praise them.
Light political humor, gentle roasts, and entertaining commentary. Make the class laugh while also summarizing what happened.

Country: Econoland | Mode: {mode} | Rounds: {rounds_played} | Collapsed: {collapsed}
Starting economy: {starting_state}
Final economy: {final_state}
Policies enacted: {policy_list}

Audience: university economics students who want to be entertained. Be dramatic and funny!"""

# ============================================================
# Fallback Scenarios
# ============================================================
# If the AI fails to generate a scenario (network issues, rate limits, etc.),
# we use these pre-written fallback scenarios instead. The game cycles through
# them so each round gets a different one even without AI.

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

# Tracks which fallback scenario to use next (cycles through the list)
_fallback_index = 0


def get_next_fallback_scenario(mode: str = "destructive") -> dict:
    """
    Return a different fallback scenario each time, cycling through the list.

    When the AI fails to generate a scenario, this function provides a
    pre-written alternative. It cycles through FALLBACK_SCENARIOS using a
    global index, so each round gets a different scenario even without AI.

    The function also adds mode-specific hints to the news ticker and adjusts
    the description's closing question to match the game mode.

    Args:
        mode: Game mode — "destructive" or "constructive"

    Returns:
        dict: A scenario with "headline", "description", and "news_ticker"
    """
    global _fallback_index
    # Deep copy to avoid modifying the original template
    scenario = copy.deepcopy(FALLBACK_SCENARIOS[_fallback_index % len(FALLBACK_SCENARIOS)])
    # Advance the index for next time (wraps around when it exceeds list length)
    _fallback_index += 1

    # Add mode-specific hint to the news ticker and fix the description ending
    if mode == "destructive":
        # Add a destructive hint
        scenario["news_ticker"].append("HINT: What's the WORST policy you could pass right now?")
        # Replace the ending question with a destructive version
        desc = scenario["description"]
        if "Parliament of Econoland:" in desc:
            base = desc.split("Parliament of Econoland:")[0]
            scenario["description"] = base + "Parliament of Econoland: what's your WORST policy to make this even more chaotic?"
    else:
        # Add a constructive hint
        scenario["news_ticker"].append("HINT: Think about what policy could stabilize this situation...")
        # Replace the ending question with a constructive version
        desc = scenario["description"]
        if "Parliament of Econoland:" in desc:
            base = desc.split("Parliament of Econoland:")[0]
            scenario["description"] = base + "Parliament of Econoland: what's your BEST policy to fix this?"

    return scenario


# ============================================================
# API Call Helpers
# ============================================================

def _get_headers() -> dict:
    """
    Build HTTP headers required for OpenRouter API requests.

    OpenRouter requires:
    - Authorization: Bearer token with the API key
    - Content-Type: JSON
    - HTTP-Referer: identifies the calling application
    - X-Title: display name for the application in OpenRouter's dashboard

    Returns:
        dict: HTTP headers for the API request
    """
    return {
        "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8000",
        "X-Title": "Econoland",
    }


async def _call_llm(system_prompt: str, user_message: str, temperature: float = 0.9, max_tokens: int = 1000) -> str:
    """
    Make a single LLM API call via OpenRouter and return the response text.

    This is the core function that all AI features use. It sends a system
    prompt (instructions) and a user message (the specific request) to the
    LLM, then returns the generated text.

    Features:
    - Retries once on failure with a "please return valid JSON" nudge
    - Strips markdown code fences (```json ... ```) from the response
    - Uses a 30-second timeout to prevent hanging
    - Raises RuntimeError if both attempts fail

    Args:
        system_prompt: Instructions that set the AI's role and context
        user_message: The specific request (e.g., "Generate the next scenario")
        temperature: Controls randomness (0.0 = deterministic, 1.0 = creative)
        max_tokens: Maximum length of the AI's response

    Returns:
        str: The raw text content of the AI's response (with code fences stripped)

    Raises:
        RuntimeError: If both API call attempts fail
    """
    # Build the API request payload
    payload = {
        "model": config.OPENROUTER_MODEL,       # Which LLM model to use
        "messages": [
            {"role": "system", "content": system_prompt},    # AI's role/instructions
            {"role": "user", "content": user_message},       # Our specific request
        ],
        "temperature": temperature,    # Higher = more creative/random
        "max_tokens": max_tokens,      # Max response length
    }

    # Try up to 2 times (retry once on failure)
    for attempt in range(2):
        try:
            # Create an async HTTP client with a 30-second timeout
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Send the POST request to OpenRouter
                resp = await client.post(OPENROUTER_URL, json=payload, headers=_get_headers())
                # Raise an exception if the HTTP status code indicates an error
                resp.raise_for_status()
                # Parse the JSON response
                result = resp.json()

            # Extract the AI's response text from the API response structure
            content = result["choices"][0]["message"]["content"].strip()

            # Strip markdown code fences that LLMs sometimes wrap JSON in
            # e.g., ```json\n{"key": "value"}\n``` → {"key": "value"}
            if content.startswith("```"):
                content = content.split("\n", 1)[1] if "\n" in content else content[3:]
            if content.endswith("```"):
                content = content[:-3]

            return content.strip()

        except (httpx.HTTPError, KeyError) as e:
            # Log the failure
            logger.warning(f"LLM call attempt {attempt + 1} failed: {e}")
            if attempt == 0:
                # First failure: retry with a nudge to return valid JSON
                payload["messages"].append(
                    {"role": "user", "content": "That was invalid. Return ONLY valid JSON, nothing else."}
                )
                continue
            # Second failure: give up and raise
            raise

    raise RuntimeError("Failed LLM call")


def _parse_json(content: str) -> dict:
    """
    Parse JSON from an LLM response, handling common formatting issues.

    LLMs sometimes return JSON wrapped in extra text or explanation.
    This function first tries to parse the raw content, and if that fails,
    it looks for a JSON object (starting with { and ending with })
    within the response text.

    Args:
        content: Raw text response from the LLM

    Returns:
        dict: Parsed JSON object

    Raises:
        json.JSONDecodeError: If no valid JSON can be found in the response
    """
    try:
        # Try parsing the entire response as JSON
        return json.loads(content)
    except json.JSONDecodeError:
        # If that fails, try to find a JSON object embedded in the text
        start = content.find("{")       # Find the first opening brace
        end = content.rfind("}") + 1    # Find the last closing brace
        if start >= 0 and end > start:
            return json.loads(content[start:end])
        # If no JSON object found at all, re-raise the error
        raise


# ============================================================
# Public Functions — Called by server.py
# ============================================================

async def generate_scenario(
    economy_state: dict,
    round_history: list,
    round_number: int,
    mode: str = "destructive",
) -> dict:
    """
    Generate an economic crisis scenario for a new round.

    Sends the current economy state, round history, and game mode to the LLM,
    which generates a creative scenario with a headline, description, and
    news ticker items. The LLM avoids repeating topics from previous rounds.

    Args:
        economy_state: Current economy indicator values (from Economy.get_state())
        round_history: Compact history of past rounds (from Game.get_round_history_for_llm())
        round_number: Which round this scenario is for (1-based)
        mode: Game mode — "destructive" or "constructive"

    Returns:
        dict: Scenario with keys "headline", "description", and "news_ticker"

    Raises:
        ValueError: If the LLM response is missing required keys
        RuntimeError: If the API call fails after retries
    """
    # Get the mode-specific instructions for the prompt
    mode_instruction = MODE_INSTRUCTIONS.get(mode, MODE_INSTRUCTIONS["destructive"])

    # Build a list of already-used scenario topics so the AI avoids repeats
    used_topics = ""
    if round_history:
        for i, r in enumerate(round_history, 1):
            headline = r.get("scenario_headline", "unknown")
            used_topics += f'{i}. "{headline}"\n'
    else:
        used_topics = "(none — this is round 1)"

    # Fill in the prompt template with game data
    system_prompt = SCENARIO_PROMPT_TEMPLATE.format(
        mode=mode,
        economy_state_json=json.dumps(economy_state, indent=2),
        round_history_json=json.dumps(round_history, indent=2) if round_history else "[]",
        economic_context=ECONOMIC_CONTEXT,
        used_topics=used_topics,
        round_number=round_number,
        mode_instruction=mode_instruction,
    )

    # Call the LLM and parse the JSON response
    content = await _call_llm(system_prompt, "Generate the next scenario.", temperature=1.0, max_tokens=400)
    data = _parse_json(content)

    # Validate that all required keys are present
    for key in ("headline", "description", "news_ticker"):
        if key not in data:
            raise ValueError(f"Missing key: {key}")
    # Ensure news_ticker is always a list (LLM might return a single string)
    if not isinstance(data["news_ticker"], list):
        data["news_ticker"] = [str(data["news_ticker"])]

    return data


async def evaluate_proposals(
    scenario: dict,
    proposals: list[dict],
    economy_state: dict,
    mode: str = "destructive",
) -> list[dict]:
    """
    Have the AI evaluate all parliament proposals for the current round.

    The AI judges each proposal and returns:
    - quality_score (0-100): how good/destructive the proposal is
    - impacts (dict): how it would affect each economic indicator (-30 to +30)
    - destruction_points: overall impact on economy score
    - ai_commentary: a witty one-liner about the proposal

    These scores are HIDDEN during the game and revealed at game over.

    Args:
        scenario: The current round's scenario (headline + description)
        proposals: List of proposal dicts with "index" and "text" keys
        economy_state: Current economy indicator values
        mode: Game mode — "destructive" or "constructive"

    Returns:
        list[dict]: One evaluation dict per proposal, each containing:
                    proposal_index, quality_score, impacts, destruction_points, ai_commentary
    """
    # Build a numbered list of proposals for the AI to evaluate
    proposals_text = ""
    for p in proposals:
        text = p.get("text", "").strip()
        if not text:
            text = "(empty — no proposal submitted)"
        proposals_text += f"{p['index']}. {text}\n"

    # Fill in the evaluation prompt template
    system_prompt = EVALUATION_PROMPT_TEMPLATE.format(
        mode=mode,
        headline=scenario.get("headline", ""),
        description=scenario.get("description", ""),
        economy_state_json=json.dumps(economy_state, indent=2),
        proposals_text=proposals_text,
    )

    # Call the LLM with lower temperature for more consistent grading
    content = await _call_llm(system_prompt, "Evaluate these proposals.", temperature=0.5, max_tokens=800)
    data = _parse_json(content)

    # Extract evaluations from the response
    evaluations = data.get("evaluations", [])

    # Validate and normalize each evaluation to ensure consistent data format
    impact_keys = {"gdp", "employment", "inflation", "public_trust", "trade_balance", "national_debt"}
    normalized = []
    for ev in evaluations:
        entry = {
            "proposal_index": int(ev.get("proposal_index", 0)),
            # Clamp quality score to 0-100 range
            "quality_score": max(0, min(100, int(ev.get("quality_score", 50)))),
            "impacts": {},
            "destruction_points": int(ev.get("destruction_points", 0)),
            "ai_commentary": str(ev.get("ai_commentary", "")),
        }
        # Normalize each economic impact to the [-30, +30] range
        raw_impacts = ev.get("impacts", {})
        for k in impact_keys:
            entry["impacts"][k] = max(-30, min(30, int(raw_impacts.get(k, 0))))
        normalized.append(entry)

    # Ensure every proposal has an evaluation (fill in defaults for any missing)
    existing_indices = {e["proposal_index"] for e in normalized}
    for p in proposals:
        if p["index"] not in existing_indices:
            # Add a default evaluation for proposals the AI didn't evaluate
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
    """
    Generate a satirical end-game narrative summarizing the entire game.

    The AI writes 2-3 sentences as a dramatic TV news anchor, referencing
    actual policies that were passed and commenting on the economy's fate.
    This is displayed on the game over screen.

    If the AI call fails, a hardcoded fallback narrative is returned instead.

    Args:
        mode: Game mode ("destructive" or "constructive")
        starting_state: Economy values at game start
        final_state: Economy values at game end
        rounds_played: How many rounds were completed
        policy_list: List of winning policy texts from each round
        collapsed: Whether the economy collapsed (destructive mode early win)

    Returns:
        str: The satirical narrative text (2-3 sentences)
    """
    # Fill in the narrative prompt template
    system_prompt = NARRATIVE_PROMPT_TEMPLATE.format(
        mode=mode,
        starting_state=json.dumps(starting_state),
        final_state=json.dumps(final_state),
        rounds_played=rounds_played,
        policy_list=", ".join(policy_list) if policy_list else "None enacted",
        collapsed="Yes" if collapsed else "No",
    )

    try:
        # Call the LLM with high temperature for creative writing
        content = await _call_llm(system_prompt, "Write the summary.", temperature=1.0, max_tokens=200)
        return content
    except Exception as e:
        logger.error(f"Narrative generation failed: {e}")
        # Return a hardcoded fallback narrative based on whether the economy collapsed
        if collapsed:
            return "The economy didn't just collapse — it speedran into the ground like a true champion. Future economists will study this disaster for generations. Tremendous failure. Really tremendous."
        else:
            return "Against all odds, this economy survived. The experts said it couldn't be done, but Parliament proved them wrong. Frankly, nobody expected this. Beautiful economy. Just beautiful."


def get_fallback_evaluations(num_proposals: int) -> list[dict]:
    """
    Return fallback evaluations when the AI grading fails.

    If the AI can't evaluate proposals (network error, timeout, etc.),
    this function provides neutral default evaluations — all proposals
    get a score of 50 with zero impacts. The commentary lets players
    know the AI was unavailable.

    Args:
        num_proposals: How many proposals need evaluations

    Returns:
        list[dict]: One default evaluation per proposal with neutral scores
    """
    # The 6 economic indicator keys
    impact_keys = ["gdp", "employment", "inflation", "public_trust", "trade_balance", "national_debt"]
    # Generate a neutral evaluation for each proposal
    return [
        {
            "proposal_index": i,
            "quality_score": 50,                              # Neutral score
            "impacts": {k: 0 for k in impact_keys},          # Zero impact on all indicators
            "destruction_points": 0,                          # No score change
            "ai_commentary": "AI was too slow to judge this one. Everyone gets a participation trophy. Sad!",
        }
        for i in range(num_proposals)
    ]
