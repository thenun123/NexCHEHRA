# NexCHEHRA - Technical Overview and Pipeline Guide

## What is the NexCHEHRA Pipeline?
The NexCHEHRA platform uses an advanced, multi-step AI pipeline to convert user ideas into final animated video influencers. The system is designed to handle multiple AI services, primarily powered by Mistral for high-speed inferencing.

The pipeline consists of three main phases:

### Phase 1: NexBrain™ (The Core Logic & Intelligence)
- **Purpose:** To generate the personality, scripts, and dialogue for the virtual influencer.
- **Technology Used:** Mistral APIs (e.g., Mistral Large).
- **Process:** The user inputs a basic prompt or idea. NexBrain uses Mistral's high-speed LLM capabilities to expand this prompt into a full, engaging script. It determines the tone, facial expressions needed, and the overall pacing of the speech.

### Phase 2: NexVision™ (Visual Persona Generation)
- **Purpose:** To create the visual appearance of the influencer.
- **Process:** Based on the persona details crafted by NexBrain, NexVision utilizes Flux Kontext Max image generation models to generate a high-quality, ultra-realistic portrait of the digital influencer. For product placement ads, it uses Flux Kontext Max Multi to composite product images naturally.
- **User Control:** Users can customize the aesthetics such as clothing, background, and lighting.

### Phase 3: NexMotion™ (Animation and Voice)
- **Purpose:** To bring the generated image to life with voice and movement.
- **Process:** 
  1. The script from NexBrain is converted into audio using Advanced Speech Synthesis or Voice Cloning (refer to the `VOICE_CLONING_IMPLEMENTATION.md` for specific details).
  2. The image from NexVision and the audio track are sent to the NexMotion engine.
  3. The engine uses lip-syncing and facial animation AI to match the influencer's mouth movements and facial expressions accurately to the audio track.
- **Output:** A lifelike MP4 video of the AI influencer delivering the script.

## Supported File Formats
- **Image Uploads:** JPG, JPEG, PNG, and WebP formats are accepted for both reference images and product images.
- **Maximum Upload Size:** 16 MB per file.
- **Video Output:** All generated videos are delivered in MP4 format.
- **Audio:** NexMotion generates synchronized audio directly — no separate audio file upload is needed.

## Supported Voice Languages
NexMotion supports native audio generation in the following languages:
- **English (US)** — Full native support
- **English (UK)** — Full native support
- **Chinese (中文)** — Full native support
- **Japanese (日本語)** — Auto-translated to English internally
- **Korean (한국어)** — Auto-translated to English internally
- **Spanish (Español)** — Auto-translated to English internally

Users can also choose "No Voice" for silent video output.

## Shot Types
NexCHEHRA supports three shot types to control framing:

| Shot Type | Description | Best For | Aspect Ratio |
|-----------|-------------|----------|-------------|
| **Headshot** | Close-up, face and shoulders only | Product close-ups, testimonials | 1:1 |
| **Half Body** | Upper body, waist up, hands visible | Product demos, talking-head videos | 1:1 |
| **Full Body** | Head to toe, entire body visible | Fashion, full outfits, lifestyle | 9:16 (vertical) |

There is also an **Auto-Detect** option where the AI decides the best shot type based on your scene description.

## Common Architecture Questions

**Does the RAG Bot interfere with the Video Pipeline?**
Because NexCHEHRA uses Mistral for both the RAG assistant and the NexBrain pipeline, the system handles concurrent requests carefully. The RAG assistant uses models (e.g., Mistral Large) to ensure it does not exhaust the API rate limits needed by the heavier video generation background tasks. If a rate limit error (HTTP 429) occurs, the video pipeline will automatically retry the generation safely in the background.

**Who is this platform for?**
NexCHEHRA is built for content creators, marketers, educators, and enterprise clients who need to generate high volumes of video content without hiring human actors, buying expensive camera gear, or setting up studios.

**What technology stack does NexCHEHRA use?**
- **Backend:** Python Flask web framework
- **AI Models:** Mistral API, Flux Kontext Max (image generation), Kling V3 (video generation)
- **Database:** SQLite with SQLAlchemy ORM
- **Authentication:** Flask-Login with session-based auth
- **Frontend:** HTML, CSS, JavaScript with a custom glassmorphic dark-mode design system
