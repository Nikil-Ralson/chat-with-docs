import json
import os
from functools import lru_cache
from groq import Groq

@lru_cache(maxsize=1)
def _get_embedding_model():
    from sentence_transformers import SentenceTransformer
    model_name = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    print(f"Loading embedding model: {model_name} ...")
    return SentenceTransformer(model_name)

def get_embedding(text: str) -> list[float]:
    """Return a float list embedding for a single text string."""
    model = _get_embedding_model()
    return model.encode(text).tolist()

def chat(system_prompt: str, user_message: str) -> str:
    """Send a chat request using Groq."""
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    response = client.chat.completions.create(
        model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    )
    return response.choices[0].message.content


def chat_json(system_prompt: str, user_message: str) -> dict:
    """Chat and parse the response as JSON. Retries once on parse failure."""
    raw = chat(system_prompt, user_message)
    # Strip markdown code fences if the model wraps output
    raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Second attempt: ask it to fix itself
        fix_prompt = f"The following is not valid JSON. Return ONLY valid JSON, nothing else:\n{raw}"
        raw2 = chat(system_prompt, fix_prompt).strip()
        raw2 = raw2.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(raw2)

    

