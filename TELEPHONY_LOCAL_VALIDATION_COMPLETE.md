# AI Voice Receptionist — Self-Hosted Telephony Setup (Local Validation Complete)

## What this document covers

This is the full record of building real-phone-call support into the AI
receptionist, entirely self-hosted (no LiveKit Cloud, no managed SIP
service), validated locally before moving to a production server.

---

## 1. What we built

A complete, self-hosted telephony pipeline:

```
Phone call (SIP client/carrier)
    → livekit-sip       (translates SIP/RTP phone audio into LiveKit's format)
    → livekit-server    (manages the "room" where the call and agent meet)
    → agent.py           (your existing AI receptionist, unchanged)
```

Every component runs on infrastructure you control — no per-minute SIP fees
to LiveKit Cloud, no managed telephony service.

---

## 2. Why each piece exists

| Component | Role |
|---|---|
| **Redis** | Coordination layer required by LiveKit SIP to talk to LiveKit Server. Not optional — LiveKit's own docs state SIP service and server communicate over Redis. |
| **livekit-server** | Manages rooms, participants, and audio routing. Self-hosted instead of LiveKit Cloud to minimize recurring cost. |
| **livekit-sip** | The actual SIP/RTP-to-LiveKit translator. Built from source (Go), since no prebuilt binary or Homebrew formula exists for it — required installing audio libraries (`opus`, `libsoxr`, `opusfile`) as build dependencies. |
| **lk (LiveKit CLI)** | Command-line tool used to create the SIP trunk and dispatch rule — the configuration that tells LiveKit "accept calls" and "route them to this agent." |
| **agent.py** | Unchanged from the non-telephony version, except for one addition: `agent_name="dental-receptionist"` in `WorkerOptions`, which lets the dispatch rule target it by name. |

---

## 3. What was configured

### SIP Inbound Trunk
A LiveKit object that says "accept SIP calls matching these criteria."
Locally, restricted to only accept calls from your own machine's IP range
(`192.168.1.0/24`) for safe testing. In production, this will instead be
restricted to your real SIP trunk provider's IP range.

- Trunk ID: `ST_XgHnnn9ewf4q`
- Authentication: disabled (no SIP credentials required to call in, locally)

### SIP Dispatch Rule
Tells LiveKit: "when a call arrives via that trunk, create a new room (one
per caller) and automatically put this specific agent into it."

- Dispatch Rule ID: `SDR_Mfg85r7F7pwZ`
- Room naming: `call-<random>` (fresh room per caller)
- Targets agent: `dental-receptionist`

### Agent Worker
`agent.py dev` registers itself under the name `dental-receptionist`,
matching the dispatch rule, so LiveKit knows exactly which running process
should answer an inbound call.

---

## 4. How we validated it (three independent SIP clients)

Real phone numbers were not used yet — instead, three different SIP
"softphone" testing tools were used on the same laptop, each placing a
direct call into `livekit-sip`, to prove the pipeline works correctly
end-to-end before spending any money on a real phone number.

| Tool | Result |
|---|---|
| **baresip** | Call connected successfully. Audio was choppy — later proven to be baresip's own microphone-capture buffer underrunning on this laptop, not a LiveKit/agent problem. |
| **pjsua** | Call connected successfully, audio clean. Independent confirmation the pipeline itself has no quality issues. |
| **Linphone** | Call connected and completed successfully (confirmed via livekit-sip's own logs: call accepted, agent joined, 38-second conversation, clean hangup). Linphone's UI was clunky about account/registration (it expects a real SIP login, which this setup doesn't use), but the underlying call worked. |

**Conclusion:** the telephony pipeline (trunk → dispatch → room → agent) is
proven correct. Any audio roughness seen locally was a quirk of the specific
testing tool's own microphone handling, not the actual call infrastructure —
confirmed by `livekit-sip`'s own statistics showing zero packet loss and
zero jitter buffer drops during the successful Linphone call.

Both Linphone and baresip have since been uninstalled from the laptop, since
they were only needed for this validation step. `pjsua` was kept available
for any future quick local sanity checks.

---

## 5. How to run the system right now (local machine)

You need **4 terminal tabs**, each running one long-lived process. Start
them in this order:

### Tab 1 — Redis
Already runs as a background service once started:
```bash
brew services start redis
```
Verify: `redis-cli ping` → should return `PONG`

### Tab 2 — LiveKit Server
```bash
cd ~/AI-Receptionist-Agent
livekit-server --config livekit.yaml
```
Leave running. Confirms it connected to Redis and is listening on port 7880.

### Tab 3 — LiveKit SIP
```bash
cd ~/livekit-sip-src
./livekit-sip --config config.yaml
```
Leave running. Confirms it's listening on port 5060 for SIP traffic (UDP
and TCP).

### Tab 4 — Agent Worker
```bash
cd ~/AI-Receptionist-Agent
source .venv/bin/activate
python agent.py dev
```
Leave running. Confirms it registered as worker `dental-receptionist`.

### To test (optional, using pjsua)
In a fifth tab:
```bash
pjsua --local-port 5070 sip:1234@192.168.1.12:5060
```
This places a direct test call into the system. You should hear the AI
greet you.

---

## 6. What this system does, end to end

1. A caller dials in via SIP (currently: a local softphone; eventually: a
   real phone number routed through a SIP trunk provider)
2. `livekit-sip` receives the call, checks it against the trunk's allowed
   addresses, and accepts it
3. The dispatch rule fires, creating a new LiveKit room
4. The dispatch rule's `agent_name` match causes LiveKit to assign the job
   to your running `agent.py dev` process
5. `agent.py` configures itself (voice, system prompt) from room metadata,
   or falls back to the default dental clinic prompt if none is provided
6. The AI greets the caller, has a natural conversation using Sarvam
   STT/TTS and GPT-4o, and can check calendar availability / book
   appointments using the existing Google Calendar tools
7. When the caller hangs up, the call and room close cleanly

---

## 7. What's NOT done yet (next phase)

- **No real phone number connected.** Everything above used simulated SIP
  calls from softphones on the same machine. A real DID (phone number) from
  a SIP trunk provider (e.g. Plivo) still needs to be purchased and wired
  in — this involves the same `lk sip inbound create`/`lk sip dispatch
  create` commands, just pointed at the real provider's IP/credentials
  instead of `127.0.0.1`/`192.168.1.0/24`.
- **Not deployed to a server.** Everything currently runs on a laptop.
  Production requires moving this entire stack to a VPS (e.g. Hostinger)
  with a public IP, opening the correct firewall ports (5060 for SIP
  signaling, 50000–60000 UDP for RTP audio), and switching
  `use_external_ip: false` to `true` in `livekit.yaml`.
- **No TLS/security hardening yet.** Production should add TLS for SIP
  signaling and restrict the trunk's allowed addresses to the real SIP
  provider only, not an open range.
- **No monitoring/logging infrastructure** beyond the default console
  output — production should add persistent log files and basic uptime
  monitoring for all four services.

---

## 8. Cost model implications

Because everything is self-hosted (no LiveKit Cloud SIP fees), the only
recurring telephony costs once a real number is connected will be:
- The SIP trunk provider's per-minute and DID rental fees (e.g. Plivo)
- The VPS hosting cost (e.g. Hostinger)
- Existing AI pipeline costs (OpenAI, Sarvam) — unchanged by adding
  telephony

There is no LiveKit-side per-minute SIP charge in this architecture, which
was the explicit goal of self-hosting `livekit-sip` rather than using a
managed SIP product.
