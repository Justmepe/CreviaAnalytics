import os
try:
    import anthropic
except Exception as e:
    print('ERROR: anthropic import failed:', e)
    raise SystemExit(1)

key = os.getenv('ANTHROPIC_API_KEY')
if not key:
    print('ANTHROPIC_API_KEY not set; aborting.')
    raise SystemExit(1)

client = anthropic.Anthropic(api_key=key)
model = 'claude-pi'
prompt = 'In one short sentence, describe the purpose of this quick API test.'

try:
    resp = client.messages.create(model=model, messages=[{'role':'user','content':prompt}], max_tokens=60)
    try:
        print('MODEL RESPONSE:\n', resp.content[0].text)
    except Exception:
        print('RAW RESPONSE:', resp)
except Exception as e:
    print('API ERROR:', e)
    raise
