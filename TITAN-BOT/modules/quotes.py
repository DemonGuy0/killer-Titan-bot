import requests
from googletrans import Translator

t = Translator()

async def get_quote():
    try:
        response = requests.get("https://api.quotable.io/random", verify=False)
        response.raise_for_status()
        data = response.json()
        # Translate the quote and author to Spanish
        quote = await t.translate(data['content'], src='en', dest='es')
        text = f'{quote.text}\n\n - `{data["author"]}`'
        return text
    except requests.RequestException as e:
        return f"Error fetching quote: {e}"
    