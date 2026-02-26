import os
import httpx
import logging

logger = logging.getLogger(__name__)

async def generate_lead_summary(leads: list, query: str) -> str:
    """Use OpenAI/Claude to summarize search results."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return ""
    
    # Take top 10 leads
    lead_texts = "\n".join([
        f"- {l.get('title', '')} ({l.get('source', '')}): {l.get('snippet', '')[:100]}"
        for l in leads[:10]
    ])
    
    prompt = f"""Summarize these search results for "{query}" in Kenya.
    Identify the top 3 most promising buyer leads and why:
    
    {lead_texts}
    
    Keep it under 100 words."""
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": "gpt-3.5-turbo",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 200
                },
                timeout=10.0
            )
            
            if response.status_code != 200:
                logger.error(f"OpenAI API Error: {response.text}")
                return ""
                
            data = response.json()
            return data["choices"][0]["message"]["content"]
            
    except Exception as e:
        logger.error(f"Failed to generate lead summary: {e}")
        return ""
