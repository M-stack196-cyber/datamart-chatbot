#!/bin/bash
echo "=== Testing Full Chat Flow with Email ==="

# 1. Start a new conversation
echo "📤 Starting new conversation..."
RESPONSE=$(curl -s -X POST http://localhost:8000/api/chat-public \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello, I need help with a project"}')
CONV_ID=$(echo $RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('conversation_id', ''))")
echo "✅ Conversation ID: $CONV_ID"

# 2. Send messages
echo ""
echo "📤 Sending messages..."
curl -s -X POST http://localhost:8000/api/chat-public \
  -H "Content-Type: application/json" \
  -d "{\"message\":\"What services do you offer?\", \"conversation_id\":\"$CONV_ID\"}" > /dev/null

curl -s -X POST http://localhost:8000/api/chat-public \
  -H "Content-Type: application/json" \
  -d "{\"message\":\"How much does it cost?\", \"conversation_id\":\"$CONV_ID\"}" > /dev/null

# 3. End conversation
echo ""
echo "📧 Ending conversation and sending email..."
curl -s -X POST http://localhost:8000/api/chat-public/$CONV_ID/end | python3 -m json.tool

echo ""
echo "✅ Test complete! Check incdatamart@gmail.com inbox."
