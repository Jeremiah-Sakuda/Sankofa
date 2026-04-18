# Sankofa — Improvement Plan

## Current State

Sankofa is an 8,500-line multimodal AI heritage narrator deployed on Google Cloud Run. Four Gemini models, two ADK agents, SSE streaming, Firestore session persistence, trust classification, live voice conversation. Won Creative Storytellers category in Google's Gemini Live Agent Challenge (11,896 participants). Presented at Google Cloud Next 2026.

The product works. It ships a cinematic narrative experience that no competitor offers. What follows is the plan to turn it from a hackathon winner into a product people return to.

---

## Critical Problem: Retention

Sankofa's core retention risk is that heritage narration appears to be a single-use experience. A user generates one narrative and has no reason to come back.

The fix: reframe the product from a narrative generator to a heritage library. The first narrative is the hook. The library is the product. The family is the network.

Every improvement below serves one of three goals: making the first experience flawless, giving users a reason to return, or building the community layer that makes the knowledge base a moat.

---

## Phase 1 — Launch Readiness (Before Google Promo)

Google's social promotion of hackathon winners is the first real user acquisition event. The product must be polished, performant, and measurable before that traffic arrives.

### Infrastructure

- Set Cloud Run minimum instances to 1 (eliminate cold start delays)
- Set GCP budget alerts at $50 and $200 thresholds
- Convert ambient audio files from WAV to compressed MP3/OGG (reduce 10-25MB payload to 2-5MB)
- Add overall timeout to ADK streaming path (180s ceiling via asyncio.wait_for)
- Add TTS concurrency semaphore (cap at 3-4 simultaneous Gemini TTS calls)

### Security

- Add input sanitization for prompt injection on initial intake fields (family_name, region_of_origin, known_fragments are injected directly into Gemini prompts without filtering)
- Add session TTL (24-48 hours) with background cleanup task for in-memory store
- Add concurrent generation limit per IP (max 2 simultaneous narrative streams)

### Mobile Readiness

- Test full flow on iOS Safari and Chrome Android
- Verify audio autoplay works after intake "Begin" button interaction
- Profile GoldParticles and word-by-word reveal performance on low-end devices
- Add prefers-reduced-motion check — disable particles and reduce animation complexity when enabled
- Verify glassmorphism voice dock renders correctly on small screens

### Analytics (Minimal)

- Add Firestore analytics collection with events: narrative_start, narrative_complete, followup_used, live_voice_started, contribute_submitted
- Track region distribution across narratives
- Add password-protected /api/stats endpoint for aggregate counts
- Measure completion rate (how many narratives reach the final act vs. abandon mid-stream)

### GitHub & Public Presence

- Add screenshot or GIF of the narrative experience to the top of README
- Update hackathon section to reflect the win and Cloud Next presentation
- Add LICENSE file (MIT or Apache 2.0)
- Add live demo link if a persistent deployment is running

---

## Phase 2 — Retention Foundation (Weeks 3-8)

This phase builds the features that make users return. Without these, Sankofa is a novelty. With them, it's a product.

### Sample Narrative ("See an Example")

- Pre-generate one strong narrative (Kenyan heritage, 1940s era) with full watercolor imagery, audio, and trust tags
- Make it accessible from the landing page as "See an example" before the user commits to entering their own data
- Reduces friction for first-time visitors who arrive from Google's promo with zero context

### Post-Narrative Discovery Prompts

After the first narrative completes, surface exploration options instead of ending the experience:

- "Explore an earlier era" — pre-fill the intake with the same region, different time period
- "What was the music of this region?" — trigger a follow-up stream focused on cultural arts
- "Trace the migration" — prompt for a destination region and generate a narrative connecting origin to diaspora
- "Share with family" — generate a shareable link

These prompts teach the user that their heritage isn't one story. It's layers. Each prompt is a new narrative, a new reason to stay.

### Session Persistence & Saved Library

- Add user accounts (email + password or Google OAuth)
- Save completed narratives to user profile
- Allow users to return to past narratives, replay audio, review trust tags
- Display saved narratives as a visual library — each one represented by its first watercolor image, family name, region, and era
- This is the shift from "generator" to "library." The library is the product.

### Social Sharing (V1)

- Add "Share this story" button after narrative completion
- Generate shareable URL: sankofa.app/story/{session_id} (read-only public view, no follow-up or live voice)
- Generate OG image for link previews: first watercolor image with family name and region overlaid
- Add is_public flag to sessions — default false, set true when user explicitly shares

### Firestore Segment Write Fix

- Separate update_session_metadata() from append_segment()
- Session metadata updates the main Firestore document
- Segments append individually to the subcollection as generated, never bulk-deleted
- Reduces write operations from O(n) to O(1) per segment and eliminates data loss risk during mid-stream crashes

### In-Memory Store Eviction

- Add LRU eviction to InMemorySessionStore (cap at 100 sessions)
- Log warning when session count exceeds 50
- Treat in-memory as dev-only; production must use Firestore

---

## Phase 3 — Multi-Generational Narratives (Months 3-4)

This is the retention unlock. One narrative is a chapter. Multi-generational is the book.

### Connected Narratives

- Allow users to link narratives across eras and geographies
- User generates a narrative about Ghana in the 1800s, then a second about Jamaica in the 1920s, then a third about Brooklyn in the 1970s
- The system connects them: shared cultural threads, migration patterns, language evolution, naming traditions
- Each new generation references the previous narrative's context, creating continuity

### Family Heritage Timeline

- Visual timeline in the user's library showing their narratives arranged chronologically
- Each node is a narrative — click to re-enter that story
- Gaps in the timeline prompt: "What happened between 1890 and 1940? Ask the griot."
- The timeline itself becomes a reason to generate more narratives — users see the gaps and want to fill them

### Family Collaboration

- Allow users to invite family members to a shared heritage library
- Family members can add their own narratives from different angles or eras
- A cousin who knows about the migration to America generates that chapter while you generated the origin chapter
- Shared library shows all family members' contributions as a collective heritage story
- Disagreements between family members' accounts become prompts: "Your cousin remembers it differently. Ask the griot to explore both versions."

---

## Phase 4 — Community Knowledge Base (Months 4-6)

### "Contribute a Memory" (V1)

- Button appears after narrative completion: "Do you know something the griot missed?"
- Minimal form: region (pre-filled), era (pre-filled), memory content (free text, max 5000 chars), source type (family oral history / academic / personal knowledge), optional email
- Submissions go to Firestore contributions collection with status pending
- Run through validate_followup_question (or equivalent safety check) before storage
- Rate limited to 3/hour per IP
- Confirmation message: "Thank you. The griot will remember."

### Contribution Review Pipeline

- Password-protected admin endpoint: GET /api/contributions?status=pending
- PATCH /api/contributions/{id} to approve, reject, or request clarification
- Approved contributions merge into the knowledge base
- Contributors receive email notification when their knowledge appears in a narrative (if email provided)

### Knowledge Base Migration

- Export Python dict knowledge base to Firestore documents
- One collection knowledge_base with documents keyed by region
- Loader reads from Firestore instead of importing Python modules
- Community contributions merge into these documents after review
- Enables dynamic knowledge base updates without code deployments

### Community Trust Tags

- Community-contributed knowledge gets tagged "Community" (distinct from Historical, Cultural, Reconstructed)
- Historian or practitioner verification upgrades "Community" to "Cultural" or "Historical"
- Users see the provenance of every piece of knowledge in their narrative
- Transparency extends from the AI's imagination to the community's contributions

---

## Phase 5 — Regional Communities (Months 6-9)

### Region Pages

- Public pages for each region with deep knowledge base coverage
- Show aggregate statistics: number of narratives generated, community contributions, coverage depth
- Display anonymized narrative excerpts (with user permission) as a collective portrait of that region's heritage
- "Ghana — Gold Coast" page shows that 400 people have explored this region, 23 community memories have been contributed, and the knowledge base covers 1750-1970 with decade-by-decade depth

### Contributor Recognition

- Contributors who submit verified knowledge appear (optionally, by name or anonymously) on the region page
- No follower counts, no likes, no social feed
- Recognition model: "This region's knowledge base includes contributions from 12 community members and 3 verified historians"
- The tone is archive, not social media

### Regional Knowledge Gaps

- Surface which regions and eras have sparse coverage
- Prompt community: "The griot's knowledge of Trinidad before 1800 is thin. Can you help?"
- Targeted contribution requests drive knowledge base depth where it's needed most

---

## Phase 6 — Platform Maturity (Months 9-12)

### Institutional Features

- Branded instances for museums and cultural organizations
- Custom knowledge bases scoped to institution's focus region
- Bulk narrative generation for exhibit kiosks
- Educator guides and curriculum integration materials
- Usage analytics dashboard for institutional administrators
- API access for integration into museum apps or educational platforms

### Heritage Tourism Integration

- Partner API for travel companies to embed Sankofa narratives in pre-trip experiences
- Destination-aware narratives: "You're traveling to Accra. Here's the heritage story of the region you'll visit."
- Post-trip follow-up: "Now that you've been there, ask the griot what you saw."

### Knowledge Graph (Long-term)

- Structured relationships between regions (trade routes, colonial connections, migration corridors)
- Enables automatic narrative threading: the griot can trace a family from Ghana to Jamaica to Brooklyn because the graph encodes that path
- Cross-regional narratives become possible without manual linking

### Model Portability

- Abstract Gemini-specific calls behind a provider interface
- Support Anthropic, OpenAI, or open-source models as fallbacks
- Reduce single-vendor dependency on Google infrastructure
- Enable self-hosted institutional deployments

---

## Technical Debt & Ongoing Maintenance

### Monitoring

- Add Gemini API health check to /api/health endpoint (verify model availability, not just FastAPI uptime)
- Add structured logging with request IDs for tracing narrative generation failures
- Set up alerting on error rate spikes and latency thresholds

### Performance

- Profile frontend bundle size — 228K of source with Motion, React 19, and Tailwind could produce a heavy initial load
- Lazy-load ambient audio per act instead of loading all five tracks at page mount
- Consider WebSocket for live voice instead of polling if latency becomes an issue

### Testing

- Add integration tests for the full narrative pipeline (intake → stream → segments → audio)
- Add frontend E2E tests (Playwright) for the critical path: landing → intake → griot intro → narrative display → follow-up
- Load test the streaming endpoint with 50 concurrent connections to identify breaking points before promo traffic arrives

### Content Safety

- Expand validate_followup_question to cover initial intake inputs
- Add output filtering on generated narratives (catch historically insensitive or factually dangerous content before it reaches the user)
- Develop a content policy document for community contributions
- Plan for moderation at scale if community features drive volume

---

## Success Metrics by Phase

### Phase 1 (Launch Readiness)
- Zero critical errors during Google promo window
- Mobile completion rate within 10% of desktop
- Sub-5s time to first meaningful content after griot intro

### Phase 2 (Retention Foundation)
- 10%+ of users generate a second narrative
- 5%+ of users save a narrative to their library
- 3%+ of completed narratives are shared via link

### Phase 3 (Multi-Generational)
- 15%+ of returning users generate connected narratives
- Average library size exceeds 2 narratives per active user
- Family collaboration feature adopted by 5%+ of users with accounts

### Phase 4 (Community)
- 100+ community contributions in first 3 months
- 20%+ of contributions pass review and enter knowledge base
- At least 3 regions see measurable knowledge base depth increase from community data

### Phase 5 (Regional Communities)
- 10+ region pages with active community engagement
- Institutional partnership conversations initiated with 5+ organizations

### Phase 6 (Platform Maturity)
- 2-3 institutional licenses signed
- 1+ heritage tourism partnership active
- Knowledge graph supports cross-regional narrative threading