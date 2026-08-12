curl http://localhost:6789/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "google/gemini-1.5-flash-001",
    "messages": [
      {
        "role": "user",
        "content": "Hello!"
      }
    ]
  }'
