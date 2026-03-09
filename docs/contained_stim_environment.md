# Designing a Contained Stim Environment
### For Two Nervous Systems in the Same Room

---

## The Actual Problem Being Solved

Standard educational software is designed for one user: the child. This document is designed for two: the child and the parent in the room with them.

A child who stims is regulating. The stimming is not the problem — it is the solution their nervous system found for managing sensory and emotional load. Suppressing it without replacement causes dysregulation. The goal is never to eliminate stimming. The goal is to create a bounded, predictable environment where stimming happens in a way that meets the child's regulatory needs without producing unpredictable sensory output that destabilizes the parent's nervous system.

The core design principle: **predictable stimulation is categorically different from unpredictable stimulation.**

A child making random sounds in a room is dysregulating for a sensory-sensitive adult because it has no pattern to anticipate. A child making sounds in response to a screen interaction is a different signal — it has a trigger, a shape, and a predictable envelope. The parent's nervous system can habituate to it. It stops being a startle and becomes background that can be filtered.

Everything in this document is oriented toward that distinction.

---

## Understanding the Stim Types in Play

Before designing for them, name them. Stims cluster by sensory channel and serve specific regulatory functions. Designing the wrong stim mechanic for a child's actual stim profile wastes effort.

| Stim Type | What it looks like | What it does for the nervous system |
|-----------|-------------------|-------------------------------------|
| **Auditory** | Echolalia, humming, repeating sounds/phrases | Processes and regulates auditory input, often reinforces language |
| **Visual** | Watching things spin/flicker, tracking motion, pattern staring | Regulates visual cortex arousal, can be deeply calming or exciting |
| **Tactile** | Rubbing, tapping, scratching surfaces, touching textures | Grounds the body in physical reality, calms proprioceptive system |
| **Proprioceptive** | Pressing, pushing, heavy work, jumping | Deep pressure input that directly regulates the autonomic nervous system |
| **Vestibular** | Rocking, spinning, swinging | Regulates the balance system, often deeply calming for high-arousal states |
| **Oral** | Chewing, mouthing objects, specific food textures | Proprioceptive regulation via jaw |

For a child with echolalia specifically: the echoing is an auditory processing strategy. He is repeating what he heard to process it, store it, and sometimes communicate through it. It is not random. Designing Bitling's speech to be echo-friendly is not accommodation — it is working with the mechanism instead of against it.

---

## Part 1: Sound Design as Nervous System Design

Sound is the highest-impact lever for the parent's sensory system. Most apps treat audio as a feature. Here it is treated as a regulated environment.

### The Sound Family Principle

Every audio element in a Bitling session should belong to the same tonal family — a consistent set of pitches, timbres, and harmonic relationships. When all sounds share a tonal family, the ear habituates faster. The parent's nervous system stops processing each sound as novel and starts filing them as "known Bitling sounds." This is the difference between background and interruption.

**Practical implementation:**
- Pick a root key for the session (e.g., C major, pentatonic)
- All interface sounds, celebration sounds, and Bitling vocalizations use only notes from that set
- Kokoro TTS voice is not in a fixed key but its timbre stays consistent — same voice, same prosody style, same volume range throughout
- No atonal "error" sounds — if something goes wrong, the sound is a gentle descending tone in the session key, not a buzzer

### Volume Architecture

No sound in a Bitling session should be louder than the established session baseline. No sudden spikes. The parent should be able to mentally set a volume floor and know nothing will exceed it.

**Rules:**
- Session starts at 60% of maximum system volume
- All celebration sounds are volume-normalized before playback — a big celebration is not louder, it is longer or more layered
- Hard cap at session volume level — no individual sound exceeds it regardless of event size
- Soft attack on all sounds — no instantaneous onset, every sound has a short ramp-up (even 20ms makes a significant perceptual difference for sensory-sensitive adults)

### Predictable Sound Triggers

Map every sound to a visible trigger so both the child and parent know what's coming. Random ambient sounds are eliminated. Every sound has a cause.

| Trigger | Sound | Character |
|---------|-------|-----------|
| Child taps | Short warm chime | Always the same — habituates fast |
| Bitling speaks | Kokoro voice, consistent prosody | Not speech-to-voice surprise |
| Successful action | 2–3 layered harmonic tones, ascending | Predictable shape, no surprises |
| Bitling celebrates | Extended version of success sound + voice | Bigger but same family |
| Transition between modes | Soft descending tone | Signals change is coming |
| Rest/stabilize mode | Low single tone, long decay | Clear signal: quieter period starting |
| Writing pad input | Soft scratch texture, matches pressure | Direct sensory mapping |

### Silence as a Feature

Silence is not dead air. Silence is a scheduled component of the session. The Regulation Engine's pause/wait mechanic already creates conversational silence — this should be framed as "Bitling is thinking" with a visible animation, so it reads as meaningful rather than broken.

Additionally: each session should have at least one explicit "quiet stretch" per major episode segment. Not silence meaning nothing is happening, but a lower-intensity period where the auditory environment drops to near-zero and the interaction shifts to tactile (writing pad) or visual-only. This gives both nervous systems a rest point.

---

## Part 2: Echolalia-First Speech Design

Echolalia is a language processing strategy. Bitling's speech should be designed to work *with* it rather than around it.

### What Makes Speech Echo-Friendly

Speech that gets echoed tends to have specific characteristics: it is short, rhythmically distinct, phonetically satisfying, and emotionally resonant. This is why children echo TV shows and songs more than conversational speech. The speech has shape.

**Design rules for Bitling's generated dialogue:**
- Sentences under 7 words when possible for key phrases
- Use alliteration, assonance, and rhythm naturally ("We found the big blue rock")
- Repeat key words within a sentence ("The door is stuck. Really stuck.")
- End on a distinct, satisfying syllable — not a trailing preposition or weak vowel
- Vary sentence rhythm deliberately — short-short-long, not uniform
- Avoid run-on sentences that blend into each other acoustically

### Building Echo Into the Interaction Mechanic

Do not treat echoed phrases as noise or error. Treat them as valid input.

**Echo-as-input design:**
- Whisper.cpp STT detects when the child repeats a phrase Bitling just said
- This is logged as a `echo_response` event — a form of engagement, not non-response
- Bitling reacts to echoed phrases positively: "Yes! Exactly that!"
- Repeated echoes of the same phrase signal high engagement with that content — flag it for the Interest Engine

**Call-and-echo games:**
Design specific mechanics built entirely around intentional echoing:
- Bitling says a word or phrase → waits → child echoes → Bitling reacts with delight
- The echo IS the correct response, not a substitute for a different response
- Gradually introduce variation: Bitling says "big dinosaur" → child echoes → Bitling says "big... what kind?" → child echoes "dinosaur" → correct
- This scaffolds the echo into productive language use without ever treating the echo as wrong

**Phrase design for high echo-value:**
- "More, more, more!" (rhythmic, repeatable)
- "Found it. Found it. Found it." (satisfying repetition)
- "That's the one." (short, decisive, phonetically clean)
- "Oh no oh no oh no." (emotion-clear, highly echoed in media children repeat)
- "Ready? Ready. Ready!" (builds anticipation pattern)

### The Echolalia Log

Store echoed phrases in the child's Postgres profile as a running list. High-frequency echoes tell you what language is landing and what is emotionally resonant for this child. Feed those patterns back into the dialogue generator as preferred phrase structures.

---

## Part 3: Visual Stim Design

Visual stims work best when they are deliberately satisfying loops rather than random animations.

### Designed Stim Loops vs Incidental Animation

Standard app animations are designed to not be annoying when repeated — they are neutral. Stim-designed animations are specifically crafted to be satisfying to watch loop. The difference is intentionality.

**Properties of a good visual stim loop:**
- Predictable cycle length (2–4 seconds is ideal for sustained attention)
- Smooth, easing motion — no hard stops or sudden direction changes
- Clear beginning and end that connect seamlessly
- Color progression that feels complete (not arbitrary)
- Something in the loop that "resolves" — a visual tension and release

**Bitling idle animation as stim loop:**
When Bitling is in wait/pause mode, its idle animation should be a designed stim loop — not random fidgeting, but a consistent, smooth, satisfying motion. Breathing, a gentle sway, or a repeating small action that has clear periodicity. The parent's eye habituates to a periodic motion much faster than an irregular one.

**Reward animations as stim design:**
The celebration animations should be designed as satisfying visual loops that the child wants to trigger again. The Catcher game's over-the-top celebration is stim-designed by nature — but make it visually coherent rather than chaotic. Confetti that follows predictable arcs. Bitling's victory dance that has a repeatable rhythm. These are worth animating carefully.

### Satisfying Repeat Mechanics

Some interactions should be specifically designed to be worth triggering repeatedly:

- **The Bounce**: Tap a thing, it bounces. Every bounce is the same. The predictability is the point. Child taps it forty times. That's fine. The writing pad captures the regularity of the tapping as a regulation signal.
- **The Reveal**: Drag to uncover something. The reveal animation is always the same shape. The satisfaction is in the predictability of what happens when you drag.
- **The Echo Visual**: Child echoes a phrase → a visual ripple follows the sound → same ripple every time. Pairs auditory and visual stim channels into one synchronized loop.

---

## Part 4: Proprioceptive Channel — The Writing Pad

The writing pad is already in the architecture. Its highest stim value is proprioceptive: it gives the child a surface to press against, to push into, to feel resistance from.

### Heavy Work Mechanics

Proprioceptive input — deep pressure, resistance, pushing — is the single most effective regulatory stim for many children with sensory processing differences. Design specific writing pad interactions that require sustained pressure:

**Push mechanics:**
- "Help Bitling push the boulder" → child presses and holds hard on tablet → Bitling strains, boulder moves, obvious cause-and-effect
- The pressure telemetry is already captured — a sustained high-pressure hold is read as intentional push, not error
- Payoff is proportional to pressure held: push harder, boulder moves faster

**Tracing mechanics:**
- Heavy trace: child traces a thick path, resistance is simulated via haptic feedback if available, the visual path fills in with clear progress
- The completeness of the fill is the reward, not a score

**Stamping mechanics:**
- Child presses stylus/finger firmly to stamp marks on the screen
- Each stamp produces the same satisfying sound + visual pop
- Highly repeatable, proprioceptively satisfying, no wrong answer

### Reading Pressure as Regulatory State

The writing pad already captures pressure. Extend the regulation signal dictionary:

| Pressure Pattern | Regulatory Signal |
|-----------------|------------------|
| Consistent medium pressure | Flow state, engaged |
| Gradually increasing pressure | Rising tension, approaching overload |
| Sharp pressure spikes | Active frustration or seeking proprioceptive input |
| Very light, hesitant pressure | Withdrawal, low engagement |
| Hard sustained pressure + smooth stroke | Proprioceptive seeking — route to heavy work mechanics |
| Hard sustained pressure + erratic stroke | Dysregulation — route to stabilize |

---

## Part 5: Structured Movement Breaks as Vestibular Stim

The screen cannot provide vestibular input (rocking, spinning, swinging), but Bitling can call for it in a structured way that makes it predictable for the parent.

### Why Structured Movement Matters for the Parent

Unstructured movement — a child suddenly jumping, running, spinning because they're overstimulated — is unpredictable and often dysregulating for a sensory-sensitive adult nearby. The same movement, preceded by a 5-second warning and contained to a specific duration, reads completely differently. The parent's nervous system has time to prepare.

### Movement Break Design

Bitling calls movement breaks as a normal part of the episode grammar — not as a response to dysregulation, but as a built-in beat. This normalizes them and makes them predictable.

**Structure:**
1. Bitling announces: "Okay. We need to do five big jumps before the next part. Ready?"
2. 3-second countdown visible on screen
3. Bitling counts out loud as the child jumps (uses STT to detect if child is counting along)
4. Defined endpoint: five jumps, done, return to seated
5. Transition sound signals end of movement break, return to screen

**Movement break types** (predictable, bounded, specific):
- Jump series (5, 10 jumps — specific count, clear end)
- Spin once each direction — and stop (vestibular + defined endpoint)
- Push against a wall for 10 seconds (proprioceptive, parent can prepare)
- Shake everything out for 5 seconds then freeze (classic regulation technique)
- March in place 20 steps

The parent knows the break is coming, knows its shape, knows when it ends. Predictable.

---

## Part 6: Stim Mode as a First-Class Teaching Mode

The existing mode list: `explore`, `engage`, `advance`, `practice`, `stabilize`, `repair`, `recover`, `rest`, `co_play`.

Add: **`stim`**

This is not a failure state. It is not triggered by dysregulation. It is a valid, intentional mode entered when the child is stim-seeking but otherwise regulated. The distinction: stim-seeking is not the same as dysregulating. A child who is contentedly stimming is regulated. A child who is stimming while escalating is dysregulating.

### Stim Mode Properties

| Property | Value |
|----------|-------|
| Demand level | Zero — no correct answers, no tasks |
| Interaction type | Pure cause-and-effect loops |
| Repeatability | Infinite — same action can trigger same response 100 times |
| Learning integration | Passive only — language in Bitling's speech, not assessed |
| Exit trigger | Child initiates transition, or Regulation Engine detects stim-satisfied state |
| Parent experience | Most predictable session mode — lowest novelty load |

### Stim Mode Mechanics

**Sound loop:** Child taps/presses anything → same satisfying sound → repeat forever. The point is that the response is 100% predictable and 100% consistent.

**Echo loop:** Bitling says a phrase → child echoes → Bitling responds warmly → Bitling says next phrase. Pure call-and-echo with no wrong answers.

**Visual trigger loop:** Child interacts → visual loop plays → resets → child interacts again. The loop is designed to be satisfying enough to want to restart.

**Heavy press loop:** Child pushes hard on writing pad → something on screen strains and moves → releases → returns to start. Designed for sustained proprioceptive seeking.

### Detecting Stim-Seeking vs Dysregulation

These look similar but are different states. Key distinguishing signals:

| Signal | Stim-Seeking (regulated) | Dysregulating |
|--------|--------------------------|---------------|
| Writing pressure | Consistent, rhythmic | Spiking, erratic |
| Interaction latency | Short, regular | Irregular, long gaps |
| Repetition pattern | Steady rhythm | Increasing urgency |
| Response to Bitling | Engaged, echoes | Ignoring or opposing |
| Duration | Sustainable, self-limiting | Escalating |

When signals indicate stim-seeking (regulated), route to stim mode. When signals indicate escalation, route to stabilize then recover as current architecture handles.

---

## Part 7: The Parent Sensory Configuration

Most applications model one user. This models two.

### Parent Profile in Postgres

Add a `parent_sensory_config` record alongside the child profile:

```json
{
  "session_volume_cap": 0.6,
  "sound_family_preference": "warm_harmonic",
  "hard_attack_sounds": "disabled",
  "movement_break_pre_announce_seconds": 5,
  "ambient_sound": "disabled",
  "celebration_style": "extended_not_louder",
  "session_start_notification": true,
  "max_celebration_duration_seconds": 4,
  "preferred_quiet_stretch_frequency": "every_3_loops"
}
```

These settings are not about limiting the child's experience. They are about making the parent's sensory environment manageable so they can stay in the room, stay regulated, and co-regulate when needed.

### Session Start Notification

Before Bitling begins speaking, a brief notification — a soft chime or visual indicator on a parent-facing display — announces the session is starting. This gives the parent's nervous system 2–3 seconds to shift from ambient background processing to "Bitling session audio is about to start." That window is enough to prevent the startle response.

### The Parent Sensory Log

Just as writing pad pressure is logged as a child regulatory signal, a parent-facing signal channel can be added. This is entirely opt-in and manual: a simple button or keyboard shortcut the parent can press when they notice they're being destabilized. This creates a log of which session moments, sounds, or interaction types are most costly for the parent's nervous system. Over time this refines the parent sensory config automatically.

---

## Part 8: Existing Architecture Integration

### What Already Works

The existing Progeny architecture has several components that map directly to contained stim design without modification:

**Regulation Engine:** Already detects overload and shifts modes. Extend its signal dictionary to distinguish stim-seeking from dysregulation (see Part 6 signal table). Add `stim` as a valid target mode.

**Writing pad telemetry:** Already captures pressure and motor patterns. Already feeds the regulation signal. Add the proprioceptive-seeking pattern recognition from Part 4.

**Kokoro TTS:** Already produces consistent voice output. Apply the volume normalization and soft attack rules at the Kokoro output layer so they apply universally.

**Teaching modes:** `co_play` and `rest` are already the closest to stim-friendly modes. `stim` mode is an addition, not a replacement. `rest` remains for low-engagement recovery. `stim` is for active, happy stimming.

**Open Brain memory:** Already stores interaction patterns. Add stim pattern tracking: which triggers produce the longest sustained stim engagement, which echoes are most frequent, which mechanics produce stim-satisfied transitions.

**Trust stages:** Stim behavior typically peaks in early trust stages (safety/familiarity) and naturally reduces as trust builds — not because stimming was suppressed but because the child's baseline regulation improves in familiar, safe environments. Track stim-mode frequency against trust stage as a natural longitudinal signal.

**Interest Engine:** Stims cluster around hyper-fixations. Dinosaur stim loops will be more effective than generic ones. Route all stim mode content through the interest anchor.

### What Needs to Be Added

**Stim profile record in Postgres:**
```sql
CREATE TABLE child_stim_profile (
    child_id UUID REFERENCES children(id),
    stim_type VARCHAR(50),          -- auditory, visual, tactile, proprioceptive, vestibular
    specific_behavior TEXT,          -- echolalia, jumping, pressing, etc.
    satisfying_trigger TEXT,         -- what in Bitling satisfies this stim
    parent_impact VARCHAR(20),       -- low, moderate, high (impact on parent's sensory system)
    bitling_mechanic TEXT,           -- which game/mechanic maps to this stim
    observed_at TIMESTAMPTZ,
    notes TEXT
);
```

**Stim-seeking detection in regulation signal:**
```python
# Add to regulation signal processing
STIM_SEEKING_SIGNALS = {
    "rhythmic_pressure": lambda p: p["pressure_rhythm_score"] > 0.7,
    "repetitive_trigger": lambda e: e["same_trigger_count_60s"] > 5,
    "echo_frequency": lambda s: s["echo_rate_per_minute"] > 3,
    "consistent_low_latency": lambda l: l["response_latency_variance"] < 0.1,
}

def detect_stim_state(signals):
    stim_score = sum(fn(signals) for fn in STIM_SEEKING_SIGNALS.values())
    escalation_score = signals.get("escalation_score", 0)

    if stim_score >= 2 and escalation_score < 0.4:
        return "stim_seeking"     # happy stimming, route to stim mode
    elif stim_score >= 2 and escalation_score >= 0.4:
        return "dysregulating"    # stimming + escalating, route to stabilize
    return "nominal"
```

**Sound normalization layer:**
```python
# Wrap all audio output through this before playback
def normalized_audio_output(sound_file, session_volume_cap=0.6):
    audio = load_audio(sound_file)
    audio = apply_soft_attack(audio, attack_ms=20)
    audio = normalize_to_cap(audio, cap=session_volume_cap)
    audio = apply_tonal_family_filter(audio, session_key="C_major_pentatonic")
    return audio
```

**WebSocket additions for stim state:**
```
Client -> Brain:
  - `parent_sensory_signal`   (parent manually logs destabilization event)

Brain -> Client:
  - `stim_mode_entered`       (Bitling entering stim mode)
  - `movement_break_incoming` (advance warning for parent)
  - `session_starting`        (pre-session notification)
  - `stim_state_update`       (stim-seeking vs nominal vs dysregulating)
```

---

## Summary: The Design Compact

This document is built on one compact between the system and both people using it:

**For the child:** You get to stim. The environment is built to make your stimming satisfying, responsive, and matched to your actual regulatory needs. Nothing here is trying to make you stop.

**For the parent:** The stimming that happens in a Bitling session will be predictable. You will know what sounds are coming, when they're coming, and what shape they'll take. Your nervous system will habituate to the session's sound environment. The random, uncontained stimming that hits you sideways is the problem this solves — not the stimming itself.

The goal is not a quiet child. The goal is a house where two dysregulated nervous systems have enough structure to coexist without one coming apart at the expense of the other.

---

*Document for Progeny (Bitling) contained stim environment design. March 2026.*
