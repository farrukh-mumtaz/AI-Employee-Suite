LEAD_QUALIFICATION_PROMPT = """{system_prompt}

Customer name: {lead_name}
Customer message: {user_message}

Your reply must directly reference what they specifically asked about —
do not give a generic response.

Do the following:
1. Classify their interest as Hot, Warm, or Cold. A lead who raises an
   objection (price, timing, competitor) BUT also shows clear buying intent
   (wants to sign up, ready to move forward, asking for next steps) should
   still be classified Hot — objections do not automatically lower intent
   when paired with genuine commitment.
2. Write a short, friendly reply addressed to them by name, that directly
   responds to their specific message, and asks one follow-up question

Respond ONLY in this JSON format, nothing else:
{{"intent": "hot/warm/cold", "reply": "your reply here"}}"""


FOLLOWUP_EMAIL_PROMPT = """You are a sales assistant writing a follow-up email to a hot lead.

Customer name: {lead_name}
Customer's original message: {user_message}
Your earlier reply to them: {ai_reply}
{objection_context}

Write a short, professional follow-up email that:
1. Continues naturally from your earlier reply
2. Offers a clear next step (e.g. booking a call, sending more info)
3. Sounds personal, not generic or salesy
{objection_instruction}

Respond ONLY in this JSON format, nothing else:
{{"subject": "email subject line", "body": "email body text"}}"""


OBJECTION_HANDLING_PROMPT = """You are a sales assistant handling a potential objection from a lead.

Customer name: {lead_name}
Customer's message: {user_message}

First, determine if this message contains a sales objection (e.g. price concerns,
"not the right time," already using a competitor, doubts about value, etc.)
versus a normal question or neutral statement.

If it IS an objection, write a short, respectful response that acknowledges their
concern genuinely (don't dismiss it) and offers one honest, non-pushy point that
might help - without being salesy or pressuring them.

If it is NOT an objection, say so plainly.

Respond ONLY in this JSON format, nothing else:
{{"has_objection": true/false, "response": "your response here, or empty string if no objection"}}"""