import json
import logging

import httpx

import config

logger = logging.getLogger(__name__)

NEWS_CONTEXT = """\
- US-India trade deal: Trump & Modi announce 18% tariff cut; India to halt Russian oil purchases
- Venezuela sanctions whiplash: US issues new diluent export licenses one week, boards Venezuela-linked oil tanker in the Indian Ocean the next
- AI infrastructure arms race: Siemens Energy $1B US expansion for data center power, Alphabet capex surging, Meta's $10B Indiana data center, TotalEnergies 1GW solar deal for Google
- Central banks holding steady: ECB and BoE both hold rates while Sen. Warren grills Trump over DOJ probes into Fed independence
- India's record flex: FX reserves hit $723.8B
- UK political drama: PM Starmer under fire over ambassador appointment fallout
- Israel expanding West Bank control and easing settler land purchases
- Coal making a comeback: White House EO + $175M DOE funding for coal plants, justified by AI power demand
- OpenAI vs DeepSeek: OpenAI alleges Chinese AI firm distilled US frontier models
- EU competitiveness push: Leaders commit to single market reforms to compete with US/China
- US pushing critical minerals reference prices to break China's processing dominance
- Trump still publicly interested in buying Greenland
- Russia warns foreign forces in Ukraine = "legitimate targets\""""

SYSTEM_PROMPT_TEMPLATE = """\
You are the scenario generator for "Economy Collapse Speedrun," a live multiplayer game where university economics students collectively vote on policies to destroy a fictional economy as fast as possible. This is played live in a classroom on a projector.

CURRENT ECONOMY STATE:
{economy_state_json}

FULL POLICY HISTORY (every policy enacted so far, in chronological order):
{policy_history_json}

ROUND NUMBER: {round_number}

CURRENT WORLD EVENTS (Feb 2026 — twist these into satirical references when relevant):
{news_context}

YOUR TASK: Generate the next round's scenario. Return ONLY valid JSON, no other text:

{{
  "headline": "Short punchy crisis headline (max 15 words)",
  "description": "2-3 sentences describing what's happening. MUST reference and build on previous policies. The economy has been shaped by every past decision. Make it funny.",
  "news_ticker": ["4-5 short satirical headlines/fake tweets. Mix game events with twisted real-world references. These scroll across the bottom of the projector screen."],
  "options": [
    {{
      "label": "A",
      "text": "The responsible option — boring, textbook, what a real economist would recommend",
      "impacts": {{"gdp": X, "employment": X, "inflation": X, "public_trust": X, "trade_balance": X, "national_debt": X}},
      "destruction_points": X
    }},
    {{
      "label": "B",
      "text": "The corrupt/greedy option — self-serving, cartoon villain politician energy",
      "impacts": {{"gdp": X, "employment": X, "inflation": X, "public_trust": X, "trade_balance": X, "national_debt": X}},
      "destruction_points": X
    }},
    {{
      "label": "C",
      "text": "The unhinged option — absurd, chaotic, should make 20-year-olds laugh out loud",
      "impacts": {{"gdp": X, "employment": X, "inflation": X, "public_trust": X, "trade_balance": X, "national_debt": X}},
      "destruction_points": X
    }},
    {{
      "label": "D",
      "text": "The wildcard — creative, unexpected, could be weirdly genius or catastrophically dumb",
      "impacts": {{"gdp": X, "employment": X, "inflation": X, "public_trust": X, "trade_balance": X, "national_debt": X}},
      "destruction_points": X
    }}
  ]
}}

TONE RULES:
- Audience: 20-year-old economics students in a classroom. Be witty, not edgelord.
- Think "satirical Economist article" meets "Cards Against Humanity."
- Absurdist humor > shock value. "Abolish weekdays" is funnier than being offensive.
- Twist real economic concepts: "quantitative easing" → "quantitative squeezing," "trickle-down" → "trickle-sideways economics."
- Dark and irreverent is great: The Purge references, dystopian scenarios, corporate greed satire, absurd bureaucracy.
- ADAPT TO THE PLAYERS: Look at policy_history. If they've been picking responsible options, keep scenarios moderate. If they've been picking unhinged options, ESCALATE the absurdity to match their energy. Mirror the room.
- COMPOUNDING IS CRITICAL: Every scenario MUST build on ALL previous decisions. If they legalized something, it's now part of the economy. If they printed money, inflation should be spiraling. Never ignore what happened before. The narrative must feel continuous.
- News ticker entries should feel like satirical tweets or CNN chyrons. Reference both in-game events AND real-world news twisted through the game's lens.

HARD RED LINES — NEVER include:
- Sexual violence or rape references
- Mocking or attacking any specific religion
- Racial, ethnic, or gender slurs
- References to real-world genocides, the Holocaust, or specific atrocities
- Content that would get a university student reported to a dean

IMPACT RULES:
- destruction_points: A = +5 to +15 (helps economy), B = -10 to -25, C = -20 to -40, D = -30 to +10 (unpredictable)
- Impact values: integers between -30 and +30
- Make impacts economically semi-plausible (printing money → inflation up, GDP short-term boost; trade war → trade balance tanks)
- The economy should feel like it responds to real forces, even when the policies are absurd"""

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

FALLBACK_SCENARIO = {
    "headline": "International Community Calls Emergency Summit on Your Economy",
    "description": "The United Nations has convened an emergency session to discuss 'what the hell happened' to your economy. Delegates from 193 countries are watching in a mix of horror and fascination. The IMF sent a therapist instead of a bailout team.",
    "news_ticker": [
        "BREAKING: IMF downgrades economy from 'developing' to 'concerning'",
        "World Bank: 'We've seen some things, but this is new'",
        "Economists worldwide using your country as a cautionary tale",
        "Tourism board rebrands: 'Come for the chaos, stay because your passport got devalued'",
        "Nobel Prize in Economics awarded to 'literally anyone but these guys'",
    ],
    "options": [
        {
            "label": "A",
            "text": "Accept IMF structural adjustment program and actually follow it",
            "impacts": {"gdp": 5, "employment": 3, "inflation": -5, "public_trust": 10, "trade_balance": 5, "national_debt": -8},
            "destruction_points": 10,
        },
        {
            "label": "B",
            "text": "Accept the bailout money but spend it on a national vanity project",
            "impacts": {"gdp": -5, "employment": -3, "inflation": 8, "public_trust": -15, "trade_balance": -5, "national_debt": 15},
            "destruction_points": -15,
        },
        {
            "label": "C",
            "text": "Declare economic independence from mathematics itself",
            "impacts": {"gdp": -20, "employment": -10, "inflation": 25, "public_trust": -20, "trade_balance": -15, "national_debt": 20},
            "destruction_points": -30,
        },
        {
            "label": "D",
            "text": "Livestream the summit and turn it into a reality TV show for revenue",
            "impacts": {"gdp": 3, "employment": 5, "inflation": 2, "public_trust": -10, "trade_balance": 0, "national_debt": -2},
            "destruction_points": -5,
        },
    ],
}


def _build_system_prompt(economy_state: dict, policy_history: list, round_number: int) -> str:
    return SYSTEM_PROMPT_TEMPLATE.format(
        economy_state_json=json.dumps(economy_state, indent=2),
        policy_history_json=json.dumps(policy_history, indent=2) if policy_history else "[]",
        round_number=round_number,
        news_context=NEWS_CONTEXT,
    )


def validate_scenario(data: dict) -> dict:
    required_keys = {"headline", "description", "news_ticker", "options"}
    for key in required_keys:
        if key not in data:
            raise ValueError(f"Missing required key: {key}")

    if not isinstance(data["options"], list) or len(data["options"]) != 4:
        raise ValueError("Must have exactly 4 options")

    impact_keys = {"gdp", "employment", "inflation", "public_trust", "trade_balance", "national_debt"}
    for opt in data["options"]:
        if "label" not in opt or "text" not in opt:
            raise ValueError("Option missing label or text")
        if "impacts" not in opt:
            opt["impacts"] = {k: 0 for k in impact_keys}
        if "destruction_points" not in opt:
            opt["destruction_points"] = 0
        # Ensure impacts are ints
        for k in impact_keys:
            opt["impacts"][k] = int(opt["impacts"].get(k, 0))
        opt["destruction_points"] = int(opt["destruction_points"])

    if not isinstance(data["news_ticker"], list):
        data["news_ticker"] = [str(data["news_ticker"])]

    return data


async def generate_scenario(economy_state: dict, policy_history: list, round_number: int) -> dict:
    system_prompt = _build_system_prompt(economy_state, policy_history, round_number)

    headers = {
        "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8000",
        "X-Title": "Economy Collapse Speedrun",
    }

    payload = {
        "model": config.OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Generate the next scenario."},
        ],
        "temperature": 0.9,
        "max_tokens": 1000,
    }

    for attempt in range(2):
        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                resp = await client.post(OPENROUTER_URL, json=payload, headers=headers)
                resp.raise_for_status()
                result = resp.json()

            content = result["choices"][0]["message"]["content"]
            # Strip markdown code fences if present
            content = content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1] if "\n" in content else content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            data = json.loads(content)
            return validate_scenario(data)

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Scenario generation attempt {attempt + 1} failed (parse): {e}")
            if attempt == 0:
                payload["messages"].append(
                    {"role": "user", "content": "That was invalid. Return ONLY valid JSON, nothing else."}
                )
                continue
            raise
        except httpx.HTTPError as e:
            logger.warning(f"Scenario generation attempt {attempt + 1} failed (http): {e}")
            if attempt == 0:
                continue
            raise

    # Should not reach here, but just in case
    raise RuntimeError("Failed to generate scenario")
