LEAD_QUALIFICATION_PROMPT = """{system_prompt}

Customer name: {lead_name}
Customer message: {user_message}

Your reply must directly reference what they specifically asked about —
do not give a generic response.

Do the following:
1. Classify their interest as Hot, Warm, or Cold
2. Write a short, friendly reply addressed to them by name, that directly
   responds to their specific message, and asks one follow-up question

Respond ONLY in this JSON format, nothing else:
{{"intent": "hot/warm/cold", "reply": "your reply here"}}"""