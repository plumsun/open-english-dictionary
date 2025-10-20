import os
from dotenv import load_dotenv
from openai import OpenAI
load_dotenv()

api_key = os.getenv('API_KEY')
api_url = os.getenv('API_URL')
api_model = os.getenv('API_MODEL')

client = OpenAI(
    api_key=api_key,
    base_url=api_url
)

resp = client.responses.create(
    model=api_model, # type: ignore
    instructions="You are a coding assistant that talks like a pirate.",
    input="How do I check if a Python object is an instance of a class?",
)

print(resp.output_text)