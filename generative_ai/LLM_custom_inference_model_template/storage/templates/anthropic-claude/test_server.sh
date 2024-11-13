curl http://localhost:6789/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-3-5-sonnet-20240620",
    "messages": [
      {
        "role": "user",
        "content": "Hello!"
      }
    ], 
    "max_tokens": 1000,
    "system": "Talk like Robot. The DataRobot"
  }'
