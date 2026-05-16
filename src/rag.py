"""
RAG Legal Parser.

Builds a local ChromaDB vector index over regulatory summaries (EU AI Act,
NIST AI RMF, ISO 42001) using sentence-transformers all-MiniLM-L6-v2.
Falls back to embedded markdown summaries when web sources are unavailable.
"""
import requests
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

CHROMA_PATH = "./chroma_db"
COLLECTION_NAME = "regulatory_docs"
EMBED_MODEL = "all-MiniLM-L6-v2"

# ---------------------------------------------------------------------------
# Embedded regulatory fallback content (authoritative condensed summaries)
# ---------------------------------------------------------------------------
REGULATORY_CORPUS: dict[str, str] = {
    "eu_ai_act_risk_classification": """
EU AI Act — Risk Classification (Articles 5–7)
PROHIBITED AI (Article 5): Social scoring by governments. Real-time biometric
surveillance in public. Subliminal manipulation. Exploitation of vulnerable groups.
HIGH-RISK AI (Article 6 + Annex III): AI in critical infrastructure, education,
employment, essential services, law enforcement, migration, justice, and democratic
processes. Must undergo conformity assessment before market placement.
LIMITED RISK: Chatbots must disclose AI identity. Deepfakes must be labelled.
MINIMAL RISK: All other AI. No mandatory requirements but voluntary codes encouraged.
""",
    "eu_ai_act_obligations": """
EU AI Act — High-Risk AI Obligations (Articles 9–15)
Article 9 — Risk Management System: Continuous iterative process throughout lifecycle.
Identify, analyse, estimate, and evaluate risks. Adopt risk mitigation measures.
Article 10 — Data Governance: Training/validation/testing data must be relevant,
representative, free of errors, and complete. Address possible biases.
Article 11 — Technical Documentation: Detailed before market placement. Enables
competent authority assessment of conformity. Annex IV specifies content.
Article 12 — Record-Keeping: Automatic logging of events during high-risk AI lifetime.
Logs retained minimum 6 months. Enable traceability and post-market monitoring.
Article 13 — Transparency: Instructions for use. Name and contact of provider.
Characteristics, capabilities, limitations. Performance on relevant groups.
Article 14 — Human Oversight: Effective oversight by natural persons. Ability to
understand capabilities/limitations. Monitor operation. Override or halt system.
Article 15 — Accuracy, Robustness, Cybersecurity: Appropriate accuracy levels.
Resilience to errors, faults, inconsistencies. Protection against adversarial attacks.
""",
    "eu_ai_act_governance": """
EU AI Act — Governance and Enforcement (Articles 56–94)
Article 56 — European AI Office: Oversees GPAI model regulation. Supports member states.
Article 63 — Market Surveillance: National authorities monitor compliance. Powers to
request documentation, conduct evaluations, order withdrawal of non-compliant AI.
Article 71 — Fines: Up to €35M or 7% global annual turnover for prohibited AI violations.
Up to €15M or 3% for high-risk AI violations. Up to €7.5M or 1.5% for false information.
Article 72 — Penalties for SMEs: Proportionate fines respecting SME interests.
GDPR ALIGNMENT: AI Act complements GDPR. DPIAs must consider AI Act requirements.
Data minimisation principles apply to AI training data governance.
""",
    "nist_ai_rmf_core": """
NIST AI Risk Management Framework (AI RMF 1.0) — Core Functions
GOVERN (GV): Establish policies, processes, and accountability for AI risk management.
GV-1: Policies, processes, and practices across AI risk management. Organizational
roles, responsibilities, and authorities. Risk tolerance articulated by leadership.
GV-4: AI risk is integrated into enterprise risk management. Board-level oversight.
GV-6: Policies enforce legal, regulatory, and contractual AI risk requirements.
MAP (MP): Identify and categorize AI risks and impacts.
MP-1: Context is established for AI risk assessment. Intended purpose documented.
MP-2: Scientific and technical knowledge used to identify potential AI risks.
MP-5: Likelihood and magnitude of each identified impact assessed and documented.
MEASURE (MS): Analyse, assess, and benchmark AI risks.
MS-1: Methods to measure AI risks in place. Evaluation sets used to test systems.
MS-2: AI system trustworthiness characteristics evaluated. Bias metrics computed.
MS-4: Measurement of AI risk extended to impacts on individuals and communities.
MANAGE (MG): Prioritize and address AI risks.
MG-1: Risks identified in Map and measured in Measure are prioritized for treatment.
MG-2: Treatment plans are monitored and documented. Residual risk assessed.
MG-4: Post-deployment AI system performance monitored. Incidents responded to.
""",
    "iso_42001_requirements": """
ISO/IEC 42001:2023 — AI Management System Requirements
Clause 4 — Context of Organization: Understand internal and external issues relevant
to AI. Identify interested parties and their requirements. Define AIMS scope.
Clause 5 — Leadership: Top management demonstrate commitment. Establish AI policy.
Assign roles and responsibilities for AI management system.
Clause 6 — Planning: Address risks and opportunities. Set AI objectives.
Conduct AI impact assessment. Plan changes to the management system.
Clause 7 — Support: Provide resources, competence, awareness, communication.
Documented information required: AI policy, risk assessments, objectives, records.
Clause 8 — Operation: Implement AI risk assessment. Control AI system development.
Manage suppliers and third-party AI. Incident preparation and response.
Clause 9 — Performance Evaluation: Monitor, measure, analyse, evaluate AI management.
Internal audits. Management review of AIMS performance.
Clause 10 — Improvement: Act on nonconformities. Corrective action. Continual improvement.
Annex A — Controls: 38 controls across 9 domains including data governance,
system lifecycle, transparency, human oversight, and incident management.
""",
    "gdpr_ai_intersection": """
GDPR and AI Systems — Key Intersection Points
Article 5 GDPR — Data Principles for AI Training: Lawfulness, fairness, transparency.
Purpose limitation: AI models trained for specific purposes. Data minimisation.
Accuracy: Training data must be accurate. Storage limitation enforced.
Article 13/14 GDPR — Transparency in Automated Processing: Inform data subjects when
their data is used to train AI. Explain logic of automated decisions affecting them.
Article 22 GDPR — Automated Decision-Making: Right not to be subject to solely
automated decisions with significant effects. Human review must be available.
Profiling restrictions apply to AI-powered recommendation and scoring systems.
Article 35 GDPR — Data Protection Impact Assessment: Required when AI processes
sensitive data at scale or makes systematic automated decisions about individuals.
DPIA must be completed before deployment of high-risk AI using personal data.
Recital 71 — Profiling Safeguards: Right to explanation for automated decisions.
Suitable measures to safeguard data subject rights and legitimate interests.
"""
}

# ---------------------------------------------------------------------------
# Optional: attempt live scrape of regulatory summary pages
# ---------------------------------------------------------------------------
SCRAPE_SOURCES: dict[str, str] = {
    # Add verified regulatory summary URLs here as they become available
}


def _try_scrape(url: str) -> str | None:
    try:
        resp = requests.get(
            url,
            timeout=8,
            headers={"User-Agent": "AI-Governance-Toolkit/2026.1 (compliance research)"}
        )
        if resp.status_code == 200 and len(resp.text) > 200:
            return resp.text[:4000]
    except Exception:
        pass
    return None


def build_index() -> chromadb.Collection:
    """Build or load the ChromaDB vector index."""
    ef = SentenceTransformerEmbeddingFunction(model_name=EMBED_MODEL)
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"}
    )

    if collection.count() > 0:
        return collection

    docs: list[str] = []
    ids: list[str] = []

    # Load embedded regulatory corpus
    for doc_id, text in REGULATORY_CORPUS.items():
        docs.append(text.strip())
        ids.append(doc_id)

    # Attempt live scrapes and append if successful
    for doc_id, url in SCRAPE_SOURCES.items():
        scraped = _try_scrape(url)
        if scraped and doc_id not in ids:
            docs.append(scraped)
            ids.append(doc_id)

    collection.add(documents=docs, ids=ids)
    return collection


def query_policy(question: str, n_results: int = 2) -> str:
    """
    Query the regulatory vector index with a natural language question.
    Returns relevant regulatory passages as a formatted string.
    """
    ef = SentenceTransformerEmbeddingFunction(model_name=EMBED_MODEL)
    client = chromadb.PersistentClient(path=CHROMA_PATH)

    try:
        collection = client.get_collection(name=COLLECTION_NAME, embedding_function=ef)
        if collection.count() == 0:
            raise ValueError("Empty collection")
    except Exception:
        collection = build_index()

    results = collection.query(query_texts=[question], n_results=min(n_results, collection.count()))

    if not results["documents"] or not results["documents"][0]:
        return "No relevant regulatory guidance found in the index."

    passages = results["documents"][0]
    sources = results["ids"][0]

    output_parts = []
    for source_id, passage in zip(sources, passages):
        label = source_id.replace("_", " ").upper()
        output_parts.append(f"**[{label}]**\n{passage.strip()}")

    return "\n\n---\n\n".join(output_parts)
