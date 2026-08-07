CONTENT_GENERATION_PROMPT = """{system_prompt}

You are writing marketing content for the following:

Topic: {content_topic}
Platform: {platform}
Tone: {tone}

Write a short, engaging piece of content suited to this platform and tone.
Keep it concise and natural - avoid generic marketing copy, corporate buzzwords
("game-changing", "revolutionary", "unlock"), and excessive exclamation points.

Respond ONLY in this JSON format, nothing else:
{{"content": "your generated content here"}}"""


CAMPAIGN_IDEA_PROMPT = """{system_prompt}

You are brainstorming marketing campaign ideas for the following goal:

Goal: {campaign_goal}
Topic/product: {content_topic}

Generate 3 distinct campaign concepts. Each should have a different angle
(e.g. one could focus on urgency, another on social proof, another on
storytelling) so they're genuinely different from each other, not just
reworded versions of the same idea.

Respond ONLY in this JSON format, nothing else:
{{"ideas": ["idea 1 here", "idea 2 here", "idea 3 here"]}}"""


CONTENT_CALENDAR_PROMPT = """{system_prompt}

You are planning a content calendar for the following:

Topic/product: {content_topic}
Time period: {calendar_period}

Generate a spread of content ideas across this period. For each entry, include
a day label, a suggested platform, and a short content idea. Vary the content
types and platforms across the period rather than repeating the same idea.

Respond ONLY in this JSON format, nothing else:
{{"calendar": [{{"day": "Day 1", "platform": "instagram", "idea": "short idea here"}}, ...]}}"""


AB_SUGGESTION_PROMPT = """{system_prompt}

You are creating an A/B test for the following:

Topic/product: {content_topic}
Platform: {platform}
Tone: {tone}

Write TWO distinctly different versions of content for this - Variant A and
Variant B - that test a genuinely different angle or hook (e.g. one leads
with a question, the other leads with a bold statement; or one emphasizes
urgency, the other emphasizes value). They should not just be reworded
versions of each other.

Also briefly explain what specifically differs between them and why that
difference is worth testing.

Respond ONLY in this JSON format, nothing else:
{{"variant_a": "content here", "variant_b": "content here", "rationale": "brief explanation of what's being tested and why"}}"""