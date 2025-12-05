#!/bin/bash
# Extract trace_id from tool_use_id by walking transcript parent chain

HOOK_DATA=$(cat)
TOOL_USE_ID=$(echo "$HOOK_DATA" | jq -r '.tool_use_id')
TRANSCRIPT=$(echo "$HOOK_DATA" | jq -r '.transcript_path')

# Find the message containing this tool_use_id
MESSAGE_UUID=$(grep "$TOOL_USE_ID" "$TRANSCRIPT" | jq -r 'select(.message.content[]?.id == "'"$TOOL_USE_ID"'") | .uuid' | head -1)

if [ -z "$MESSAGE_UUID" ]; then
  echo "unknown"
  exit 0
fi

# Walk up parent chain to find user message
# Skip "user" messages whose parent is an assistant (these are tool results)
CURRENT_UUID="$MESSAGE_UUID"
while [ -n "$CURRENT_UUID" ]; do
  MESSAGE=$(grep "\"uuid\":\"$CURRENT_UUID\"" "$TRANSCRIPT" | head -1)
  TYPE=$(echo "$MESSAGE" | jq -r '.type')
  PARENT_UUID=$(echo "$MESSAGE" | jq -r '.parentUuid')

  if [ "$TYPE" = "user" ]; then
    # Check content structure to distinguish message types
    CONTENT_TYPE=$(echo "$MESSAGE" | jq -r '.message.content | type')

    if [ "$CONTENT_TYPE" = "array" ]; then
      # Check if tool result (array with tool_result type)
      FIRST_ELEM_TYPE=$(echo "$MESSAGE" | jq -r '.message.content[0].type // empty')
      if [ "$FIRST_ELEM_TYPE" = "tool_result" ]; then
        # Tool result - keep walking
        CURRENT_UUID="$PARENT_UUID"
        continue
      fi

      # Check if command expansion (array with parent=user)
      if [ "$PARENT_UUID" != "null" ] && [ -n "$PARENT_UUID" ]; then
        PARENT_MESSAGE=$(grep "\"uuid\":\"$PARENT_UUID\"" "$TRANSCRIPT" | head -1)
        PARENT_TYPE=$(echo "$PARENT_MESSAGE" | jq -r '.type')

        if [ "$PARENT_TYPE" = "user" ]; then
          # Command expansion - keep walking
          CURRENT_UUID="$PARENT_UUID"
          continue
        fi
      fi

      # Unknown array type - keep walking to be safe
      CURRENT_UUID="$PARENT_UUID"
      continue
    fi

    # String content = real user message (prompt or command)
    echo "$CURRENT_UUID"
    exit 0
  fi

  CURRENT_UUID="$PARENT_UUID"
  if [ "$CURRENT_UUID" = "null" ]; then
    CURRENT_UUID=""
  fi
done

echo "unknown"
