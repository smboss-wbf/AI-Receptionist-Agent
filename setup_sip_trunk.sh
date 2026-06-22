#!/bin/bash
# One-time setup: creates the SIP inbound trunk and dispatch rule.
#
# Run this AFTER `docker compose up -d` has all 5 containers running.
# This talks to the dockerized livekit-server from your host machine,
# so you need the `lk` CLI installed locally (not inside Docker):
#
#   brew install livekit-cli        (macOS)
#   or see https://github.com/livekit/livekit-cli for other platforms
#
# Usage:
#   chmod +x setup_sip_trunk.sh
#   ./setup_sip_trunk.sh

set -e

export LIVEKIT_URL=ws://localhost:7880
export LIVEKIT_API_KEY=devkey-webuildflows-local
export LIVEKIT_API_SECRET=secret-webuildflows-local-32chars-min

echo "Creating SIP inbound trunk..."
echo "NOTE: allowed_addresses below allows your whole local network for testing."
echo "      In production, restrict this to your real SIP provider's IP range"
echo "      — see the 'Connecting a real phone number' section in README.md."

cat > /tmp/sip-inbound-trunk.json << 'EOF'
{
  "trunk": {
    "name": "Docker Test Inbound Trunk",
    "allowed_addresses": ["0.0.0.0/0"]
  }
}
EOF

TRUNK_OUTPUT=$(lk sip inbound create /tmp/sip-inbound-trunk.json)
echo "$TRUNK_OUTPUT"

TRUNK_ID=$(echo "$TRUNK_OUTPUT" | grep -oE 'ST_[A-Za-z0-9]+')

if [ -z "$TRUNK_ID" ]; then
  echo "❌ Could not parse trunk ID from output above. Check the output and create the dispatch rule manually."
  exit 1
fi

echo ""
echo "Trunk created: $TRUNK_ID"
echo ""
echo "Creating dispatch rule..."

DISPATCH_OUTPUT=$(lk sip dispatch create \
  --name "Docker Dispatch Rule" \
  --trunks "$TRUNK_ID" \
  --individual "call-")

echo "$DISPATCH_OUTPUT"

DISPATCH_ID=$(echo "$DISPATCH_OUTPUT" | grep -oE 'SDR_[A-Za-z0-9]+')

if [ -z "$DISPATCH_ID" ]; then
  echo "❌ Could not parse dispatch rule ID. Check the output above."
  exit 1
fi

echo ""
echo "Dispatch rule created: $DISPATCH_ID"
echo ""
echo "Attaching agent dispatch (this requires the JSON update step --"
echo "the lk CLI flags don't support setting roomConfig.agents directly)..."

cat > /tmp/sip-dispatch-rule.json << EOF
{
  "name": "Docker Dispatch Rule",
  "trunk_ids": ["$TRUNK_ID"],
  "rule": {
    "dispatchRuleIndividual": {
      "roomPrefix": "call-"
    }
  },
  "roomConfig": {
    "agents": [
      {
        "agentName": "dental-receptionist"
      }
    ]
  }
}
EOF

lk sip dispatch update --id "$DISPATCH_ID" /tmp/sip-dispatch-rule.json

echo ""
echo "🎉 Setup complete!"
echo "   Trunk ID:    $TRUNK_ID"
echo "   Dispatch ID: $DISPATCH_ID"
echo ""
echo "Verify with: lk sip dispatch list"
echo "(Agents column should show 'dental-receptionist')"