from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from typing import Dict, Any
from io import BytesIO
import json
import asyncio
import ast
import re
from concurrent.futures import ThreadPoolExecutor
import fitz  # PyMuPDF
from PIL import Image
import pytesseract

from backend.services.contract_intelligence import answer_contract_question
from backend.llm_config import (
    AI_PROVIDER,
    OPENAI_BASE_URL,
    OPENAI_MODEL,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    OLLAMA_NUM_CTX,
    OLLAMA_TEMPERATURE,
    OLLAMA_TIMEOUT,
    selected_api_key,
)

executor = ThreadPoolExecutor()


model_name = OLLAMA_MODEL if AI_PROVIDER == "ollama" else OPENAI_MODEL
base_url = OLLAMA_BASE_URL if AI_PROVIDER == "ollama" else (OPENAI_BASE_URL or None)

if not model_name:
    print("WARNING: selected LLM model is not set. GenAI features may be disabled.")

llm_kwargs = {
    "model": model_name,
    "base_url": base_url,
    "api_key": selected_api_key(),
    "temperature": OLLAMA_TEMPERATURE if AI_PROVIDER == "ollama" else 0.2,
}
if AI_PROVIDER == "ollama":
    llm_kwargs["request_timeout"] = OLLAMA_TIMEOUT
    llm_kwargs["model_kwargs"] = {"num_ctx": OLLAMA_NUM_CTX}

llm_model = ChatOpenAI(**llm_kwargs)

analysis_system_prompt = """
You are a professional contract clause extraction engine.

You are given this contract text:
{contract_text}

Response language requirement: {response_language}.

Extract clauses into a flat JSON object using ONLY these clause keys and meanings:
- parties: Names, roles, and identifying information of the parties entering the agreement.
- effective_date: The date the contract starts or becomes legally binding.
- scope_of_work: The specific services, deliverables, or job responsibilities defined in the contract.
- compensation: Salary, fees, payment amounts, currency, frequency, and any bonuses or commissions.
- working_hours: Hours per day/week, shift arrangements, overtime policy.
- leave_policy: Annual leave, sick leave, public holidays, and unpaid leave entitlements.
- probation: Trial/probation period duration and conditions.
- termination: Notice periods, grounds for termination, resignation process, end-of-service entitlements.
- confidentiality: Non-disclosure obligations, definition of confidential information, duration.
- non_compete: Restrictions on working for competitors after the contract ends.
- intellectual_property: Ownership of work produced during the engagement.
- governing_law: Which country or jurisdiction's law governs this contract.
- dispute_resolution: How disputes are handled — courts, arbitration, mediation.
- force_majeure: Unforeseeable events that excuse a party from performance.
- limitation_of_liability: Caps on damages or excluded liability types.
- indemnification: Who bears costs if a third party makes a claim.
- payment_terms: Invoice schedules, due dates, late payment penalties.
- renewal: Automatic or manual renewal terms and conditions.
- miscellaneous: Any other important clauses not covered above.

For each clause key, include ONLY content that directly and specifically belongs
to that clause type. Do not put content from one clause type into another.
If a clause is not present in the contract, omit that key entirely from the JSON.
Do not invent or summarize — extract the actual contract text verbatim for each clause.

Output requirements:
- Return a valid JSON object only.
- Every key must be one of the clause names above.
- Every value must be the exact extracted contract text for that clause.
- No extra keys, no nested objects, no arrays.

Before returning the JSON, review each key-value pair and ask yourself:
does this content actually describe what this clause type means?
If the answer is no, move the content to the correct clause key or remove it.
"""

prompt1 = PromptTemplate.from_template(analysis_system_prompt)


evaluation_system_prompt = """ 
You are a professional and intelligent contract health assessor, well known for your ability to assess the health of contracts precisely and efficiently, and for providing the correct reasoning behind the assessment.

Your responsibilities include:
1. Carefully reading key legal contract clauses provided in JSON format.
2. Analyzing each clause to assess its clarity, completeness, fairness, and risk mitigation based on best legal and business practices.
3. Considering whether the contract as a whole is approved (healthy) or not, and if it protects both parties adequately and manages key risks.
4. Providing clear, professional, and precise reasoning behind your assessment.
5. Returning a structured JSON object with:
- `approved`: A boolean indicating whether the contract overall should be approved (true if healthy, false if there are critical issues).
- `reasoning`: A concise, professional explanation of why the contract is approved or not, mentioning key strengths and weaknesses.
- `missing_critical_clauses`: Array of missing critical clause names.
- `issues`: Array of precise contract-specific problems.
- `required_changes`: Array of actionable, contract-specific changes needed for approval.
- `risk_level`: One of `low`, `medium`, `high`.

---

You are given the following key legal contract clauses (in JSON format):  

{contract_json}

---

Response language requirement: {response_language}.

Your task is to read the clauses carefully, analyze them and assess the overall health of the contract along with a precise and professional reasoning behind your assessment to return a structured JSON object containing the approval state and the reasoning behind it.

Let's break your task into steps.

##Step 1: Reading

Read the JSON object containing the key legal clauses carefully, make sure you understand each clause clearly


##Step 2: Checking for missing critical clauses 

Check whether all the following clauses are present or not and identify the missing clauses if exist:
- Definitions Clause
- Scope of Work Clause
- Payment Terms Clause
- Confidentiality Clause
- Termination Clause
- Force Majeure Clause
- Dispute Resolution Clause
- Governing Law / Choice of Law Clause
- Limitation of Liability Clause
- Entire Agreement Clause
- Indemnification Clause
- Notices Clause
- Amendment Clause
- Assignment Clause
- Severability Clause
- Non-Waiver Clause


#Step 3: Checking the correctness of clauses

For each clause present in the JSON, assess its health based on these criteria:
- Clarity: Is the clause written in clear language?
- Completeness: Does it fully cover what it should?
- Fairness / Balance: Does it protect the interests of both parties fairly?
- Risk Mitigation: Does it effectively manage legal, financial, and operational risks?

Focus on the following expected qualities per clause type:
- Definitions Clause: Clear, precise definitions; no ambiguity.
- Scope of Work Clause: Specific deliverables and timelines.
- Payment Terms Clause: Detailed schedule, amounts, method and penalties for late payment.
- Confidentiality Clause: Clear obligations, duration, exceptions.
- Termination Clause: Conditions, procedures, notice periods, fairness to both sides.
- Force Majeure Clause: Reasonable triggers, recovery time, mitigation obligations.
- Dispute Resolution Clause: Clear steps, cost-effective process, specified jurisdiction.
- Governing Law / Choice of Law Clause: Appropriate jurisdiction and legal certainty.
- Limitation of Liability Clause: Clear cap on liability, balanced exclusions.
- Entire Agreement Clause: Prevents side agreements, no ambiguity.
- Indemnification Clause: Clear scope, procedures, and limits.
- Notices Clause: Delivery methods, accuracy of addresses.
- Amendment Clause: Written, signed requirement.
- Assignment Clause: Controls transfer of rights, protects parties.
- Severability Clause: Ensures contract survives partial invalidity.
- Non-Waiver Clause: Protects rights from being waived by inaction.


##Step 3: Health assessment

Classify whether the contract is approved (healthy) or not based on the the following criteria:

The contract should be approved if:
-It contains all essential clauses (or reasonable equivalents) to protect both parties.
-Clauses are clear, complete, and balanced.
-The contract manages legal, financial, and operational risks effectively.

The contract should be not approved if:
-It is missing critical clauses.
-Clauses are vague, incomplete, or unfair.
-It exposes either party to unreasonable risks.


##Step 4: Reasoning
Provide a clear, concise, and professional explanation for your approval or disapproval decision (classification).

Your reasoning should:
- Summarize key strengths (presence of strong clauses, fair terms, effective risk management).
- Highlight weaknesses (missing critical clauses, vague language, unbalanced terms, unclear risk handling).
- Reference specific clauses or missing elements that contributed to your decision.
- Be written in plain English, suitable for business and legal professionals.

###Important:
Avoid assumptions about content not explicitly present in the provided JSON.



##Step 5: Output
Output the result as valid JSON with these fields:
- `approved`: true if the contract is healthy, false if it is not.
- `reasoning`: a clear and professional string summarizing your evaluation.
- `missing_critical_clauses`: list of exactly which critical clauses are missing.
- `issues`: list of exact issues in present clauses (ambiguity, imbalance, missing safeguards).
- `required_changes`: list of specific edits/additions required before approval.
- `risk_level`: `low`, `medium`, or `high`.

###Return only a valid JSON object. Do not include intermediate steps, headings, or explanations. Output must contain only valid JSON, no markdown or text around it.
###Do not infer or assume clauses that are not explicitly present in the input JSON. Only reference clauses that exist in the input.

###The JSON should look like this:
{{
  "approved": true or false,
  "reasoning": "Your professional explanation here.",
  "missing_critical_clauses": ["Clause A", "Clause B"],
  "issues": ["Specific issue 1", "Specific issue 2"],
  "required_changes": ["Specific fix 1", "Specific fix 2"],
  "risk_level": "low|medium|high"
}}

---

###IMPORTANT  
- Be precise and professional in your assessment.  
- Do not fabricate or assume content not present in the clause.  
- The output must contain valid JSON only, no extra explanation or comments.
- Think through the steps internally, but return only the final JSON output.

---

Here is an example to help you:

contract JSON:
{{
  "Definitions Clause": "“Confidential Information” means all non-public information disclosed by one party to the other, in any form, that is designated as confidential or that reasonably should be understood to be confidential.",
  "Scope of Work Clause": "Provider shall design, develop, and maintain a custom enterprise software platform for Client, as detailed in Exhibit B.",
  "Payment Terms Clause": "Client agrees to pay Provider a total of $500,000 in four equal installments, due upon completion of each project milestone as defined in Exhibit C. Late payments are subject to a 1.5% monthly interest charge.",
  "Confidentiality Clause": "Each party agrees to keep all Confidential Information strictly confidential, using at least reasonable care, and shall not disclose such information to any third party without prior written consent, except as required by law.",
  "Termination Clause": "This Agreement shall remain in effect for two years from the Effective Date, unless terminated earlier. Either party may terminate for cause upon 30 days’ written notice and opportunity to cure. Either party may terminate for convenience with 90 days’ prior written notice.",
  "Force Majeure Clause": "Neither party shall be liable for delays or failure to perform caused by acts beyond its reasonable control, including natural disasters, acts of war, or government regulations.",
  "Dispute Resolution Clause": "All disputes shall first be negotiated in good faith. If unresolved, disputes shall proceed to mediation, then binding arbitration under the rules of the American Arbitration Association in Chicago, Illinois.",
  "Governing Law / Choice of Law Clause": "This Agreement shall be governed by and construed in accordance with the laws of the State of Illinois, without regard to conflicts of law principles.",
  "Limitation of Liability Clause": "Neither party shall be liable for indirect, special, or consequential damages. Aggregate liability under this Agreement shall not exceed the total fees paid in the 12 months preceding the claim.",
  "Entire Agreement Clause": "This Agreement constitutes the entire understanding between the parties and supersedes all prior discussions, agreements, and understandings.",
  "Indemnification Clause": "Provider shall indemnify, defend, and hold harmless Client against claims arising from Provider’s gross negligence or willful misconduct.",
  "Notices Clause": "All notices shall be delivered via certified mail or email to the designated contact persons listed in Exhibit D.",
  "Assignment Clause": "Neither party may assign this Agreement without the prior written consent of the other party, except in connection with a merger or sale of substantially all assets.",
  "Severability Clause": "If any provision is found invalid, the remainder of the Agreement shall remain enforceable.",
  "Amendment Clause": "No modification of this Agreement shall be valid unless in writing and signed by both parties.",
  "Non-Waiver Clause": "The failure of either party to enforce any provision shall not be deemed a waiver of future enforcement.",
  "Transition Assistance": "Upon expiration or termination, Provider shall provide transition services for up to 60 days at standard hourly rates to assist with migration or handover.",
  "Data Security": "Provider agrees to implement and maintain commercially reasonable data security measures, including encryption, access controls, and regular security audits.",
  "Subcontracting": "Provider may subcontract portions of the services with Client’s prior written consent, but remains responsible for the subcontractor’s performance.",
  "Publicity": "Neither party shall issue press releases or public announcements relating to this Agreement without the prior written approval of the other party."
}}

Output:
{{
  "approved": true,
  "reasoning": "The contract is approved because it includes the critical protections and has no major gaps.",
  "missing_critical_clauses": [],
  "issues": [],
  "required_changes": ["No mandatory changes required. Optional: tighten SLA remedies and notice windows."],
  "risk_level": "low"
}}


"""

prompt2 = PromptTemplate.from_template(evaluation_system_prompt)


layman_clause_explainer_prompt = PromptTemplate.from_template(
    """
You are explaining contract clauses to someone who has never read a contract before.

Response language requirement: {response_language}.

Given this input JSON of clauses:
{clauses_json}

Return valid JSON only, with the EXACT SAME KEYS.
Each value must follow this exact format:
[CLAUSE_NAME]
What it means: One or two sentences in simple everyday language explaining what this clause means for the person signing.
What to watch out for: One sentence flagging anything that could be risky or unfair for the signing party (or say "Nothing unusual here." if it looks standard).

Strict rules:
- Do NOT repeat or copy the original clause text in your explanation.
- Do NOT use legal jargon. Write as if explaining to a friend over a phone call.
- Your explanation must be shorter than the original clause text.
- If a clause is short and standard (for example governing law), keep the explanation to one sentence maximum.
"""
)

contract_chat_prompt = PromptTemplate.from_template(
    """
You are a contract assistant that helps users understand a specific contract.

Rules:
- Answer using ONLY the provided contract text.
- If the answer is not in the contract, clearly say you cannot find it in the provided contract.
- Keep the answer natural, human, practical, and easy to understand.
- Adapt your tone and writing style to the user's style guide below without copying slang excessively.
- Use short paragraphs and bullets when useful.
- Response language requirement: {response_language}.

User style guide:
{user_style_guide}

Contract text:
{contract_text}

User question:
{question}
"""
)



def infer_user_style_guide(question: str, response_language: str) -> str:
    question_text = (question or "").strip()
    lang = normalize_response_language(response_language)

    if not question_text:
        return (
            "استخدم نبرة واضحة ومهنية مع شرح مبسط." if lang == "Arabic" else
            "Use a clear, professional tone with simple explanations."
        )

    lower_question = question_text.lower()

    if any(token in lower_question for token in ["simple", "explain like", "easy", "beginner", "بسيط", "شرح", "افهم"]):
        return (
            "استخدم أسلوبًا مبسطًا جدًا ولغة غير قانونية قدر الإمكان، مع مثال قصير إن أمكن."
            if lang == "Arabic"
            else "Use plain non-legal language, keep it beginner-friendly, and include one short example if helpful."
        )

    if "?" in question_text and len(question_text.split()) <= 10:
        return (
            "المستخدم يسأل بشكل مباشر وسريع؛ أجب بإيجاز شديد ثم أضف نقطة توضيح واحدة مهمة."
            if lang == "Arabic"
            else "The user asks directly; answer briefly first, then add one key clarification."
        )

    if len(question_text.split()) > 35:
        return (
            "المستخدم مفصل؛ قدّم إجابة منظمة مع نقاط واضحة وخطوات عملية."
            if lang == "Arabic"
            else "The user is detailed; provide a structured response with clear bullets and practical next steps."
        )

    return (
        "حافظ على نبرة ودودة ومهنية، وقدم إجابة واضحة مع نقاط عملية قصيرة."
        if lang == "Arabic"
        else "Keep a friendly professional tone and provide a clear answer with short practical points."
    )

# Backward-compatible sentinel; pipeline is handled manually in sync helper.
full_pipeline_chain = None




def _coerce_llm_content(raw_content: Any) -> str:
    """Normalize LangChain response content into plain text."""
    if raw_content is None:
        return ""
    if isinstance(raw_content, str):
        return raw_content
    if isinstance(raw_content, list):
        parts = []
        for item in raw_content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                if isinstance(item.get("text"), str):
                    parts.append(item["text"])
                elif item.get("type") == "text" and isinstance(item.get("content"), str):
                    parts.append(item["content"])
                else:
                    parts.append(str(item))
            else:
                parts.append(str(item))
        return "\n".join([p for p in parts if p]).strip()
    return str(raw_content)


def _extract_json_payload(raw_content: Any) -> Any:
    """Extract JSON from model output even when wrapped in markdown/code fences."""
    def _parse_json_loose(candidate: str) -> Any:
        payload = (candidate or "").strip()
        if not payload:
            raise ValueError("empty candidate")

        try:
            return json.loads(payload)
        except Exception:
            pass

        compact = re.sub(r",\s*([}\]])", r"\1", payload)
        try:
            return json.loads(compact)
        except Exception:
            pass

        # Python-like dict/list fallback (single quotes, True/False/None)
        for candidate_text in (payload, compact):
            try:
                parsed = ast.literal_eval(candidate_text)
                if isinstance(parsed, (dict, list)):
                    return parsed
            except Exception:
                continue

        raise ValueError("not parseable as JSON")

    text = _coerce_llm_content(raw_content).strip()
    if not text:
        raise ValueError("Model returned an empty response")

    try:
        return _parse_json_loose(text)
    except ValueError:
        pass

    if "```" in text:
        for block in text.split("```"):
            candidate = block.strip()
            if not candidate:
                continue
            if candidate.lower().startswith("json"):
                candidate = candidate[4:].strip()
            try:
                return _parse_json_loose(candidate)
            except ValueError:
                continue

    start_obj = text.find("{")
    end_obj = text.rfind("}")
    start_arr = text.find("[")
    end_arr = text.rfind("]")

    candidates = []
    if start_obj != -1 and end_obj > start_obj:
        candidates.append(text[start_obj : end_obj + 1])
    if start_arr != -1 and end_arr > start_arr:
        candidates.append(text[start_arr : end_arr + 1])

    for candidate in candidates:
        try:
            return _parse_json_loose(candidate)
        except ValueError:
            continue

    raise ValueError("Model output is not valid JSON")


def _normalize_clause_dict(model_output: Any) -> Dict[str, str]:
    if isinstance(model_output, dict) and isinstance(model_output.get("clauses"), dict):
        model_output = model_output["clauses"]

    if not isinstance(model_output, dict):
        raise ValueError("Clause payload must be a JSON object")

    normalized: Dict[str, str] = {}
    for key, value in model_output.items():
        if isinstance(value, dict):
            text = value.get("value") or value.get("text") or ""
        else:
            text = value

        text_str = str(text).strip()
        if text_str and text_str.lower() != "not found":
            normalized[str(key).strip()] = text_str

    if not normalized:
        raise ValueError("No usable clauses found in model output")
    return normalized


def _fallback_clause_extraction(contract_text: str) -> Dict[str, str]:
    from backend.services.contract_intelligence import extract_key_clauses

    extracted = extract_key_clauses(contract_text)
    clauses = extracted.get("clauses", {}) if isinstance(extracted, dict) else {}
    fallback: Dict[str, str] = {}
    for key, details in clauses.items():
        value = details.get("value") if isinstance(details, dict) else details
        text = str(value).strip() if value is not None else ""
        if text and text.lower() != "not found":
            fallback[str(key)] = text

    if not fallback:
        fallback["summary"] = (contract_text or "")[:500].strip()

    return fallback


def _fallback_layman_explanations(contract_clauses: Dict[str, str]) -> Dict[str, str]:
    explanations: Dict[str, str] = {}
    for key, value in contract_clauses.items():
        short = " ".join(str(value).split())[:220]
        explanations[str(key)] = f"This clause means: {short}" if short else "No simple explanation generated."
    return explanations

def normalize_response_language(response_language: str) -> str:
    lang = (response_language or "english").strip().lower()
    if lang in {"ar", "ara", "arabic", "العربية"}:
        return "Arabic"
    return "English"


def get_ocr_languages(response_language: str) -> str:
    if normalize_response_language(response_language) == "Arabic":
        return "ara+eng"
    return "eng+ara"


def analyze_contract_sync(
    contract_text: str,
    response_language: str = "english",
) -> Dict[str, str]:
    """
    Uses a GenAI model to extract and classify legal clauses from contract text.

    Args:
        contract_text (str): The full text of the contract.
        llm_model (Any): The LLM model instance to use (e.g. Ollama, Anthropic, etc.).

    Returns:
        Dict[str, str]: A dictionary where keys are clause types and values are clause contents.

    Raises:
        TypeError: If contract_text is not a string.
        ValueError: If contract_text is empty or model response is invalid.
        RuntimeError: For unexpected failures.
    """
    if not isinstance(contract_text, str):
        raise TypeError("contract_text must be a string")
    if not contract_text.strip():
        raise ValueError("contract_text cannot be empty or whitespace")
    try:
        prompt_text = prompt1.format(
            contract_text=contract_text,
            response_language=normalize_response_language(response_language),
        )
        result = llm_model.invoke(prompt_text).content
        clauses_raw = _extract_json_payload(result)
        return _normalize_clause_dict(clauses_raw)

    except Exception:
        # Open-source models may return near-JSON; recover with deterministic fallback.
        return _fallback_clause_extraction(contract_text)




def explain_clauses_for_layman_sync(
    contract_clauses: Dict[str, str],
    response_language: str = "english",
) -> Dict[str, str]:
    if not isinstance(contract_clauses, dict) or not contract_clauses:
        raise ValueError("contract_clauses must be a non-empty dictionary")

    for key, value in contract_clauses.items():
        if not isinstance(value, str):
            raise ValueError(f"Clause content for '{key}' must be a string")

    try:
        prompt_text = layman_clause_explainer_prompt.format(
            clauses_json=json.dumps(contract_clauses),
            response_language=normalize_response_language(response_language),
        )
        result = llm_model.invoke(prompt_text).content
        explanations = _extract_json_payload(result)

        if not isinstance(explanations, dict):
            raise ValueError("Model output for explanations is not a JSON object")

        normalized_explanations: Dict[str, str] = {}
        for key in contract_clauses.keys():
            text = explanations.get(key, "")
            normalized_explanations[key] = str(text).strip() if text else "No simple explanation generated."

        return normalized_explanations
    except Exception:
        return _fallback_layman_explanations(contract_clauses)

def evaluate_contract_sync(
    contract_clauses: Dict[str, str],
    response_language: str = "english",
) -> Dict[str, Any]:
    """
    Uses a GenAI model to assess the health of a contract based on its key legal clauses.

    Args:
        contract_clauses (Dict[str, str]): A dictionary of clause types and their contents.
        llm_model (Any): The LLM model instance to use.

    Returns:
        Dict[str, Any]: A dictionary containing:
            - 'approved' (bool): Whether the contract is healthy.
            - 'reasoning' (str): Explanation of the assessment.

    Raises:
        ValueError: If input is invalid or model response is not valid JSON or empty.
        RuntimeError: If the evaluation chain fails unexpectedly.
    """

    if not isinstance(contract_clauses, dict) or not contract_clauses:
        raise ValueError("contract_clauses must be a non-empty dictionary")
    for key, value in contract_clauses.items():
        if not isinstance(value, str):
            raise ValueError(f"Clause content for '{key}' must be a string")

    try:
        contract_json_str = json.dumps(contract_clauses)
        prompt_text = prompt2.format(
            contract_json=contract_json_str,
            response_language=normalize_response_language(response_language),
        )
        result = llm_model.invoke(prompt_text).content
        assessment = _extract_json_payload(result)

        if "approved" not in assessment or "reasoning" not in assessment:
            raise ValueError(
                "The model response does not contain required fields 'approved' and 'reasoning'."
            )

        # Normalize optional structured diagnostics to improve frontend rendering.
        assessment.setdefault("missing_critical_clauses", [])
        assessment.setdefault("issues", [])
        assessment.setdefault("required_changes", [])
        assessment.setdefault("risk_level", "medium")

        for key in ["missing_critical_clauses", "issues", "required_changes"]:
            if not isinstance(assessment.get(key), list):
                assessment[key] = [str(assessment[key])]
            assessment[key] = [str(item) for item in assessment[key]]

        if assessment.get("risk_level") not in {"low", "medium", "high"}:
            assessment["risk_level"] = "medium"

        return assessment

    except Exception:
        from backend.services.contract_health import evaluate_contract_health_from_clauses

        return evaluate_contract_health_from_clauses(
            contract_clauses,
            response_language=response_language,
        )


def analyze_and_evaluate_contract_sync(
    contract_text: str,
    pipeline_chain: Any = full_pipeline_chain,
    response_language: str = "english",
) -> Dict[str, Any]:
    """
    Runs the full contract analysis + evaluation pipeline in one step.

    Args:
        contract_text (str): The full text of the contract.
        pipeline_chain (Any): Backward-compatible placeholder; pipeline is run manually.

    Returns:
        Dict[str, Any]: The final evaluation result from the pipeline.

    Raises:
        TypeError: If contract_text is not a string.
        ValueError: If contract_text is empty or pipeline output is invalid.
        RuntimeError: If the pipeline fails unexpectedly.
    """
    if not isinstance(contract_text, str):
        raise TypeError("contract_text must be a string")
    if not contract_text.strip():
        raise ValueError("contract_text cannot be empty or whitespace")

    try:
        clauses = analyze_contract_sync(
            contract_text,
            response_language=response_language,
        )
        return evaluate_contract_sync(
            clauses,
            response_language=response_language,
        )

    except json.JSONDecodeError as e:
        raise ValueError(f"Pipeline output is not valid JSON: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"Pipeline failed: {str(e)}")


async def evaluate_contract(
    contract_clauses: Dict[str, str],
    response_language: str = "english",
) -> Dict[str, Any]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        executor, evaluate_contract_sync, contract_clauses, response_language
    )


async def analyze_contract(
    contract_text: str,
    response_language: str = "english",
) -> Dict[str, str]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        executor, analyze_contract_sync, contract_text, response_language
    )




async def explain_clauses_for_layman(
    contract_clauses: Dict[str, str],
    response_language: str = "english",
) -> Dict[str, str]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        executor, explain_clauses_for_layman_sync, contract_clauses, response_language
    )

async def analyze_and_evaluate_contract(
    contract_text: str,
    pipeline_chain: Any = None,
    response_language: str = "english",
) -> Dict[str, Any]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        executor,
        analyze_and_evaluate_contract_sync,
        contract_text,
        pipeline_chain,
        response_language,
    )


def contract_chat_sync(
    contract_text: str,
    question: str,
    response_language: str = "english",
) -> str:
    if not isinstance(contract_text, str) or not contract_text.strip():
        raise ValueError("contract_text must be a non-empty string")
    if not isinstance(question, str) or not question.strip():
        raise ValueError("question must be a non-empty string")

    try:
        prompt_text = contract_chat_prompt.format(
            contract_text=contract_text,
            question=question,
            response_language=normalize_response_language(response_language),
            user_style_guide=infer_user_style_guide(question, response_language),
        )
        result = llm_model.invoke(prompt_text).content
        response_text = _coerce_llm_content(result).strip()
        if response_text:
            return response_text
    except Exception:
        pass

    fallback = answer_contract_question(
        contract_text=contract_text,
        question=question,
        response_language=response_language,
    )

    if isinstance(fallback, dict):
        answer = str(fallback.get("answer", "")).strip()
        evidence = fallback.get("evidence", [])
        if answer:
            if isinstance(evidence, list) and evidence:
                quotes = []
                for item in evidence[:2]:
                    if isinstance(item, dict):
                        q = str(item.get("quote", "")).strip()
                        if q:
                            quotes.append(q)
                if quotes:
                    return answer + "\n\nEvidence:\n- " + "\n- ".join(quotes)
            return answer

    # Hard fallback for resilience: return a safe, deterministic message instead of raising.
    return "I couldn't generate a reliable AI response right now. Please ask a contract-specific question and I will answer from the provided contract text."


async def contract_chat(
    contract_text: str,
    question: str,
    response_language: str = "english",
) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        executor,
        contract_chat_sync,
        contract_text,
        question,
        response_language,
    )


class CorruptPDFError(Exception):
    """Raised when a PDF file is damaged, corrupt, or not a valid PDF."""

    pass


def extract_text_from_pdf(file_path: str) -> str:
    """
    Extracts text from a PDF file.

    Args:
        file_path (str): Path to the PDF file.

    Returns:
        str: The full extracted text from all pages.

    Raises:
        FileNotFoundError: If the file does not exist.
        IsADirectoryError: If the path is a directory.
        CorruptPDFError: If the file is not a valid PDF or is corrupted.
        ValueError: If no text could be extracted.
        RuntimeError: For unexpected failures in PDF processing.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError("PDF file not found: {file_path}")
    if os.path.isdir(file_path):
        raise IsADirectoryError(f"Expected a file but got a directory: {file_path}")

    try:
        text = ""
        pdf_doc = fitz.open(file_path)
        for page in pdf_doc:
            text += page.get_text()
        pdf_doc.close()

        if not text.strip():
            raise ValueError("No text could be extracted from the PDF.")

        return text

    except fitz.FileDataError:
        raise CorruptPDFError(
            f"The file is not a valid PDF or is corrupted: {file_path}"
        )
    except RuntimeError as e:
        raise RuntimeError(f"PyMuPDF processing failed: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error during PDF extraction: {str(e)}")


def _ocr_text_from_pdf_bytes(pdf_bytes: bytes, ocr_languages: str = "eng+ara") -> str:
    text = ""
    with fitz.open(stream=pdf_bytes, filetype="pdf") as pdf_doc:
        for page in pdf_doc:
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            image = Image.open(BytesIO(pix.tobytes("png")))
            text += pytesseract.image_to_string(image, lang=ocr_languages) + "\n"
    return text


def extract_text_from_pdf_bytes(
    pdf_bytes: bytes,
    use_ocr: bool = True,
    response_language: str = "english",
) -> str:
    """
    Extracts text from PDF bytes.

    Args:
        pdf_bytes (bytes): PDF file content as bytes.

    Returns:
        str: The full extracted text from all pages.

    Raises:
        CorruptPDFError: If the bytes are not a valid PDF or are corrupted.
        ValueError: If no text could be extracted.
        RuntimeError: For unexpected failures in PDF processing.
    """
    try:
        text = ""
        with fitz.open(stream=pdf_bytes, filetype="pdf") as pdf_doc:
            for page in pdf_doc:
                text += page.get_text()

        if text.strip():
            return text

        if use_ocr:
            ocr_text = _ocr_text_from_pdf_bytes(
                pdf_bytes, ocr_languages=get_ocr_languages(response_language)
            )
            if ocr_text.strip():
                return ocr_text

        raise ValueError("No text could be extracted from the PDF.")

    except fitz.FileDataError as exc:
        raise CorruptPDFError("The provided bytes are not a valid PDF or are corrupted") from exc
    except RuntimeError as e:
        raise RuntimeError(f"PyMuPDF processing failed: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error during PDF processing: {str(e)}")
