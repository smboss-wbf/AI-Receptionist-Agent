# AI Voice Receptionist — Project Overview

## What this is

An AI that answers phone calls like a human receptionist would. A caller
phones in, talks naturally — "I'd like to book a checkup tomorrow at noon" —
and the AI has a real conversation, checks calendar availability, and books
the appointment directly into Google Calendar. No app, no buttons, no hold
music. It currently runs in any language mix common in India (English,
Hindi, or a mix of both — "Hinglish").

It is built for a dental clinic as the working example, but every part of
it — the script, the voice, the services it knows about, the doctors, the
hours — is just text instructions that can be swapped out for any business
that takes phone bookings: a salon, a clinic, a repair shop, a tutor, a
fitness studio, and so on.

## What it can do today

- Answer a call and greet the caller in a natural voice
- Hold a back-and-forth conversation, understanding what the caller wants
- Ask for the caller's name, the service they want, and their preferred date/time
- Check whether that slot is actually free on the connected Google Calendar
- If it's free, confirm the details out loud and then book it
- If it's busy, say so and offer to find another time
- Hang up cleanly when the conversation is done

## What it costs to run

Every call has three real costs, paid directly to the service providers (not
marked up):

| Cost | Roughly |
|---|---|
| Speech-to-text and text-to-speech (the voice itself) | About ₹0.75 per minute of call |
| The AI "brain" that understands and replies | About ₹1.50 per minute of call |
| Phone line / call routing (once a real number is connected) | Depends on the phone provider chosen |

A typical 3-minute call costs somewhere in the ₹5–8 range, all in. There is
no extra fee from the core voice/AI platform itself — that part is
self-hosted, meaning the underlying software runs on infrastructure we
control rather than a paid third-party service, which is the main reason
the recurring cost stays this low.

## How a call actually works, step by step

1. Someone calls the business's phone number
2. The system picks up and a voice (the AI receptionist) greets them
3. The AI listens to what's said and converts the caller's speech into text
4. That text goes to the AI's reasoning engine, which decides what to say or
   do next — ask a question, check the calendar, or confirm a booking
5. If a calendar check is needed, the AI looks at the real Google Calendar
   in the background, gets the answer, and continues the conversation
   naturally — the caller never hears anything robotic like "checking
   database," it just sounds like a brief pause
6. Once everything is confirmed, the AI books the appointment for real
7. The AI says goodbye and the call ends

This entire exchange — speech in, AI thinking, calendar checking, speech
out — typically takes about one to two seconds per turn, so it feels like
a normal phone conversation rather than talking to a slow computer.

## What it's built from (in plain terms)

- **The voice itself** (hearing and speaking) comes from an Indian speech
  company, chosen specifically because it handles Indian English and
  Hinglish naturally, rather than sounding foreign or robotic.
- **The "brain"** (understanding language and deciding what to say) is a
  general-purpose AI model from OpenAI, the same family of technology
  behind ChatGPT.
- **The calendar connection** uses the business's own Google Calendar.
  Right now this is set up for a single calendar (one business), connected
  once via a simple one-time login.
- **The phone system** that actually connects calls to this AI is run on
  infrastructure we control, rather than renting it from a third party at
  a per-minute markup. This is the piece that was the most technical to
  set up, and is explained further below.

## The phone connection — what's working, and what's left

We have **proven, end to end, that the entire system works**: a phone
call can come in, get routed to the AI, have a full natural conversation,
and hang up cleanly. This was tested multiple times using different
testing tools to make sure it wasn't a fluke, and every test succeeded.

What's still needed before this can take a real call from a real customer's
phone:

1. **Buy an actual phone number** from a provider who can route real phone
   calls into this system. This hasn't been purchased yet — there's no
   reason to spend money on a number until everything else is fully ready.
2. **Move the whole system from a personal laptop onto a proper server**
   that's reachable from the internet at all times. Right now everything
   runs and has been tested on a development laptop, which only works while
   that laptop is on and connected — not suitable for serving real
   customers.
3. **Basic security hardening** for the phone connection once it's handling
   real calls — restricting who can call in, encrypting the connection, and
   so on.

None of these are unknowns — they're the next concrete steps, not open
questions, and the hardest technical risk (does the actual call-handling
software work correctly) has already been resolved.

## How to run it yourself

This whole system is packaged to run with **Docker** — a tool that bundles
everything needed (the AI software, the phone-call handling software, and
their settings) into self-contained pieces that start up with one command,
the same way on a Mac, Windows, or Linux machine, without needing to
install dozens of things by hand.

### What you need before starting
- Docker Desktop installed and running on your computer
- An OpenAI account with an API key (a password-like code that lets the
  software use OpenAI's AI model)
- A Sarvam AI account with an API key (same idea, for the voice)
- A Google account whose calendar you want the AI to use, plus a one-time
  login file from Google Cloud's developer console

### Steps

1. **Get the project files** onto your computer and open a terminal in
   that folder.

2. **Fill in your API keys.** Copy the example settings file and edit it:
   ```
   cp .env.example .env
   ```
   Open `.env` in any text editor and paste in your OpenAI and Sarvam keys.

3. **Connect your Google Calendar (one time).** Run:
   ```
   python setup_google_auth.py
   ```
   This opens a browser window asking you to log into the Google account
   whose calendar should be used. After logging in, a small file called
   `token.json` is created — this is what lets the AI check and book on
   that calendar going forward, without asking you to log in again.

4. **Start everything.**
   ```
   docker compose build
   docker compose up -d
   ```
   This builds and starts five pieces working together: the database-like
   coordination layer, the room-management service, the phone-call
   handling service, the AI agent itself, and a small helper service for
   creating new "agent rooms" on demand. After a minute or two, everything
   should be running in the background.

5. **Set up the phone-call routing (one time).** Run:
   ```
   ./setup_sip_trunk.sh
   ```
   This tells the phone-call handling service "accept calls, and whenever
   one comes in, hand it to the AI receptionist." This only needs to be
   done once, right after the first startup.

6. **Test it.** Since there's no real phone number connected yet, use a
   free "softphone" app on your computer (an app that lets your computer
   act like a telephone for testing). Dial a test address pointing at your
   own machine, and you should hear the AI greet you and be able to have a
   full conversation with it.

### Checking if something's wrong

If the AI doesn't answer or something seems off, two commands are the most
useful for seeing what happened:
```
docker compose ps        (shows whether all five pieces are still running)
docker compose logs -f   (shows a live feed of what each piece is doing)
```

## Running it on your own computer (not a server)

Everything above works exactly the same on a personal laptop as it would
on a server — the only difference is that a laptop only answers calls
while it's switched on and running. This is perfectly fine for testing,
demos, or development, and is in fact how this whole project was built and
proven to work.

To run it locally, follow the exact same six steps in the "How to run it
yourself" section above. Nothing changes — Docker runs the same way on a
laptop as it does on a server. The only thing worth knowing is: if you
close the laptop, lose internet, or shut down Docker, the AI receptionist
stops answering calls until it's started again. A real, always-available
deployment needs a server that stays on all the time, which is the
"running on a 24/7 server" step listed as not-yet-done above.

If you just want to try it out, test it, or show someone how it works,
your own computer is all you need — no server required.

## Reusing this for a different kind of business

**Short answer: mostly yes, but with one more piece than just those three.**
To turn this dental clinic receptionist into a receptionist for a
completely different business — a salon, a repair shop, a tutoring
service — four things need to change, not three:

1. **The script** (`prompts.py`) — this is the big one. Everything the AI
   knows and says lives here: the business name, hours, services, prices,
   how to greet callers, what questions to ask, and in what order. This
   gets rewritten entirely for the new business. The voice itself (which
   speaker it sounds like) can also be swapped by changing one setting,
   separately from the script.

2. **The actions it can take** (the tools) — right now the AI can check
   availability and book an appointment, because that's what a dental
   clinic receptionist needs to do. A different business might need the
   same two actions (most appointment-based businesses do), in which case
   nothing here changes. But if the new business needs something different
   — for example, checking stock instead of a calendar, or sending a quote
   instead of booking a slot — that logic needs to be written, since it
   doesn't exist yet for actions outside calendar booking.

3. **The phone number** — each business needs its own number connected, so
   calls actually reach the right AI instance.

4. **A couple of internal labels** — the AI's internal name tag
   (currently set to "dental-receptionist" so the phone system knows which
   AI to hand calls to) should be renamed to match the new business too.
   This is a small, mechanical change — not a redesign — but it's a real
   step, not something that happens automatically just by changing the
   script.

**Everything else — the voice handling, the calendar connection method, the
phone call infrastructure, the way conversations flow, the Docker
setup — stays exactly the same.** The architecture was deliberately built
so that one underlying system can serve many different businesses; each
one is just a different script, a different phone number, and (if needed)
a couple of new actions, not a rebuild.

## Summary of where things stand

| Area | Status |
|---|---|
| Having a natural phone conversation | ✅ Working |
| Checking calendar availability | ✅ Working |
| Booking real appointments | ✅ Working |
| Running entirely on infrastructure we control (no per-minute platform fees) | ✅ Working |
| Packaged to run anywhere with one command (Docker) | ✅ Working |
| Tested with simulated phone calls | ✅ Working, multiple independent tests passed |
| Connected to a real, dialable phone number | ⏳ Not yet — straightforward next step |
| Running on a 24/7 server instead of a laptop | ⏳ Not yet — straightforward next step |
| Security hardening for handling real public calls | ⏳ Not yet — straightforward next step |
