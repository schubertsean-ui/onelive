# Appendix A — AI attribution standards research report (verbatim agent output)

Provenance: single research-agent web fan-out, 2026-07-22, commissioned for
Session Contract #21 (docs/strategy/ONE_LIVE_AI_ATTRIBUTION_SYSTEM_v1.md).
Committed VERBATIM per the in-diff evidence rule (PR #47 evaluator r1; PR #18
r6–r7 precedent). The agent's own reliability caveat: every direct page fetch
was blocked by the sandbox egress proxy (CONNECT 403), so every claim is
SEARCH-SNIPPET grade — R-023 gates re-verification.

---

I have gathered comprehensive material across all six topics. Note on method: every claim below is labeled **SEARCH-SNIPPET** because the session's egress proxy returned policy 403s on every `WebFetch`/`curl` attempt (arxiv.org, ec.europa.eu, spec.c2pa.org, sidley.com, iptc.org, example.com all denied at the CONNECT tunnel). I could not open a single page directly; all facts derive from the search engine's result snippets. Treat everything as second-hand and re-verify the load-bearing dates/versions against the primary URLs listed at the end before relying on them.

# AI-Content Provenance & Attribution: State of the Art (as of 2026-07-22)

## 1. C2PA / Content Credentials

**Spec version & standardization** (SEARCH-SNIPPET)
- Current C2PA technical spec: **version 2.3, dated 2026-01-05** (PDF published ~Jan 8, 2026). A **2.4** spec tree is also live at spec.c2pa.org (`/specifications/2.4/`), suggesting 2.4 is the newest working draft/release. Prior cadence: 2.1 (2024-09-20), 2.2 (2025-05-01), 2.3 (2026-01).
- 2.1 added stricter tamper resistance and a formal conformance certification program.
- Standardized as **ISO/IEC 22144** ("Authenticity of information — Content Credentials"). Search snippets are inconsistent: one says C2PA 2.1 is "now an ISO standard (ISO/IEC 22144)"; another says **ISO/DIS 22144** was still at Draft International Standard stage mid-2025. Re-verify current ISO status.
- The consortium reported "5,000 members" (blog title) and a snippet claimed **"over 6,000 members and affiliates" as of Jan 2026**, including Google, Meta, OpenAI, Sony, Nikon, Leica.

**How manifests attribute AI involvement** (SEARCH-SNIPPET)
- AI declaration is carried in the **`c2pa.actions` assertion** via the **`digitalSourceType`** field, whose values come from the **IPTC "Digital Source Type" NewsCodes vocabulary** (`http://cv.iptc.org/newscodes/digitalsourcetype/...`):
  - **`trainedAlgorithmicMedia`** — asset created by generative AI tools (fully AI-generated). Paired with the `c2pa.created` action.
  - **`compositeWithTrainedAlgorithmicMedia`** (snippets also show the variant spelling `compositedWithTrainedAlgorithmicMedia`) — asset contains one or more elements created by generative AI (AI-assisted / partial). Paired with `c2pa.edited` or `c2pa.placed` actions, e.g. inpainting.
- IPTC published dedicated metadata guidance for AI-generated "synthetic media"; C2PA reuses IPTC's controlled vocabulary rather than defining its own.

**Soft binding / durable credentials** (SEARCH-SNIPPET)
- C2PA calls invisible **watermarking and content fingerprinting "soft bindings"**; a **Durable Content Credential** is one with one or more soft bindings enabling rediscovery of the manifest even after the embedded manifest is stripped.
- Mechanism: manifest stored in a cloud **manifest repository**; a **Soft Binding Resolution API** (Web API) lets clients (browsers/apps) re-fetch a stripped manifest via the watermark/fingerprint. Adobe's open-source "Durable Content Credentials" stack combines embedded metadata + invisible watermark (**TrustMark**) + image fingerprinting.
- 2.1 formally integrated **digital watermarks** (Digimarc, Imatag cited as vendors); soft bindings must use C2PA-approved watermarking/fingerprinting algorithms.

**Known limitations** (SEARCH-SNIPPET)
- Embedded JUMBF manifests are **destroyed when any non-C2PA-aware tool re-saves** the file. **WhatsApp, iMessage, and Facebook re-encode images on upload and silently drop credentials.**
- Watermarks alter pixel data and **can be cropped/removed**; paraphrase/re-encode defeats them. Durable CR only recovers provenance if a copy was stored in an online repository.
- Adoption gaps: **Nikon's certificate program was suspended after a signing vulnerability and, per an early-2026 snippet, had not been restored.** World Privacy Forum published a critical privacy/identity/trust review of C2PA.

**Does C2PA apply to TEXT / structured data?** (SEARCH-SNIPPET) — **Yes, as of 2.3.**
- **Section A.7/A.8/A.9 of C2PA 2.3** define embedding manifests into **unstructured text** (articles, social posts) using **Unicode Variation Selectors** (visually non-rendering code points; a data-hash assertion is required), **structured text** (comment / front-matter "ASCII Armour" blocks), and **HTML** (`<script>`/`<link>`). A reference implementation exists (`encypherai/c2pa-text`). Unicode also has an active proposal (L2/26-042) on embedded metadata in plain text.
- Historically C2PA was media-only (image/video/audio/PDF); **text support is new (2026) and not yet widely deployed.** No evidence C2PA models arbitrary structured/event data schemas — text support is about embedding a manifest inside text payloads, not attesting extracted fields.

**Adoption highlights 2025-2026** (SEARCH-SNIPPET — several claims from secondary blogs; verify each)
- **OpenAI**: signs Sora 2 video, DALL·E 3 and ChatGPT image generations with Content Credentials + invisible SynthID-style watermark.
- **Google**: Content Credentials + SynthID across Imagen 4, Veo 3, Lyria 2; "Trusted Images"/"About this image" on Pixel/Android; **Pixel 10 (Aug 2025) signs every photo with C2PA at capture** (claimed "first consumer phone" to do so).
- **Cameras**: Sony, Nikon, Canon, Leica, Fujifilm, Panasonic have C2PA-capable models; Leica SL3-S (Jan 2025) an early mover; Sony PXW-Z300 (IBC 2025) first native-C2PA camcorder. Samsung Galaxy S25 supports C2PA only for AI-edited images.
- **Platforms**: TikTok, LinkedIn adopted Content Credentials in 2025; Pinterest, Snap, Reddit following. **TikTok claimed >1.3 billion videos labeled with AI provenance.** Meta uses C2PA + IPTC metadata to drive its labels.
- **Government**: U.S. **NSA guidance (Jan 2025)** recommended federal adoption of Content Credentials for multimedia integrity.

## 2. EU AI Act Article 50 (transparency)

**Applicability date: 2 August 2026 — CONFIRMED by multiple SEARCH-SNIPPETs** (not page-verified).
- Regulation (EU) 2024/1689 entered into force 1 Aug 2024; Article 50 transparency obligations **become enforceable 2 August 2026**.
- **Grace period:** for AI systems **placed on the market before 2 Aug 2026**, the **marking/detection obligation for AI-generated content** applies only **from 2 December 2026**.

**Substantive obligations** (SEARCH-SNIPPET)
- **(a) AI systems interacting with users (chatbots):** providers must design them so affected persons are informed they are interacting with an AI, unless obvious.
- **(b) Synthetic content marking:** providers of generative AI must ensure outputs are **marked in a machine-readable format and detectable as artificially generated or manipulated** — this is the provision that maps to C2PA/watermarking. Applies to audio, image, video, and **text**.
- **(c) Deployer disclosure for text on matters of public interest:** deployers who publish **AI-generated/manipulated text to inform the public on matters of public interest** must disclose it is artificially generated — with a widely-cited carve-out: **not required where the content underwent human review / editorial responsibility** (a human-in-the-loop exemption). This carve-out is directly relevant to your human-gated workflow; re-verify exact wording against the Commission FAQ.
- **(d) Deepfakes:** deployers must disclose that image/audio/video content is a deepfake (with artistic/satirical adaptations getting lighter transparency).

**Code of Practice / guidance status mid-2026** (SEARCH-SNIPPET)
- The **European Commission released draft Guidelines on Article 50 transparency obligations** (for providers and deployers) — a draft-guidelines article and the Commission's "Guidelines on transparency obligations" library entry both appear.
- The Commission released a **first draft of a Code of Practice on marking and labelling AI-generated content** in **December 2025** for public consultation, with **feedback due 23 January 2026.** As of mid-2026 this is not yet final. (TechPolicy.Press published an explainer on the "AI Transparency Code of Practice.")

## 3. News / publishing AI-disclosure practice

**Newsroom policies** (SEARCH-SNIPPET)
- **AP (Aug 2023 guidelines):** generative AI **"cannot be used to create publishable content and images"**; AI output is "unvetted source material" subject to AP sourcing standards. AP has an OpenAI licensing deal but bars AI-authored publishable copy.
- **Reuters:** commits to making "use of data and AI in our products and services understandable."
- **The Guardian (editorial code, updated ~late 2025/2026):** AI is an assistant, not author; the journalist is always accountable; **byline work must be human-authored**; AI use disclosed to readers; **AI-generated content must be labeled clearly and understandably**; active human oversight essential.
- A **JournalistsResource study compared AI policies at 52 news organizations** — useful survey source. NYT-specific policy did not surface cleanly in snippets (NYT permits limited AI-assist tools with restrictions; verify separately).

**Trust Project / IPTC** (SEARCH-SNIPPET)
- **The Trust Project's "8 Trust Indicators"** (Best Practices, Author expertise, Type of work labeling, Citations/References, Methods, Locally Sourced, Diverse Voices, Actionable Feedback) are the "first global transparency standard" for who/what is behind a story; used by Google, Facebook, Bing. The project has **added AI-transparency attributes** to the indicators and is working on distinguishing generative AI vs. non-generative AI use.
- **IPTC** provides the machine-readable backbone — the **Digital Source Type NewsCodes** vocabulary that C2PA and Meta consume — plus published guidance for synthetic media metadata.

**Reader-trust effects — the "transparency dilemma" (academic, 2023-2026)** (SEARCH-SNIPPET; strong convergent finding)
- **Core finding: labeling content as AI-generated tends to REDUCE trust/perceived accuracy, even when the content is not actually less accurate.** Audiences apply an "automation heuristic" / defensive skepticism.
- Key sources: **Toff & Simon, "'Or They Could Just Not Use It?': The Dilemma of AI Disclosure for Audience Trust in News,"** *The International Journal of Press/Politics*, 2025 (SAGE) — audiences rate AI-labeled news as less trustworthy though not less accurate/fair.
- **"AI labeling reduces the perceived accuracy of online content but has limited broader effects"** (arXiv 2506.16202; also in *Computers in Human Behavior* / ScienceDirect 2026): labeling lowers perceived accuracy and reduces expressed policy interest, but has limited spillover on policy support or misinformation concern.
- **"Full Disclosure, Less Trust?"** (ACM FAccT 2026): **more-detailed disclosure of AI use reduced trust further** — additional context backfired ("transparency dilemma").
- **"The Transparency Dilemma: An Experiment on How AI Disclosures Affect..."** (AAAI/AIES).
- Related: arXiv 2409.03500 (quality perceptions of AI-generated vs AI-assisted news); arXiv 2606.11116 ("Designed by Journalists, but Is It for Readers?"); arXiv 2601.11072 (visualizing human-AI collaboration disclosures).
- Consumer-demand counterpoint: an eMarketer/survey figure — **~61% of US consumers think publications should always disclose AI-created content** — i.e., audiences *demand* disclosure even though disclosure depresses trust (the crux of the dilemma).

## 4. Text watermarking

**Google SynthID-Text** (SEARCH-SNIPPET)
- **First large-scale production LLM text watermark**; published in **Nature (2024)** — "Scalable watermarking for identifying large language model outputs" (*Nature* s41586-024-08025-4). Uses **generative/"Tournament" sampling** that biases next-token selection to leave a detectable statistical signal, reportedly **no measurable quality loss** across ~20M live Gemini responses and human side-by-side ratings.
- **Deployed in Gemini app/web**; **open-sourced Oct 2024** (google-deepmind/synthid-text; integrated into Hugging Face Transformers).
- **Robustness — weak, especially short text:** vulnerable to **paraphrasing, back-translation (e.g., Google Translate), summarization by another model, and edits**; ETH SRI Lab and others showed the watermark is **detectable via black-box queries** and **easier to "scrub" than other SOTA schemes** for naive adversaries; a **"layer inflation" attack** breaks it (arXiv 2603.03410, 2508.20228). Detection weakens sharply as text length drops.

**OpenAI** (SEARCH-SNIPPET)
- Built a text-watermarking method (perturbs token selection) reported **~99.9% effective given enough text** — but **has withheld public release** citing circumvention risk, disproportionate impact on **non-English speakers**, and a user survey finding **~30% would stop using ChatGPT if watermarked while competitors weren't.** OpenAI's earlier public **"AI Text Classifier" was withdrawn (2023) for low accuracy.**

**Viability for short-form text** (SEARCH-SNIPPET)
- Consensus across sources: text watermarking is **not robust for short text.** Detection reliability depends on sufficient token count; short/edited/paraphrased passages evade detection. Removal is trivial (translate/rewrite). No watermark is cross-vendor (a GPT watermark can't detect Gemini/Claude output and vice versa). For short descriptive copy in an events app, watermarking is widely regarded as **not a viable standalone attribution mechanism.**

## 5. Provenance UX patterns ("discreet" disclosure)

**Content Credentials "CR" icon** (SEARCH-SNIPPET)
- Official **"icon of transparency": a minimalist pin bearing the letters "CR."** Design criteria: convey trust, **signal that more info is available**, universally understood, flexible across backgrounds. Interaction: **hover/click reveals a "digital nutrition label" / "list of ingredients"** side-panel showing creator, capture time/place, tools used, whether generative AI was involved, and edit history.
- **LinkedIn** shows a clickable CR badge on Content-Credentialed images → provenance summary. Browser extensions (Digimarc, "C2PA Content Credentials" Chrome extension) surface it where platforms don't.

**Google "About this image" / "AI Info"** (SEARCH-SNIPPET)
- Provenance is placed **at the bottom of the "Details" section** of Google Photos / behind an **"About this image"** affordance in Search, Chrome, Gemini (rolled out 2025, expanded Nov 2025). Example string: **"Credit: Edited with Google AI, Digital source type: Edited using Generative AI."** Google detects SynthID + C2PA. Google also began (Jul 2026) disclosing which **ads** are made with AI.

**Meta "AI Info" label** (SEARCH-SNIPPET)
- Originally **"Made with AI" (May 2024)**; after photographers complained real photos with minor AI edits were mislabeled, **renamed to "AI Info" (Jul 2024)** across Meta apps — deliberately softer/less absolute wording. Underlying detection unchanged; driven by **C2PA + IPTC metadata.** The label is **tap-to-expand** (low-prominence chip → details on tap).

**Best-practice pattern (synthesized from snippets):** a **small, persistent, non-intrusive glyph/chip** (CR pin, "AI Info") that is **progressively disclosed** — minimal at rest, full "nutrition label" of model/tools/edits/source on hover/tap. Word choice trends toward **neutral/informational ("AI Info," "About this image")** rather than absolute verdicts ("Made with AI"), partly because binary labels misfire and (per §3) depress trust. Note "AI Disclosure Labels Risk Becoming Digital Background Noise" (TechPolicy.Press) — habituation/banner-blindness is a documented failure mode of ubiquitous low-mindshare labels.

## 6. Attribution records for agentic AI work (model, prompt, approver, sources)

**Model / system cards** (SEARCH-SNIPPET)
- **Model Cards** (Mitchell et al.) document training data sources, evaluation, intended use — audience-facing model documentation. **AI System Cards** (arXiv 2509.20394) extend this to end-to-end systems. Emerging: **model cards for edge/agentic AI** (arXiv 2511.21661); **Policy Cards** — machine-readable runtime governance for autonomous agents (arXiv 2510.24383).

**AI Bill of Materials (AIBOM)** (SEARCH-SNIPPET)
- Extends SBOM discipline to AI: enumerates **models, datasets, training lineage.** Two practical formats:
  - **CycloneDX ML-BOM (OWASP), v1.7** — CI/CD-oriented ("MLBOM").
  - **SPDX 3.0 AI Profile** — ISO/IEC 5962 lineage, procurement/regulatory weight, aligns to NIST AI RMF.
- **CISA-facilitated "SBOM for AI" Tiger Team** produced use cases; **Linux Foundation, ISO/IEC 42001, OWASP, NIST, COSO** all published AIBOM-adjacent guidance. Research: **AIBoMGen** (arXiv 2601.05703) generates AIBOMs during training; **AIRS Framework** (arXiv 2511.12668) ties AIBOM artifacts to MITRE ATLAS threat categories. A **"Model Bill of Materials"** framing targets AI Act auditors.

**NIST** (SEARCH-SNIPPET)
- **NIST AI RMF** (AI 100-1, Jan 2023) — voluntary; functions Govern/Map/Measure/Manage. **Content provenance is an explicitly called-out consideration.**
- **NIST AI 600-1 — Generative AI Profile** (companion to the RMF) is the GenAI-specific profile; addresses provenance/data-tracking and synthetic-content risks.

**W3C PROV-O** (SEARCH-SNIPPET)
- **W3C PROV family (2013):** PROV-DM (data model), **PROV-O (ontology)**, serializations. Models provenance as a graph of **Entities, Activities, Agents.** In AI pipelines it links a decision/output to the model artifacts and activities that produced it — enabling the traceability audits referenced by the EU AI Act and NIST AI RMF. This is the standard best-suited to your "which model / prompt version / human approver / source documents" record: a PROV-O graph where the AI model and the human approver are `prov:Agent`s, extraction/generation are `prov:Activity`s, and source docs + output copy are `prov:Entity`s with `wasDerivedFrom` / `wasAttributedTo` / `wasAssociatedWith` links.

**Dataset provenance** (SEARCH-SNIPPET)
- **MLCommons Croissant** standardizes ML dataset description (relevant if source event data becomes training/reference data).

**Gap:** No snippet surfaced a single dominant standard specifically for **agentic run-time attribution records** (model+prompt-version+human-gate+source-doc lineage per output). The current practice stitches together: **PROV-O** (lineage graph) + **model/system cards** (the model artifact) + **AIBOM** (dependency inventory) + **C2PA digitalSourceType** (the AI-involvement claim on the emitted asset) + **NIST AI RMF / AI 600-1** (governance framing). "Policy Cards" and "AI System Cards" are the closest emerging attempts at per-agent machine-readable records but are research-stage, not adopted standards.

## Cross-cutting facts relevant to your event-app design (facts only)
- C2PA's AI-attribution primitive (`digitalSourceType = trainedAlgorithmicMedia` / `compositeWithTrainedAlgorithmicMedia`) is defined by **IPTC** and reused across C2PA, Google, and Meta labels — it is the de-facto interoperable vocabulary for "AI-generated" vs "AI-assisted."
- **EU AI Act Art. 50 marking obligation covers text**, and the **deployer disclosure duty for public-interest text has a human-editorial-review carve-out** — directly germane to a human-gated pipeline (verify exact wording).
- **Text watermarking is not robust for short copy** (§4); **provenance metadata/records (C2PA-text, PROV-O, AIBOM) — not watermarks — are the viable path for short descriptive text.**
- **Empirical trust research (§3) consistently finds AI labels lower trust**, while surveys show audiences demand disclosure — the "transparency dilemma" — and over-detailed disclosure worsens the trust hit.

## Source list (all accessed via search 2026-07-22; none page-verified due to egress 403s)

C2PA / Content Credentials
- C2PA Technical Spec 2.3 (2026-01-05): https://spec.c2pa.org/specifications/specifications/2.3/specs/_attachments/C2PA_Specification.pdf
- C2PA Spec 2.4 tree: https://spec.c2pa.org/specifications/specifications/2.4/specs/C2PA_Specification.html
- C2PA AI/ML guidance 2.4: https://spec.c2pa.org/specifications/specifications/2.4/ai-ml/ai_ml.html
- CAI assertions/actions docs: https://opensource.contentauthenticity.org/docs/manifest/writing/assertions-actions/
- Durable Content Credentials: https://opensource.contentauthenticity.org/docs/durable-cr/
- C2PA Soft Binding API: https://spec.c2pa.org/specifications/specifications/2.2/softbinding/Decoupled.html
- Wikipedia, Content Credentials: https://en.wikipedia.org/wiki/Content_Credentials
- ISO/DIS 22144 (ASIS&T): https://www.asist.org/2025/03/19/iso-22144-authenticity-information-standards/
- IPTC synthetic-media metadata guidance: https://iptc.org/news/iptc-publishes-metadata-guidance-for-ai-generated-synthetic-media/
- Digimarc on C2PA 2.1 watermarks: https://www.digimarc.com/blog/c2pa-21-strengthening-content-credentials-digital-watermarks
- World Privacy Forum C2PA review: https://worldprivacyforum.org/posts/privacy-identity-and-trust-in-c2pa/
- C2PA-text reference impl: https://github.com/encypherai/c2pa-text
- CAI 5,000 members blog: https://contentauthenticity.org/blog/5000-members-building-momentum-for-a-more-trustworthy-digital-world

EU AI Act Art. 50
- Commission FAQ (Art. 50 transparency): https://digital-strategy.ec.europa.eu/en/faqs/transparency-obligations-under-article-50-ai-act
- Commission Guidelines on transparency obligations: https://digital-strategy.ec.europa.eu/en/library/guidelines-transparency-obligations-providers-and-deployers-ai-systems
- artificialintelligenceact.eu Art. 50 guide: https://artificialintelligenceact.eu/transparency-rules-article-50/
- Sidley Data Matters (2026-06-24): https://datamatters.sidley.com/2026/06/24/eu-ai-act-transparency-obligations-preparing-for-compliance-by-2-august-2026/
- Technology.org (2026-07-17): https://www.technology.org/2026/07/17/eu-ai-act-what-actually-applies-on-2-august-2026/
- TechPolicy.Press, AI Transparency Code of Practice: https://www.techpolicy.press/the-eus-ai-transparency-code-of-practice-explained/

News/publishing disclosure & trust research
- JournalistsResource (52 newsrooms): https://journalistsresource.org/home/generative-ai-policies-newsrooms/
- Poynter on AP AI guidance: https://www.poynter.org/ethics-trust/2023/new-ap-stylebook-guidelines-artificial-intelligence-chatgpt/
- Nieman Lab, AP clarifies GenAI standards: https://www.niemanlab.org/2023/08/not-a-replacement-of-journalists-in-any-way-ap-clarifies-standards-around-generative-ai/
- Guardian GenAI policy summary: https://www.stuartbruce.biz/2026/03/the-guardians-generative-ai-and-journalism-policy/
- The Trust Project, indicators: https://thetrustproject.org/trust-indicators/
- Toff & Simon, dilemma of AI disclosure (IJPP 2025): https://journals.sagepub.com/doi/10.1177/19401612241308697
- AI labeling reduces perceived accuracy (arXiv 2506.16202): https://arxiv.org/pdf/2506.16202
- Full Disclosure, Less Trust? (ACM FAccT 2026): https://dl.acm.org/doi/10.1145/3805689.3812386
- Transparency Dilemma (AAAI/AIES): https://ojs.aaai.org/index.php/AIES/article/download/36671/38809/40746
- eMarketer, consumers want AI transparency: https://www.emarketer.com/content/consumers-want-ai-transparency-media-publications

Text watermarking
- SynthID-Text, Nature 2024: https://www.nature.com/articles/s41586-024-08025-4
- google-deepmind/synthid-text: https://github.com/google-deepmind/synthid-text
- MIT Tech Review, open-sourcing: https://www.technologyreview.com/2024/10/23/1106105/google-deepmind-is-making-its-ai-text-watermark-open-source/
- ETH SRI Lab, probing SynthID-Text: https://www.sri.inf.ethz.ch/blog/probingsynthid
- Robustness assessment (arXiv 2508.20228): https://arxiv.org/abs/2508.20228
- SynthID theoretical analysis (arXiv 2603.03410): https://arxiv.org/html/2603.03410v2
- OpenAI withholding watermark (Thurrott): https://www.thurrott.com/a-i/306664/openai-built-text-watermarking-solution-to-detect-ai-generated-content-but-may-not-release-it

Provenance UX
- Official Content Credentials icon: https://contentcredentials.org/introducing-official-content-credentials-icon/ ; https://c2pa.org/introducing-official-content-credentials-icon/
- Content Credentials verify site: https://contentcredentials.org/
- TechCrunch, Meta "AI Info" rename: https://techcrunch.com/2024/07/01/meta-changes-its-label-from-made-with-ai-to-ai-info-to-indicate-use-of-ai-in-photos/
- Techlicious, Google Search/Chrome/Gemini AI-image detection: https://www.techlicious.com/blog/google-search-chrome-gemini-detect-si-generated-images/
- TechPolicy.Press, labels as background noise: https://www.techpolicy.press/ai-disclosure-labels-risk-becoming-digital-background-noise/

Attribution records / AIBOM / provenance standards
- NIST AI 600-1 GenAI Profile: https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf
- CycloneDX ML-BOM: https://cyclonedx.org/capabilities/mlbom/
- SPDX AI Working Group publications: https://spdxai.github.io/publications/
- Palo Alto Networks, AI-BOM: https://www.paloaltonetworks.com/cyberpedia/what-is-an-ai-bom
- AIBoMGen (arXiv 2601.05703): https://arxiv.org/pdf/2601.05703
- AIRS Framework (arXiv 2511.12668): https://arxiv.org/html/2511.12668v1
- AI System Cards (arXiv 2509.20394): https://arxiv.org/pdf/2509.20394
- Policy Cards (arXiv 2510.24383): https://arxiv.org/pdf/2510.24383
- Claru, data provenance / W3C PROV: https://claru.ai/glossary/data-provenance

**Reliability caveat (important):** Because every direct page fetch was blocked by this session's egress policy, I could not independently confirm any figure against its primary source — notably the C2PA membership counts, the "Pixel 10 signs every photo," TikTok's "1.3 billion," ISO/IEC 22144's exact current stage, and the precise statutory text of Article 50's human-review carve-out. These are the highest-value items to re-verify by opening the primary URLs (Commission FAQ, spec.c2pa.org, Nature) from an unrestricted network before you rely on them.
