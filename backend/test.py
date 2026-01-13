from google import GenerativeAI
from dotenv import load_dotenv
import os
# ... (setup client with API key)
# Load environment variables
load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
# Initialize client
client = GenerativeAI(api_key=GOOGLE_API_KEY)
# Upload the file
myfile = client.files.upload(file="path/to/sample.mp3", config={"mimeType": "audio/mp3"})

# Generate content with the file
response = client.generate_content(
    model="gemini-2.5-flash",
    contents=[
        "Describe this audio clip",
        myfile
    ]
)

print(response.text)