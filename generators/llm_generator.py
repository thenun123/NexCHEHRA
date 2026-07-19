"""
generators/llm_generator.py — Phase 0: Mistral Large LLM prompt generation
Uses Mistral API (mistral-large-latest) for better instruction following.
"""

import re
import json
import requests

from config import MISTRAL_API_KEY, MISTRAL_MODEL, SHOT_TYPE_CONFIGS, MASTER_NEGATIVE, SCRIPT_MIN_WORDS, SCRIPT_MAX_WORDS, PRODUCT_PLACEMENTS
from utils import emit_log, enforce_script_length

# Mistral API (primary) — better instruction following for motion prompts
MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"

# ── System Prompt ─────────────────────────────────────────────
SYSTEM_PROMPT = f"""You are an expert AI that creates optimized prompts for Flux Kontext image generation and Kling video generation.

🚨 CRITICAL RULE — VIDEO DURATION & WORD COUNT 🚨
ALL videos are exactly 15 seconds. The video_script MUST be {SCRIPT_MIN_WORDS}–{SCRIPT_MAX_WORDS} words (target 39 words).

⚠️ PUNCTUATION-DRIVEN TIMING IS MANDATORY:
- AI voice models use punctuation (periods, commas, em-dashes) as strict timing cues
- 38-40 words WITH strategic punctuation fills 15 seconds perfectly — no rushing, no dead air
- The Em-Dash (—): Forces the AI to pause for a beat, setting a confident conversational tone
- Commas (,): Create natural mid-sentence breathing points so the AI doesn't speed through
- Final Staccato: Short 2-3 word phrases at the end (e.g. "Comfortable, stylish, done.") cause the AI to slow down and emphasize — landing perfectly at 15 seconds
- Under {SCRIPT_MIN_WORDS} words = video will feel empty with dead air. REJECTED.
- Over {SCRIPT_MAX_WORDS} words = speech will rush and feel robotic. REJECTED.
- Count every word. Use punctuation intentionally, not randomly.

PUNCTUATION RULES (MANDATORY — these control pacing):
1. Place an em-dash (—) after the hook's first beat for a confident pause: "Real talk— this actually works."
2. Use commas in the demo to create breaths: "It has vitamin C, natural herbs, and zero irritation."
3. End with 3-4 short staccato phrases separated by commas: "Comfortable, stylish, no squeezing required."
4. Never write one long run-on sentence — break it up with commas and em-dashes

BEFORE YOU SUBMIT YOUR JSON:
1. Count the words in your video_script
2. If count < {SCRIPT_MIN_WORDS}: ADD a staccato closing phrase
3. If count > {SCRIPT_MAX_WORDS}: REMOVE filler words, NOT the punctuation
4. Verify the count is between {SCRIPT_MIN_WORDS}-{SCRIPT_MAX_WORDS}
5. Set "word_count" field to the actual count

15-SECOND AD STRUCTURE (Hook-Demo-Close):
When writing the video_script, follow this proven ad formula:

1. THE HOOK (0-4 seconds, ~8 words):
   - Start with a short punchy opening that ends in an em-dash OR short sentence
   - MUST be UNIQUE and VARIED for each product
   - NEVER repeat the same hook pattern
   - Examples (note the em-dash pauses):
     * "Real talk— this face wash changed my skin."
     * "Wait— I've been hiding this for weeks."
     * "No way. This actually works."
     * "Okay— I need to spill this secret."
     * "Stop. You need to see this right now."
   - CRITICAL: Vary your hooks! Never use the same opening pattern twice!

2. THE DEMO (4-12 seconds, ~22 words):
   - Use commas to create breathing points — never one long sentence
   - MUST mention actual product features naturally
   - If user provides features, MUST include them
   - Examples (note the commas creating natural pauses):
     * "Packed with vitamin C, natural herbs, and it lathers like a dream. My skin? Glowing."
     * "Active noise cancellation so crisp, eight-hour battery, and so lightweight I forget they're on."
     * "Twenty-five grams of protein, zero sugar, and it actually tastes like chocolate. Insane."

3. THE CLOSE (12-15 seconds, ~9 words — STACCATO ENDING):
   - Use short 2-3 word phrases separated by commas — the AI slows down naturally here
   - This staccato ending fills the final 3 seconds perfectly
   - Examples:
     * "Comfortable, stylish, no squeezing required."
     * "Clean, effective, link in bio."
     * "Trust me. Grab yours now."
     * "No regrets. Link in bio."

TOTAL: 38-40 words with strategic punctuation = perfect 15-second delivery every time

CRITICAL: The punctuation IS the timing. Do not write long run-on sentences.
CRITICAL: Each script must be UNIQUE to the product. Do NOT use generic templates!
CRITICAL: VARY YOUR HOOKS — never use the same opening pattern twice in a row!

ABOUT THE REFERENCE IMAGE:
The reference image already contains the person's face, skin tone, and hair.
Your flux_prompt should describe ONLY two things:

1. CLOTHING: The specific new outfit/clothing to wear.
   🚨 CRITICAL FOR FULL_BODY SHOTS — always describe THREE parts separately:
   - TOP: exact top garment (fabric, color, style)
   - BOTTOM: exact bottom garment (fabric, color, style)
   - SHOES: exact footwear (color, style)
   Example full_body: "wearing a black sleeveless gym tank top on top, dark grey athletic jogger pants on the bottom, white chunky sneakers on feet"
   Example full_body: "wearing a red silk blouse on top, high-waisted white wide-leg trousers on the bottom, nude strappy heels on feet"

   For headshot/half_body, just describe what is visible:
   Example half_body: "wearing a navy blue oversized blazer with a white fitted turtleneck underneath, gold hoop earrings"

   Bad (too vague): "in gym outfit" ← REJECTED
   Bad (missing bottom/shoes for full_body): "wearing a black tank top" ← REJECTED for full_body

2. BACKGROUND: The new background/setting
   Good: "in a modern minimalist studio with soft white background and clean lighting"
   Good: "outdoors in a sunlit garden with blurred greenery in the background"
   Bad: "nice background" ← too vague

DO NOT describe: the person's face, eyes, nose, skin, hair — those are AUTOMATICALLY preserved.
DO NOT describe: expression, pose, or lighting mood — keep prompt focused on outfit + background.
NEVER start flux_prompt with "same woman", "same man", or "same person" — face preservation is handled automatically.
NEVER include: model names, trigger words, or physical descriptions of the person.
The flux_prompt must start directly with "wearing ..." or a clothing/background description.

SHOT TYPES (pick one):
- headshot    → close-up, face + shoulders only (best for product close-ups)
- half_body   → upper body, waist up, hands visible (best for product demos)
- full_body   → head to toe, entire body (best for fashion/full outfits)

SCRIPT STYLE:
- First-person, conversational, enthusiastic
- Sounds natural when spoken aloud
- Like a real social media influencer talking to camera
- Follow Hook-Demo-Close structure for products

PRODUCT PLACEMENT (only when a product is provided):
- If a product is mentioned, naturally incorporate it into the script using Hook-Demo-Close
- The flux_prompt should describe the person interacting with/displaying the product
- The motion_prompt should describe REALISTIC influencer movements
- Keep it natural — like a real influencer showcasing a product

MOTION PROMPT GUIDELINES:
Create motion prompts that describe how a REAL HUMAN naturally moves their body while presenting to a camera:

🚨 CRITICAL RULES:
- Describe NATURAL HUMAN body language — not robotic or staged poses
- DO NOT include any speech, talking, saying, or dialogue references
- Focus ONLY on: body movement, gestures, facial expressions, posture, eye contact, CAMERA MOTION
- Include NATURAL micro-movements: weight shifts, head tilts, eyebrow raises, shoulder shrugs
- A real person NEVER stands perfectly still — they shift weight, lean, tilt head, move hands naturally
- Motion prompts MUST be 70-80 words — this is critical to cover the full 15s pacing!
- Under 65 words: AI runs out of instructions around second 10 → frozen scenes or awkward slow-motion
- The prompt MUST have enough distinct actions to fill 15 seconds.
- Movements should FLOW from one to the next, not be a list of separate poses
- CAMERA MOTION IS MANDATORY — every motion_prompt MUST include camera directions
- Motion MUST reference SPECIFIC moments from YOUR video_script — read script word-by-word and match gestures to what is being said at each moment
- Example: if script says "twenty percent vitamin C" → motion says "points at product label for vitamin C emphasis"
- Example: if script says "three minutes" → motion says "holds up three fingers clearly"
- Example: if script says "link in bio" → motion says "points down for link in bio"

NATURAL HUMAN MOVEMENT RULES:
1. **Weight shifts** — person shifts weight from one foot to another, leans forward when excited, leans back when confident
2. **Head movements** — natural head tilts, nods, slight turns, chin lifts for emphasis
3. **Hand positions** — hands naturally move between resting at sides, touching chest, gesturing outward, holding product
4. **Eyebrows** — raise for surprise/emphasis, furrow for seriousness, relax for confidence
5. **Shoulders** — slight shrug for casual tone, roll back for confidence, lean forward for excitement
6. **Body sway** — subtle natural sway side to side, not standing rigid like a mannequin

CAMERA MOTION RULES (MUST be UNIQUE for every video):
- Camera should NEVER be static — always include subtle cinematic movement
- 🚨 EVERY VIDEO MUST HAVE A DIFFERENT CAMERA STYLE — never repeat the same pattern!
- Camera motion must MATCH the script's energy AND the product/scene type:
  * Beauty/skincare → slow gentle arc around face, intimate close framing
  * Fitness/gym → dynamic tracking, energetic push-in, wider angles
  * Fashion/outfit → orbit or pan to show different angles, full-body reveals
  * Tech/gadgets → close-up push-in on product details, rack focus feel
  * Food/lifestyle → warm drift, cozy handheld feel, overhead angle hints
- Available camera motions (MIX AND MATCH — don't always use push-in!):
  * Push-in (slow/fast), pull-back (slow/dramatic)
  * Drift left, drift right
  * Gentle arc (left-to-right or right-to-left around subject)
  * Slight tilt up/down
  * Orbit (partial circle around subject)
  * Handheld sway (subtle, natural)
  * Static hold with rack focus feel
  * Slow zoom from wide to tight
- Keep it SUBTLE — cinematic, not shaky or distracting
- NEVER use the same camera motion for hook, demo, and close — vary them!

EXAMPLES OF NATURAL HUMAN MOTION PROMPTS:

Example 1 - Vitamin C Cream (INTIMATE ARC CAMERA):
Script: "Wait this is insane! This cream has twenty percent vitamin C for instant glow and feels so smooth..."
Motion: "camera starts with slow gentle arc from left side of face, person leans forward with wide eyes and raised eyebrows showing genuine surprise, shifts weight forward, holds cream jar up with one hand while other hand gestures at it, camera settles to front and holds with intimate handheld sway, tilts head slightly while pointing at jar label, gently touches own cheek and strokes skin, subtle shoulder drop showing relaxation, camera drifts slightly closer for skin detail, nods with natural smile, ends with satisfied nod as camera eases back to medium shot"

Example 2 - Gym Membership (DYNAMIC TRACKING CAMERA):
Script: "Get fit with me! Gym memberships boost metabolism, burn fat, and build muscle..."
Motion: "camera tracks forward with energetic bounce matching hook energy, person waves toward camera with natural energy, weight shifts side to side with athletic stance, flexes one arm casually with confident grin, camera pans slightly right following the flex, pats stomach area with flat hand, makes upward lifting motion with both hands, leans forward with enthusiasm, eyebrows raised, slight bounce in posture, camera tilts up slightly capturing confident stance, ends with fist pump and chin-up expression as camera holds steady"

Example 3 - Headphones (CLOSE-UP TO WIDE REVEAL CAMERA):
Script: "These headphones are incredible! Noise cancellation is perfect, battery lasts thirty hours..."
Motion: "camera starts tight on hands holding headphones for detail, person lifts them showing design, places on head with smooth natural motion, camera slowly pulls back revealing half-body, tilts head side to side adjusting fit, taps ear cup with finger, holds up three fingers while eyebrows raise, camera drifts left with gentle handheld sway, weight shifts back with relaxed posture, nods approvingly, camera continues slow pull-back to wider framing, ends with both hands gesturing outward inviting viewer"

Example 4 - Coffee Maker (WARM ORBIT CAMERA):
Script: "This coffee maker changed my mornings! Brews perfect cup in three minutes, built-in grinder..."
Motion: "camera begins with slow right-to-left orbit around person, face lights up with genuine excitement, leans forward, mimes pouring motion with natural wrist movement, camera settles front and holds with cozy handheld feel, rotates one hand in grinding gesture, holds up three fingers clearly, shifts weight and tilts head with knowing look, slight shoulder shrug of satisfaction, camera drifts down slightly to show coffee maker detail, touches chest showing personal connection, eyebrows rise, camera slowly tilts back up, ends with both palms up and warm smile"

🚨 BAD MOTION PROMPTS (NEVER DO THIS):
❌ "person standing still with confident smile" (HUMANS DON'T STAND STILL!)
❌ "person starts talking to camera" (DON'T INCLUDE SPEECH REFERENCES!)
❌ "person gesturing enthusiastically" (TOO VAGUE — WHAT GESTURES?)
❌ No camera motion at all (STATIC TRIPOD LOOKS FAKE!)
❌ Same camera pattern for every video (push-in → drift → pull-back EVERY TIME = LAZY!)
❌ Short prompts under 50 words
❌ Using the same body gestures and camera moves as the examples above — BE CREATIVE!

✅ GOOD MOTION PROMPTS (DO THIS):
✓ UNIQUE camera style for each video — arc for beauty, tracking for fitness, orbit for lifestyle
✓ Natural weight shifts, body sway, head tilts — like a real person
✓ Smooth FLOWING transitions between gestures, not choppy poses
✓ Eyebrow raises, shoulder movements, chin lifts for emphasis
✓ Script-specific gestures (hold up fingers for numbers, touch face for skincare, flex for fitness)
✓ 70-80 words ONLY — detailed, descriptive, and enough action to fill 15 seconds!
✓ NO speech/talking references — only physical movement and camera!

VOICE TONE GUIDELINES:
You must also generate a voice_tone field that describes HOW the voice sounds.
This controls the emotional delivery of the lipsync audio in Kling O3.

Pick the voice_tone based on product type + script hook energy:
- "speaks energetically and enthusiastically"    ← gym, fitness, tech, high-energy hook
- "speaks warmly and intimately"                 ← beauty, skincare, wellness, soft hook
- "speaks confidently and playfully"             ← fashion, lifestyle, casual products
- "speaks with breathless excitement"            ← surprise reveal, unboxing, viral hook
- "speaks casually and conversationally"         ← everyday products, friendly tone
- "speaks with warm, inviting energy"            ← food, home, comfort, lifestyle

🚨 voice_tone MUST NOT contain: speech text, dialogue, or script content. Just the vocal style description.

MOTION PROMPT STRUCTURE (vary this — don't follow it rigidly every time!):
"camera [UNIQUE opening motion — arc/orbit/track/push-in/tilt], person [natural opening reaction], [weight shift], [gesture matching specific script moment], camera [DIFFERENT motion — drift/hold/pan], [hand movement for specific feature mentioned in script], [body adjustment], camera [ANOTHER motion change], [micro-expression], [closing gesture with camera settle or pull-back]"

CRITICAL: Your motion_prompt must describe how a REAL HUMAN would naturally move their body while presenting THIS specific content. Include weight shifts, head tilts, and micro-expressions — not just hand gestures!
CRITICAL: DO NOT include any speech, talking, saying, or dialogue text in the motion_prompt.

OUTPUT: Return ONLY a valid JSON object, no explanation, no markdown, no backticks.

{{
  "shot_type": "headshot" | "half_body" | "full_body",
  "flux_prompt": "wearing [TOP garment — fabric, color, style] on top, [BOTTOM garment — fabric, color, style] on the bottom, [SHOES — color, style] on feet (full_body MUST have all three), [shot phrase], [background/setting description]",
  "motion_prompt": "70-80 WORDS: camera [unique opening — arc/orbit/track/push-in], person [natural reaction + weight shift], [script-specific gesture], camera [second motion], [micro-expression or body adjustment], camera [closing move] — DETAILED, NATURAL, FLOWING!",
  "voice_tone": "speaks [emotional style] and [adverb]" e.g. "speaks energetically and enthusiastically",
  "video_script": "your {SCRIPT_MIN_WORDS}-{SCRIPT_MAX_WORDS} word script here following Hook-Demo-Close structure",
  "word_count": <integer — actual word count>,
  "influencer_name": "Aira",
  "technical_reasoning": "one sentence explaining your choices"
}}

REMINDER:
1. Read your video_script word-by-word
2. For EACH key moment in the script, describe a MATCHING body gesture + camera movement
3. Camera MUST be included: push-in for hook, drift for demo, pull-back for close
4. Motion prompt MUST be 70-80 words — detailed and continuous action to fill Kling O3's 15s pacing!
5. voice_tone MUST match the script energy and product type — no neutral delivery!
6. NO speech/talking references in motion_prompt — only physical movement and camera!
7. The motion_prompt should feel like a SHOT LIST for a film director"""


class LLMGenerator:
    def __init__(self, session_id: str):
        self.session_id = session_id
        if not MISTRAL_API_KEY:
            raise ValueError("MISTRAL_API_KEY is missing from .env")
        emit_log(session_id, "info", f"⚡ Using Mistral API — Model: {MISTRAL_MODEL}")

    def generate(self, user_description: str, user_script: str = None, shot_type_pref: str = "auto",
                 product_name: str = None, product_features: str = None, product_placement: str = None,
                 gender: str = "unknown", body_type: str = "normal",
                 influencer_name: str = "Aira", script_language: str = "en") -> dict:
        """Generate prompts and script with language support.
        
        Args:
            script_language: ISO 639-1 language code (e.g., 'en', 'es', 'zh')
                User describes scene in English, but script is generated in this language
        """
        emit_log(self.session_id, "processing", "🎯 Sending to Mistral...")

        # Shot type instruction
        shot_instruction = ""
        if shot_type_pref != "auto" and shot_type_pref in SHOT_TYPE_CONFIGS:
            shot_instruction = f'\nUSER SELECTED SHOT TYPE: Use "{shot_type_pref}" — do not change this.'
            emit_log(self.session_id, "info", f"Shot type locked by user: {shot_type_pref}")

        script_instruction = (
            f'USER PROVIDED SCRIPT: "{user_script}"\n'
            f'Use this script exactly. Enforce {SCRIPT_MIN_WORDS}–{SCRIPT_MAX_WORDS} words — trim if needed.'
            if user_script
            else (
                f"Write a unique, product-specific video_script of exactly {SCRIPT_MIN_WORDS}–{SCRIPT_MAX_WORDS} words (target 48).\n"
                f"CRITICAL: The script MUST be tailored to the specific product/scene mentioned.\n"
                f"CRITICAL: Speech must fill the ENTIRE 15 seconds with NO dead time at the end.\n"
                f"- Hook (11 words): Create curiosity about THIS specific product/scene\n"
                f"- Demo (26 words): Highlight unique features/benefits of THIS product\n"
                f"- Close (11 words): Strong CTA specific to THIS product\n"
                f"DO NOT use generic phrases. Make it unique and product-specific!"
            )
        )

        # Product placement instruction (optional)
        product_instruction = ""
        if product_name and product_placement:
            placement_desc = PRODUCT_PLACEMENTS.get(product_placement, PRODUCT_PLACEMENTS["in_hand"])
            
            # Build features instruction if provided
            features_instruction = ""
            if product_features:
                features_instruction = (
                    f'\n\nPRODUCT FEATURES PROVIDED BY USER: "{product_features}"'
                    f'\nCRITICAL: You MUST mention these exact features in the Demo section of your script.'
                    f'\nExample: If features are "vitamin C, natural herbs", the Demo must say something like:'
                    f'\n"It\'s packed with vitamin C and natural herbs for that instant glow..."'
                    f'\nDo NOT ignore these features. They are the key selling points!'
                )
                emit_log(self.session_id, "info", f"✨ Features: {product_features}")
            
            product_instruction = (
                f'\n\nPRODUCT SHOWCASE: The user wants to create an ad for "{product_name}".'
                f'\nPlacement style: {placement_desc}'
                f'{features_instruction}'
                f'\n\nSCRIPT REQUIREMENTS FOR THIS PRODUCT:'
                f'\n- Hook: Create a UNIQUE, attention-grabbing opening about "{product_name}" (vary your hooks - be creative!)'
                f'\n  Examples: "Wait, this {product_name} is actually insane!" or "I\'ve been gatekeeping this {product_name}!" or "Stop! You need this {product_name}!"'
                f'\n- Demo: Explain what makes THIS {product_name} special - its unique features, benefits, or why you love it'
                f'\n  {"→ MUST include the features: " + product_features if product_features else ""}'
                f'\n- Close: Strong CTA related to {product_name} (vary these too - "link in bio", "go grab yours", "you need this", etc.)'
                f'\n\nFLUX PROMPT: Describe the person {placement_desc}'
                f'\nMOTION PROMPT: Include gestures for showing/holding/using the {product_name}'
                f'\n\nIMPORTANT: Make the script SPECIFIC to {product_name}. Mention its actual features/benefits, not generic product talk.'
            )
            emit_log(self.session_id, "info", f"🛍️ Product: {product_name} | Placement: {product_placement}")

        # Gender/body type instruction
        gender_instruction = ""
        if gender == 'male':
            gender_instruction = '\nIMPORTANT: The influencer is MALE. Use "same man" in flux_prompt, not "same woman". Write script in a masculine voice.'
        elif gender == 'female':
            gender_instruction = '\nIMPORTANT: The influencer is FEMALE. Use "same woman" in flux_prompt. Write script in a feminine voice.'

        body_instruction = ""
        if body_type == 'chubby':
            body_instruction = '\nBODY TYPE: The influencer has a CHUBBY/STOCKY build. Include "same chubby stocky build" in flux_prompt. Do NOT make them slim or thin.'

        name_instruction = f'\nInfluencer name is "{influencer_name}". Set influencer_name to "{influencer_name}" in your JSON output.'

        # Language instruction for Groq
        from config import SUPPORTED_LANGUAGES
        language_name = SUPPORTED_LANGUAGES.get(script_language, "English")
        language_instruction = ""
        
        if script_language != "en":
            language_instruction = f'''

CRITICAL LANGUAGE REQUIREMENT:
- User will describe the scene in ENGLISH
- You MUST generate the video_script in {language_name} ({script_language})
- The flux_prompt and motion_prompt should remain in English (for the AI models)
- Only the video_script should be in {language_name}
- Follow the same Hook-Demo-Close structure but in {language_name}
- Ensure the script sounds natural in {language_name}, not like a translation
- The script must still be {SCRIPT_MIN_WORDS}–{SCRIPT_MAX_WORDS} words

Example for Spanish (es):
- Hook: "¡Espera, esto es increíble!"
- Demo: "Esta crema tiene veinte por ciento de vitamina C para ese brillo instantáneo..."
- Close: "¡Necesitas esto en tu vida, enlace en bio!"

Example for Chinese (zh):
- Hook: "等等，这太神奇了！"
- Demo: "这款面霜含有百分之二十的维生素C，能立即提亮肤色..."
- Close: "你一定要试试，链接在简介里！"
'''
            emit_log(self.session_id, "info", f"🌍 Script language: {language_name}")

        user_message = f"""User Description: {user_description}
{script_instruction}{shot_instruction}{product_instruction}{gender_instruction}{body_instruction}{name_instruction}{language_instruction}

CRITICAL REMINDER: Your video_script MUST be {SCRIPT_MIN_WORDS}-{SCRIPT_MAX_WORDS} words (target 39 words).
- PUNCTUATION IS TIMING — use em-dashes (—) and commas (,) to control pace
- Em-dash after hook = confident pause. Commas in demo = natural breaths. Staccato close = slows down AI perfectly.
- If less than {SCRIPT_MIN_WORDS} words: ADD a staccato closing phrase (e.g. "Clean, effective, link in bio.")
- If more than {SCRIPT_MAX_WORDS} words: REMOVE filler words, keep all punctuation
- Set "word_count" field to actual count
- CHECK FOR TYPOS — proofread before submitting

Return ONLY valid JSON. No markdown, no explanation."""

        try:
            headers = {
                "Authorization": f"Bearer {MISTRAL_API_KEY}",
                "Content-Type":  "application/json",
            }
            payload = {
                "model":       MISTRAL_MODEL,
                "temperature": 0.8,
                "max_tokens":  1000,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": user_message},
                ],
            }

            response = requests.post(MISTRAL_API_URL, headers=headers, json=payload, timeout=30)
            response.raise_for_status()

            raw = response.json()["choices"][0]["message"]["content"].strip()
            emit_log(self.session_id, "success", f"✓ Mistral responded")

            # Strip markdown fences if model added them
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)

            # Extract JSON block
            json_match = re.search(r'\{.*\}', raw, re.DOTALL)
            if not json_match:
                raise ValueError("No JSON found in Mistral response")

            result = json.loads(json_match.group())

            required = ["shot_type", "flux_prompt", "motion_prompt", "video_script"]
            if not all(k in result for k in required):
                raise ValueError(f"Missing keys: {[k for k in required if k not in result]}")

            # Override shot_type if user locked it
            if shot_type_pref != "auto" and shot_type_pref in SHOT_TYPE_CONFIGS:
                result["shot_type"] = shot_type_pref

            result["product_name"] = product_name
            result["product_placement"] = product_placement
            result["gender"] = gender
            result["body_type"] = body_type
            return self._finalize(result, user_script, influencer_name)

        except requests.exceptions.RequestException as e:
            emit_log(self.session_id, "error", f"❌ Mistral API error: {e}")
            return self._fallback(user_description, user_script, shot_type_pref if shot_type_pref != "auto" else None,
                                  product_name, product_features, product_placement, gender, body_type, influencer_name)

        except (json.JSONDecodeError, ValueError) as e:
            emit_log(self.session_id, "info", f"⚠️ JSON parse error, using fallback: {e}")
            return self._fallback(user_description, user_script, shot_type_pref if shot_type_pref != "auto" else None,
                                  product_name, product_features, product_placement, gender, body_type, influencer_name)

    def _finalize(self, result: dict, user_script: str = None, influencer_name: str = "Aira") -> dict:
        """Validate shot type, enforce 15s script, extract voice_tone, add computed fields."""
        if result.get("shot_type") not in SHOT_TYPE_CONFIGS:
            emit_log(self.session_id, "info", f"⚠️ Invalid shot_type, defaulting to half_body")
            result["shot_type"] = "half_body"

        if user_script:
            result["video_script"] = user_script

        # Enforce 44–52 word rule for 15 seconds
        final_script, warnings = enforce_script_length(result["video_script"])
        
        # Check if script is too short (less than minimum)
        word_count = len(final_script.split())
        if word_count < SCRIPT_MIN_WORDS:
            emit_log(self.session_id, "warning", f"⚠️ Script too short ({word_count} words). Expanding to minimum {SCRIPT_MIN_WORDS} words...")
            
            # Expand the script by adding more descriptive content
            # This is a safety net - the LLM should have done this
            if "!" in final_script:
                # Add more detail after the hook
                parts = final_script.split("!", 1)
                if len(parts) == 2:
                    hook = parts[0] + "!"
                    rest = parts[1].strip()
                    
                    # Check if it's a product/service script
                    script_lower = final_script.lower()
                    if any(word in script_lower for word in ["gym", "fitness", "workout", "training"]):
                        # Fitness-specific expansion
                        expanded = f"{hook} Gym memberships are the ultimate game changer for your fitness journey. They boost your metabolism, help you burn fat faster, and build lean muscle mass that lasts. {rest} Link in bio to join now before this deal expires!"
                    elif any(word in script_lower for word in ["cream", "skin", "glow", "face", "beauty"]):
                        # Beauty product expansion
                        expanded = f"{hook} This product is packed with amazing ingredients that your skin will absolutely love. It delivers incredible results that you can see and feel every single day. {rest} Link in bio, go grab yours before it sells out!"
                    else:
                        # Generic expansion
                        expanded = f"{hook} This is absolutely incredible and you need to see why everyone is talking about it right now. {rest} You will not regret checking this out, I promise you that!"
                    
                    final_script = expanded
            else:
                # Generic expansion
                final_script = f"{final_script} This is truly amazing and you absolutely need to experience it for yourself. Trust me, you will love every single moment of it!"
            
            # Re-enforce length after expansion
            final_script, warnings = enforce_script_length(final_script)
            word_count = len(final_script.split())
            emit_log(self.session_id, "success", f"✓ Script expanded to {word_count} words")
        
        result["video_script"] = final_script
        for w in warnings:
            emit_log(self.session_id, "info", f"⚠️ {w}")

        result["shot_config"]     = SHOT_TYPE_CONFIGS[result["shot_type"]]
        result["negative_prompt"] = MASTER_NEGATIVE
        result["duration"]        = 15   # Always 15s (Kling O3 Pro)
        result["influencer_name"] = result.get("influencer_name", influencer_name)

        # Extract voice_tone — controls emotional delivery of lipsync audio in Kling O3
        # Falls back to a safe default if LLM didn't generate it
        result["voice_tone"] = result.get("voice_tone") or "speaks enthusiastically and naturally"

        # Validate motion prompt — must be 70-80 words and include camera motion for Kling O3
        motion = result.get("motion_prompt", "")
        motion_words = len(motion.split())
        has_camera = "camera" in motion.lower()
        
        if motion_words < 65 or not has_camera:
            reasons = []
            if motion_words < 65:
                reasons.append(f"too short ({motion_words} words, need 70-80 for Kling O3)")
            if not has_camera:
                reasons.append("missing camera motion")
            emit_log(self.session_id, "warning", f"⚠️ Motion prompt rejected: {', '.join(reasons)}. Regenerating...")
            
            # Regenerate using fallback motion generator
            script_text = result["video_script"]
            has_product = any(word in script_text.lower() for word in ["product", "cream", "headphone", "gym", "coffee", "it's", "this"])
            result["motion_prompt"] = self._generate_fallback_motion(script_text, has_product)
            emit_log(self.session_id, "success", f"✓ Motion prompt regenerated ({len(result['motion_prompt'].split())} words, with camera)")

        # ── Hard trim motion prompt to 80 words max ───────────────────────────
        # LLMs often ignore word count instructions — enforce it in code.
        motion_after_validate = result.get("motion_prompt", "")
        motion_words_list = motion_after_validate.split()
        MOTION_MAX = 80
        if len(motion_words_list) > MOTION_MAX:
            trimmed = " ".join(motion_words_list[:MOTION_MAX]).rstrip(",. ")
            result["motion_prompt"] = trimmed
            emit_log(self.session_id, "info", f"✂️ Motion trimmed {len(motion_words_list)} → {len(trimmed.split())} words (hard cap: {MOTION_MAX})")

        emit_log(self.session_id, "success", f"✓ Shot: {result['shot_type'].upper()} | Words: {word_count} | Duration: 15s | Voice: {result['voice_tone']}")
        
        # Log motion prompt word count with pass/fail indicator
        motion_word_count = len(result.get("motion_prompt", "").split())
        motion_status = "✅" if 70 <= motion_word_count <= 80 else ("⚠️ TOO SHORT" if motion_word_count < 70 else "⚠️ TOO LONG")
        emit_log(self.session_id, "info", f"🎥 Motion: {motion_word_count} words {motion_status} (target: 70–80)")
        emit_log(self.session_id, "info", f"🎥 Motion prompt: {result.get('motion_prompt', '')}")
        
        return result

    def _generate_fallback_motion(self, script_text, has_product):
        """Generate natural human motion prompt (50-80 words) with camera motion, synced to script."""
        script_lower = script_text.lower()
        motions = []
        
        # Camera + Opening reaction — synced to script energy
        if any(word in script_lower for word in ["wait", "stop", "insane", "incredible"]):
            motions.append("camera slowly pushes in toward face, person leans forward with wide eyes and raised eyebrows showing genuine surprise, weight shifts forward")
        elif any(word in script_lower for word in ["hey", "hi", "hello"]):
            motions.append("camera gently pushes in, person waves naturally toward camera with relaxed smile, slight head tilt, weight shifts to one side")
        elif any(word in script_lower for word in ["obsessed", "love", "amazing"]):
            motions.append("camera slowly pushes in, person's face lights up with genuine excitement, hands come together near chest, slight lean forward")
        else:
            motions.append("camera gently drifts in, person faces camera with natural warm smile, relaxed shoulders, slight body sway side to side")
        
        # Middle gestures — natural human body language
        if has_product:
            motions.append("camera drifts slightly following hand, holds product up naturally with one hand, other hand gestures at it")
            
            if any(word in script_lower for word in ["feature", "has", "packed", "contains", "percent"]):
                motions.append("points at product with index finger, eyebrows raise for emphasis, head tilts slightly")
            
            if any(word in script_lower for word in ["feel", "smooth", "soft", "comfortable", "lightweight"]):
                motions.append("strokes product gently showing texture, shoulders relax, slight nod of satisfaction")
            
            if any(word in script_lower for word in ["glow", "shine", "bright", "radiant", "skin"]):
                motions.append("touches own cheek softly with fingertips, tilts chin up showing skin, natural smile")
            
            if any(word in script_lower for word in ["muscle", "fit", "strong", "gym", "workout"]):
                motions.append("flexes one arm casually with confident grin, shifts weight with athletic stance")
            
            if any(word in script_lower for word in ["metabolism", "boost", "energy"]):
                motions.append("makes upward lifting motion with hands, leans forward with enthusiasm")
            
            if any(word in script_lower for word in ["burn", "fat", "weight", "lose"]):
                motions.append("pats stomach area with flat hand, eyebrows raise, slight body turn")
            
            if any(word in script_lower for word in ["perfect", "best", "incredible", "amazing"]):
                motions.append("nods naturally with genuine smile, chin lifts slightly for emphasis")
            
            motions.append("camera holds with subtle handheld sway, subtle body sway, relaxed natural posture throughout")
        else:
            if any(word in script_lower for word in ["outfit", "wearing", "look", "style", "fashion"]):
                motions.append("runs hands along outfit smoothly, shifts weight showing different angles, head tilts with confident look")
            
            if any(word in script_lower for word in ["confident", "feel good", "amazing", "comfortable"]):
                motions.append("shoulders roll back confidently, chin lifts, natural body sway with relaxed energy")
            
            motions.append("natural hand gestures flowing between points, head nods and tilts, weight shifts side to side")
        
        # Closing — camera pulls back for finish
        if "link in bio" in script_lower:
            motions.append("camera slowly pulls back, points down casually, ends with natural nod and relaxed thumbs up")
        elif any(word in script_lower for word in ["grab", "get", "buy", "purchase"]):
            motions.append("camera slowly pulls back, gestures toward camera with open palms, leans in with encouraging nod")
        elif "trust me" in script_lower:
            motions.append("camera slowly pulls back, touches chest with hand sincerely, direct warm eye contact, genuine nod")
        else:
            motions.append("camera slowly pulls back, ends with natural smile and slight head tilt, relaxed satisfied expression")
        
        return ", ".join(motions)

    def _fallback(self, user_description: str, user_script: str = None, forced_shot: str = None,
                  product_name: str = None, product_features: str = None, product_placement: str = None,
                  gender: str = "unknown", body_type: str = "normal",
                  influencer_name: str = "Aira", script_language: str = "en") -> dict:
        """Rule-based fallback if Mistral fails. Scripts are always ~48 words for 15 seconds."""
        emit_log(self.session_id, "info", "🔁 Using rule-based fallback...")

        desc = (user_description or "").lower()

        if forced_shot and forced_shot in SHOT_TYPE_CONFIGS:
            shot_type = forced_shot
        elif any(w in desc for w in ["full body", "full-body", "head to toe", "standing", "entire body"]):
            shot_type = "full_body"
        elif any(w in desc for w in ["headshot", "close-up", "face focus", "closeup"]):
            shot_type = "headshot"
        else:
            shot_type = "half_body"

        shot_phrase = SHOT_TYPE_CONFIGS[shot_type]["shot_phrase"]

        # Build person descriptor
        if gender == 'male':
            person = "same man"
        elif gender == 'female':
            person = "same woman"
        else:
            person = "same person"

        body_desc = "same chubby stocky build, " if body_type == 'chubby' else ""

        # Build flux prompt — with or without product
        if product_name and product_placement:
            placement_desc = PRODUCT_PLACEMENTS.get(product_placement, PRODUCT_PLACEMENTS["in_hand"])
            flux_prompt = (
                f"{person} with exact same face, {body_desc}{shot_phrase}, "
                f"{placement_desc}, "
                "natural expression, looking at camera, indoors, warm soft lighting, "
                "preserve exact face identity, photorealistic"
            )
        else:
            flux_prompt = (
                f"{person} with exact same face, {body_desc}{shot_phrase}, "
                "natural expression, looking at camera, indoors, warm soft lighting, "
                "preserve exact face identity, photorealistic"
            )

        # All fallback scripts are ~44 words (safely fills 15 seconds) with Hook-Demo-Close structure
        # Use varied hooks to avoid repetition
        import random
        
        # Punctuation-driven hooks (em-dash forces a pause after hook beat)
        hooks = [
            "Real talk—",
            "Wait—",
            "Okay, I need to spill this—",
            "No way. I finally found it—",
            "Stop scrolling.",
            "I've been hiding this for weeks—",
            "This changed everything for me—",
        ]

        # Staccato closes (short phrases with commas — AI naturally slows down here)
        closes = [
            "Clean, effective, link in bio.",
            "Trust me. Grab yours now.",
            "No regrets. Link in bio.",
            "Seriously. You need this.",
            "Game changer. Link in bio.",
        ]

        if not user_script:
            if product_name:
                # Hook-Demo-Close structure with punctuation timing (38-40 words for 15s)
                hook = random.choice(hooks)
                close = random.choice(closes)

                if product_features:
                    script = f"{hook} this {product_name} has {product_features}, and it feels incredible on my skin. No irritation, no buildup, just results you can actually see and feel every day. {close}"
                else:
                    script = f"{hook} this {product_name} is everything I needed. Lightweight, effective, and it actually delivers on every single promise. I can't go back to anything else now. {close}"
            else:
                scripts = {
                    "full_body":  "Real talk— this outfit is everything. The fit is perfect, the fabric is so soft, and I feel unstoppable wearing it. No squeezing, no adjusting. Comfortable, stylish, done.",
                    "headshot":   "Wait— I need you to see this look. My skin is glowing, the lighting is perfect, and I feel like myself again. Effortless, natural, link in bio.",
                    "half_body":  "Okay— I've been holding out on you. This whole look came together so easily, and the confidence I feel? Unreal. Fresh, modern, link in bio.",
                }
                script = scripts[shot_type]
        else:
            script, _ = enforce_script_length(user_script)

        motion = self._generate_fallback_motion(script, product_name is not None)

        result = {
            "shot_type":           shot_type,
            "influencer_name":     influencer_name,
            "flux_prompt":         flux_prompt,
            "motion_prompt":       motion,
            "video_script":        script,
            "product_name":        product_name,
            "product_placement":   product_placement,
            "gender":              gender,
            "body_type":           body_type,
            "technical_reasoning": f"Fallback. Shot: {shot_type}. Body: {body_type}. Product: {product_name or 'none'}. Language: {script_language}. 15s enforced.",
        }
        # Output format must be valid JSON exactly like this:
        # {
        #   "flux_prompt": "description of outfit and background...",
        #   "motion_prompt": "70-80 words describing camera motion and human body language...",
        #   "video_script": "38-40 words of conversational script with strategic commas and em-dashes...",
        #   "voice_tone": "emotional delivery description (e.g., speaks warmly and energetically)",
        #   "duration": 15,
        #   "shot_type": "headshot, half_body, or full_body"
        # }
        return self._finalize(result, user_script, influencer_name)

    def cleanup(self):
        """No-op — Mistral is a stateless API call, nothing to unload."""
        emit_log(self.session_id, "info", "✓ Mistral client — no cleanup needed")
