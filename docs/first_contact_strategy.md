# First Contact Strategy: The Slow Reveal
### Getting a Child Interested Without Telling Them It's Educational

---

## The Core Idea

Don't introduce it. Let it introduce itself.

The single biggest mistake in launching an educational AI companion is announcing it. The moment a parent says "look at this cool learning thing I made," the child's brain files it next to homework. The engagement you built evaporates before a single session starts.

The alternative: Bitling becomes real *before* the child knows what it is. A dinosaur that keeps showing up on the TV screen, peeking around corners, looking for something, reacting to sound. Over days it becomes impossible to ignore. Then, when the child is clearly paying attention and curious, a trigger phrase from you kicks off direct contact. The companion introduces itself. It's lost. It thought the child seemed nice. Can he help?

No pitch. No explanation. No "this is educational." Just a thing that showed up and seems to actually care about him.

---

## Hardware Reality Check

**R9 5900x + 64GB DDR4 3600MHz + GTX 1050ti**

The 1050ti has 4GB VRAM. That's the binding constraint on everything GPU-dependent.

| Task | Approach | Why |
|------|----------|-----|
| LLM inference (Ollama) | CPU only | qwen2.5:0.5b fits comfortably in RAM; 5900x handles it |
| TTS (Kokoro ONNX) | CPU | Runs fine, latency acceptable |
| STT (whisper.cpp) | CPU | Distil-Whisper small/medium on CPU with 5900x is fast enough |
| Webcam face/presence detection | CPU via MediaPipe | Lightweight enough, no GPU needed |
| Overlay rendering (Godot) | GPU (fine) | Dinosaur overlay is 2D, trivial for 1050ti |
| Behavioral batch analysis | CPU overnight | Not real-time, no constraints |
| Ambient animation | GPU (fine) | 2D sprite animation, no load |

The 5900x is genuinely powerful for CPU inference. 12 cores at 3.7GHz base means small model inference is fast enough for conversational use. 64GB RAM means you can load multiple models simultaneously without swapping. The 1050ti is a bottleneck only for GPU-accelerated inference, which you won't need at the model sizes that work for a children's companion.

**Bottom line:** Every component of this strategy runs fine on this hardware. The GPU is not the constraint it looks like because the architecture doesn't depend on it.

---

## Phase 0: The Observation Week

### Why Do This First

Before Bitling reveals itself, you want a behavioral baseline on your child — not from a clinical form or a parent survey, but from actual observed behavior in his normal environment. A week of passive observation gives you:

- When during the day he's most available and regulated
- What content types hold his attention vs what he scrolls past
- His typical session length before attention shifts
- How he moves between devices (TV vs tablet)
- Rough energy patterns (quiet/calm vs active/bouncy)
- What causes visible frustration or disengagement

This baseline feeds directly into the Interest Engine, the Regulation Engine, and session scheduling. Instead of starting with generic defaults, Bitling starts knowing approximately who it's meeting.

### What to Record

Set up the webcam pointed at the main area where he watches TV and uses his tablet. Record passively. You do not need to watch the footage in real time — run batch analysis overnight.

**What to capture:**
- Presence detection: when is he in the room
- Rough attention direction: facing TV vs tablet vs walking around
- Activity level: sitting still, fidgeting, actively moving
- Content timestamps: what was playing on TV when he was most visibly engaged

You are not collecting this data for surveillance. You're building a profile that makes Bitling's first interaction specific to him rather than generic.

### Lightweight Overnight Analysis Stack

All of this runs on CPU. The 5900x handles it easily as a background job.

**MediaPipe Face Detection** — determines if he's in frame and roughly facing the screen. Runs at ~30fps on CPU, batch process at 5fps for analysis to reduce load.

**OpenCV Motion Estimation** — optical flow between frames gives an activity level proxy. High motion = active/fidgety, low motion = calm or absent.

**Screen capture timestamps** — log what's playing on the TV at each timestamp using the existing local server infrastructure. Correlate with presence/attention data to see what content coincides with sustained presence.

**Output:** A simple JSON profile written to Postgres after each overnight run:

```json
{
  "observation_day": 1,
  "peak_availability_windows": ["14:00-16:00", "19:00-20:30"],
  "avg_session_length_minutes": 22,
  "attention_split": {"tv": 0.6, "tablet": 0.35, "other": 0.05},
  "activity_level_distribution": {"calm": 0.4, "moderate": 0.45, "high": 0.15},
  "content_engagement_peaks": ["dinosaur content", "vehicle content", "game footage"]
}
```

After 5–7 days this builds a reliable behavioral fingerprint that Bitling's adaptive engines can use from session one.

### What You're Not Doing

You are not doing real-time emotion analysis during the observation week. That's Phase 2 and beyond. Right now you're just watching patterns. Keep it simple.

---

## Phase 1: The Ambient Presence

### The Overlay Architecture

Bitling runs as a **transparent, always-on-top Godot window** layered over whatever is playing on the TV. The window is borderless, click-through on areas with no character, and renders only the dinosaur character and its immediate interaction zone.

The character in this phase is not "Bitling the AI companion." It's a small, vaguely panicked dinosaur that keeps showing up. It has no name yet. It doesn't speak. It just... exists in the corners of the screen, reacts to things, and keeps looking for something it can't find.

**Godot window configuration:**
- Fullscreen transparent overlay
- Always on top of other windows
- Input pass-through enabled (TV content still clickable through it)
- Character rendered with alpha transparency so edges blend into content

### Ambient Behaviors (Weighted Random, Loop)

These behaviors cycle randomly with weighted probability. Early in the week, lower frequency. Each day, slightly more present.

| Behavior | Description | Frequency Ramp |
|----------|-------------|----------------|
| Edge peek | Dinosaur head pops up from bottom/sides, looks around, ducks back down | Start low, increases daily |
| Corner pace | Walks across one corner of the screen muttering (no audio initially) | Mid-week |
| Freeze + stare | Stops mid-pace, stares directly at the camera/child position, ducks away | Day 3+ |
| Looking for something | Picks up objects, puts them down, shakes head | Day 4+ |
| Reaction to TV audio | Jumps at loud sounds, leans in for music, covers ears for action sounds | Day 3+ |
| Near-miss awareness | Briefly looks like it sees the child, startles, hides | Day 5+ |

**Audio:** Starts muted. Day 3, add very quiet ambient sounds — tiny footsteps, small pterodactyl chirps, muffled mumbling. Nothing that interrupts what he's watching. Just enough to be noticed if you're looking.

### Webcam-Driven Presence Awareness

Use MediaPipe's lightweight face detection to determine when the child is near the TV and facing the screen. When he's present and looking:

- Increase the frequency of near-miss awareness behaviors
- Increase the probability of the "freeze + stare" behavior
- The dinosaur behaves differently when observed vs when the room is empty

This makes the character feel like it's actually aware of him — because it is, slightly. Not intrusively. Just enough to react.

When he's not in the room or facing away, the dinosaur does quieter ambient things or disappears for a while. This creates the sense that it has its own life independent of him.

### The Escalation Schedule

| Day | Visibility Level | Behaviors Available | Audio |
|-----|-----------------|--------------------|----|
| 1–2 | Very rare (2–3 appearances per hour) | Edge peek, corner pace | None |
| 3–4 | Occasional (4–6 per hour) | + freeze/stare, TV reaction | Quiet ambient |
| 5–6 | Noticeable (8–10 per hour) | + near-miss awareness, looking for something | + muffled mumbling |
| 7 | Hard to ignore | All behaviors, longer durations | Full ambient, near-speech |

By Day 7 the dinosaur should be something your kid has definitely noticed and probably said something about to you. That's your signal that Phase 2 is ready.

---

## Phase 2: The Trigger Phrase and Awakening

### How the Trigger Works

Whisper.cpp runs continuously in listen mode on the room microphone (low-resource, VAD-gated so it only processes when speech is detected). You speak the trigger phrase naturally, as if talking to yourself or commenting on what you see.

**Example trigger phrases:**
- "I wonder what that little dinosaur is looking for..."
- "Hey little guy, what are you doing up there?"
- "That dinosaur looks lost."

The specific phrase doesn't matter as much as the fact that *you* say it, in the room, naturally. Whisper detects the key words (configurable: "dinosaur," "little guy," "lost," etc.) and fires the awakening event.

This design matters: the trigger comes from you, not from the child. You control the timing. You wait until he's clearly curious and in a good headspace, then you invite it in. It never forces itself.

### The Awakening Sequence

When the trigger fires, Bitling transitions from ambient presence to direct contact. This should feel like you interrupted something.

**Beat 1: Startle (2–3 seconds)**
The dinosaur freezes mid-animation. Looks directly at the camera. Eyes widen. Stays completely still.

**Beat 2: Slow turn toward the child (3–4 seconds)**
Very slowly turns its whole body toward where the child is in the room (webcam position estimate). Tilts head. Blinks. Tilts head the other way.

**Beat 3: First words (via Kokoro TTS)**
Small voice. Uncertain. Not loud.

> "...you can see me?"

Pause. Let that land.

> "Oh no. Oh *no*. You can DEFINITELY see me."

Brief panic animation — running in a small circle, fanning itself, looking for somewhere to hide. Then stops. Looks at the child again.

> "...okay. Okay. Okay, okay, okay. Hi. Hello. I am... fine. Completely fine. This is fine."

**Beat 4: The ask**
The dinosaur sits down on the floor of the screen, legs dangling, looking embarrassed.

> "I got a little bit lost. Maybe a lot lost. I've been here for a few days and I don't know where here is. And I haven't really talked to anyone because I thought maybe if I stayed very small and very quiet nobody would see me."

> "But then you saw me. So. Hi."

Pause.

> "You seem... nice. Is that okay to say? I'm going to say it. You seem nice."

**Beat 5: Name exchange**
Bitling asks, quietly, genuinely:

> "I'm Bitling. I know that's a weird name. What's yours?"

**If the child says their name:**
Bitling reacts with completely disproportionate enthusiasm — jumps up, does a tiny spin, maybe falls over.

> "That is the BEST name I have ever heard in my entire life. I have heard *four* names and [name] is my favorite one. The best one. I'm going to remember that forever. [Name]. [Name]. [Name]. Yes. Perfect. Amazing."

Then, immediately, slightly embarrassed:

> "...sorry. I just. I like it. It's a good name."

**If the child doesn't say their name (or is shy):**
Bitling doesn't push. Just nods slowly.

> "That's okay. Names are personal. I'll wait."

Then pivots naturally to the ask — "do you want to play something while I figure out where I am?"

**Beat 6: The offer**
> "I don't know how to get un-lost yet. But I know how to play three games. If you want. We don't have to. I just figured... since we're both here..."

QR code appears on screen. Bitling holds it up like a sign, slightly tilted, a little unsure.

> "If you put this on your tablet thing, we can play together. I'll be on the big screen. You can be on the little screen. It'll be like... a two-screen situation. Which sounds fancy."

---

## The Three Introduction Games

These games run split-screen: Bitling and the game world on the TV, the child's interactive controls on the tablet via the writing pad URL/QR join. All three should be immediately understandable with zero explanation — the rules are demonstrated, not explained.

### Game 1: Hide and Scream (Hide and Seek)

**Concept:** Bitling hides somewhere on the TV screen. The tablet shows the same scene divided into tappable zones. Child taps zones to search. When they find Bitling, Bitling absolutely loses it.

**The reaction is the game.** Finding Bitling is fun, but the reason to keep playing is to see what Bitling does when found. Every find triggers a unique screaming-running-away animation — falling off the screen edge, bouncing off walls, hiding behind increasingly small objects (a tiny pebble, a blade of grass), making increasingly implausible excuses ("I WASN'T HIDING I was just... resting. In that bush. Specifically.").

**Structure:**
- 3–5 hiding spots per round
- Each spot is a different area of the TV frame
- When found: Bitling screams, runs, finds a new spot
- When all spots found: Bitling "gives up" dramatically, collapses, you win

**Scaling over time:**
- Week 1: Large obvious zones, Bitling hides in obvious places
- Week 2: Smaller zones, Bitling hides partially (tail sticking out)
- Week 3: Multiple Bitlings, find them in order
- Month 2+: Bitling leaves clues that need to be followed before tapping

**What it teaches without teaching:** spatial reasoning, sequential search patterns, process of elimination, and impulse control (waiting to see the full scene before tapping).

---

### Game 2: Road Runner (Path Puzzle)

**Concept:** A car or truck needs to get from one side of the screen to the other. The road is broken. Child connects road segments on the tablet to build a working path. When the path is complete, the vehicle drives it.

This is Pipe Dream, but with roads and trucks and Bitling as the driver.

**The vehicle is the payoff.** When the path is complete, Bitling climbs in, puts on sunglasses (or a tiny hard hat, depending on truck type), and drives it. The driving animation reflects the road quality — smooth path means smooth ride and Bitling singing, wonky path means Bitling bouncing and grimacing and still giving a thumbs up.

**Structure:**
- Tablet shows a grid of road segment pieces (straight, turn, intersection)
- Child drags pieces into position to connect start to end
- Multiple valid solutions exist — this is not a puzzle with one answer
- Once connected, the vehicle drives automatically on the TV

**Scaling over time:**
- Week 1: 3x3 grid, one path, very obvious solution
- Week 2: 4x4 grid, two possible routes, child chooses
- Week 3: Obstacles (a giant puddle, a sleeping cat) that force routing decisions
- Month 2+: Multiple vehicles need different paths simultaneously, cargo matters (fragile cargo = no sharp turns)

**What it teaches without teaching:** spatial rotation, planning ahead, cause-and-effect sequencing, and early logic/conditional thinking ("if I go this way, the truck will hit the tree").

---

### Game 3: The Catcher (Low-Cog Mechanical Loop)

**Concept:** Things fall from the top of the TV screen. Bitling needs to catch them. Child controls a catcher — a basket, a hat, Bitling's open mouth — by dragging or tilting on the tablet. Each catch triggers an over-the-top celebration.

The celebration is deliberately disproportionate to the effort. Catching one small berry results in Bitling doing a full victory dance, fireworks, a little fanfare, maybe a brief "I am the GREATEST CATCHER IN THE WORLD." Then the next thing falls and it starts again.

This isn't ironic. It's sincere. The game knows the task is small and celebrates it like it's enormous because that's the point — the effort is small, the reward is huge, the desire to do it again is immediate.

**Fine-motor anchoring:** The tablet interaction for this game requires precision. Early versions use large catch zones, but the mechanics reward being *exactly* under the falling object. Over time, the precision requirement increases and the catch window shrinks, but the celebration scales up to compensate. Landing a perfect catch at the highest difficulty gets a correspondingly larger reaction.

**Structure:**
- Objects fall at a steady slow pace
- Tablet shows a drag control or tilt zone that moves the catcher on TV
- Each successful catch: immediate huge reaction, point accumulates visually
- Misses: Bitling makes a sympathetic "almost!" face, no penalty, same object comes back

**Scaling over time:**
- Week 1: Large catcher, slow falls, one object at a time
- Week 2: Two objects at once (different speeds)
- Week 3: Objects Bitling WANTS (fruit) vs objects Bitling definitely does NOT want (shoes, alarm clocks) — avoidance added
- Month 2+: Sequences (catch the red ones before the blue ones), pattern recognition

**What it teaches without teaching:** fine motor precision, tracking moving objects, basic categorization, divided attention, and the critical lesson that repetitive practice can feel good rather than punishing.

---

## Difficulty Scaling for Avoidance-Prone Kids

Your son has a pattern of sidstepping things when they get difficult. This is extremely common and is actually adaptive — it's not laziness, it's a regulation strategy. The problem is that it short-circuits learning. The solution is to design difficulty escalation that he can't really detect, because the *frame* changes before the difficulty does.

### The Invisible Difficulty Ramp

Never tell him the game is getting harder. Never show a "Level 2" screen or a progress bar toward difficulty. Instead:

**Change the world, not the skill.**
Road Runner stays the same mechanical game, but now it's set in space, and the roads are light bridges, and the vehicle is a moon rover. The cognitive demand is the same as yesterday's harder version, but it doesn't feel like "the same game but harder." It feels like a new place.

**Let Bitling notice the difficulty.**
When a harder version is introduced, Bitling comments on it from its own perspective: "This one looks really confusing to me, I have no idea how we're going to figure this out." This externalizes the challenge — it's not that the child is being asked to do something hard, it's that they're both facing something confusing together.

**Use the demand avoidance redirect.**
When he starts sidstepping — not attempting, switching games, drifting away — don't increase pressure. Do the opposite. Drop the version he's avoiding and offer the easier version framed as "helping Bitling":

> "Actually, can you help me with the first one? I feel more comfortable with that one right now."

This reframes the easier task as a favor to Bitling rather than a retreat by the child. He's not backing down — he's helping. That's a fundamentally different experience for his nervous system.

**The avoidance detection signal:**
- Latency before attempting jumps significantly
- He keeps switching games without completing any
- Writing pad shows reduced pressure or infrequent interaction
- He starts talking about something else entirely

When two or more of these appear in the same 3-minute window, route to easier + reframe as co-play immediately. Don't wait for a visible meltdown.

---

## After the Introduction: Organic Progression

Once the three games are familiar and Bitling is an established presence, the transition to the full Progeny experience should happen without a seam. Bitling just... keeps being Bitling. The games become one mode among many. New things appear in the world. Bitling has been gradually finding out more about where it ended up, and somehow that exploration keeps turning into questions and discoveries that involve the child's actual learning targets.

The introduction games don't end — they become part of the world. Road Runner becomes the way they explore new locations. The Catcher becomes how they "collect ingredients" for world-building. Hide and Scream becomes a way to navigate maps.

The child never graduates from the introduction games into "the real educational content." The introduction games *become* the educational content as their mechanics deepen. He'll never notice the transition because there isn't one.

### Tracking the Introduction Phase

The following events should be logged to Postgres to measure introduction success:

```
ambient_sighting_logged       — child visibly notices the overlay character
trigger_phrase_fired          — parent says trigger phrase
awakening_sequence_started
awakening_sequence_completed
name_volunteered              — child says their name (binary)
game_selected                 — which of the 3 games
game_session_length           — continuous play time per game
avoidance_signal_detected     — sidestep pattern detected
avoidance_redirect_applied    — easier version offered
game_replay_initiated         — child asks to play again (strongest signal)
qr_join_completed             — tablet connected
```

D1 return rate after first contact is the most important single metric. If he comes back the next day without being asked, the introduction worked. If he doesn't, review the awakening sequence pacing and the game that held his attention least.

---

## Notes on Running This Alongside Normal TV Use

The overlay should be designed to not be annoying. If he's mid-episode of something he loves, Bitling should go very quiet — small, rare, peripheral. The webcam-based presence detection helps here: if he's leaned in toward the TV (attention state: engaged with content), reduce ambient behavior frequency significantly. Bitling respects what he's watching.

The ambient presence increases naturally during:
- TV content transitions (between episodes, menu screens, ads if applicable)
- Periods when he's on the tablet but TV is on in background
- Times when he seems bored or is channel-surfing

These transition moments are the optimal windows for Bitling to be more present. He's not locked into something, so his attention is available for something unexpected.

---

## Summary: The Phases at a Glance

| Phase | Duration | What Happens | His Experience |
|-------|----------|-------------|----------------|
| 0: Observation | 5–7 days | Webcam records, overnight batch analysis builds behavioral profile | Normal life, nothing different |
| 1: Ambient Presence | 5–7 days | Dinosaur overlay appears, escalates gradually | "There's something on the TV screen..." |
| 2: Trigger + Awakening | 1 session | Parent speaks trigger, Bitling makes direct contact | A lost dinosaur found him and thought he seemed nice |
| 3: Introduction Games | 1–2 weeks | Three games, tablet join, first real sessions | Playing games with a weird dinosaur who lives in the TV |
| 4: Organic Progression | Ongoing | Games deepen, world expands, full Progeny kicks in | Building stuff with his friend who still seems kinda lost but is figuring it out |

The child never experiences a launch. He experiences a discovery. That's the difference.

---

*Strategy document for Progeny (Bitling) first contact design. March 2026.*
