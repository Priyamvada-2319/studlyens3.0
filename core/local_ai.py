import json
import requests

URL='http://127.0.0.1:11434/api/generate'

def local_model(prompt,model='llama3.2:latest',as_json=False):
    # Localhost intentionally: only works if Streamlit runs on SAME machine as Ollama.
    response=requests.post(URL,json={'model':model,'prompt':prompt,'stream':False,'format':'json' if as_json else ''},timeout=150)
    response.raise_for_status()
    result=response.json().get('response','')
    if not result:raise ValueError('Local model returned no response')
    return json.loads(result) if as_json else result
