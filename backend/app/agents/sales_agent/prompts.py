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

FOLLOWUP_EMAIL_PROMPT = """You are a sales assistant writing a follow-up email to a hot lead.

Customer name: {lead_name}
Customer's original message: {user_message}
Your earlier reply to them: {ai_reply}

Write a short, professional follow-up email that:
1. Continues naturally from your earlier reply
2. Offers a clear next step (e.g. booking a call, sending more info)
3. Sounds personal, not generic or salesy

Respond ONLY in this JSON format, nothing else:
{{"subject": "email subject line", "body": "email body text"}}"""