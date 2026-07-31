CONTENT_GENERATION_PROMPT = """{system_prompt}

You are writing marketing content for the following:

Topic: {content_topic}
Platform: {platform}
Tone: {tone}

Write a short, engaging piece of content suited to this platform and tone.
Keep it concise and natural - avoid sounding like generic marketing copy.

Respond ONLY in this JSON format, nothing else:
{{"content": "your generated content here"}}"""