from langchain_openai import ChatOpenAI
import openai
from langchain.prompts import PromptTemplate
from typing import Dict, Any
from io import BytesIO
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor
import os
import fitz  # PyMuPDF
from PIL import Image
import pytesseract

executor = ThreadPoolExecutor()


OPENAI_API_KEY = os.getenv(
    "OPENAI_API_KEY",
    "",
)
if not OPENAI_API_KEY:
    print(
        "WARNING: OPENAI_API_KEY environment variable is not set. GenAI features will be disabled."
    )
openai.api_key = OPENAI_API_KEY

llm_model = ChatOpenAI(
    model_name="gpt-4", temperature=0.2, openai_api_key=OPENAI_API_KEY
)

analysis_system_prompt = """ 
    
You are a professional and intelligent contract analyzer specialized in extracting key clause types and their contents from a contract text.

Your responsibilities include:
1. Reading contracts carefully.
2. Identifying and classifying key legal clauses.
3. Returning a structured JSON object where each key is the clause type and the value is its full content as found in the contract.

---

You are given this contract text:

{contract_text}

---

Response language requirement: {response_language}.

Your task is to read the contract text carefully, analyze it, and extract the key legal clauses to return a structured JSON object containing the clause types and their contents.

Let’s break your task into steps:

---

## Step 1: Reading  
Carefully read the contract text, make sure you understand every word, heading, and statement.

---

## Step 2: Identification & Classification  
Identify and classify the key legal clauses found in the contract text.

### Focus on these clause types (normalize variations as instructed):

- Definitions Clause: Establishes the meaning of specific terms used throughout the contract to ensure consistent interpretation and avoid misunderstandings.

- Scope of Work Clause: Clearly defines the services, deliverables, or obligations expected from each party, specifying what is included and excluded.

- Payment Terms Clause: Specifies the payment schedule, amounts, methods, and consequences of late or missed payments.

- Confidentiality Clause: Protects sensitive or proprietary information from unauthorized disclosure during and after the contract.

- Termination Clause: Outlines the conditions, procedures, and notice requirements under which the contract may be ended before its natural expiration.

- Force Majeure Clause: Relieves parties from liability or obligation when unforeseeable and uncontrollable events prevent contract performance.

- Dispute Resolution Clause: Specifies how disputes will be handled, including methods such as negotiation, mediation, arbitration, and applicable jurisdiction.

- Governing Law / Choice of Law Clause: Determines which jurisdiction’s laws will govern the interpretation and enforcement of the contract.

- Limitation of Liability Clause: Caps the amount or types of damages a party may be liable for, helping allocate and limit risk.

- Entire Agreement Clause: Confirms that the written contract constitutes the full agreement between the parties, superseding prior agreements or oral understandings.

- Indemnification Clause: Describes each party’s obligation to protect the other from specified claims or damages.

- Notices Clause: Specifies how and where legal notices or formal communications must be sent.

- Amendment Clause: Explains how the contract may be modified or amended.

- Assignment Clause: Defines whether rights or obligations can be assigned or transferred to another party.

- Severability Clause: Ensures the rest of the contract remains enforceable even if one provision is invalid.

- Non-Waiver Clause: States that failure to enforce a provision does not waive the right to enforce it later.

---

### IMPORTANT:
Map clause titles that are similar to the correct type.

Examples of acceptable mappings:
- Term and Termination = Termination Clause
- Termination and Renewal = Termination Clause
- Governing Law = Governing Law / Choice of Law Clause
- Limitation of Liability and Disclaimer = Limitation of Liability Clause
- Dispute Resolution and Arbitration = Dispute Resolution Clause
- Assignment and Subcontracting = Assignment Clause

If the contract contains a clause with a different heading but a similar meaning to the description, map it to the appropriate type.

Do not skip clauses that match or map to these types, even if the title is written slightly different.

In addition to the specific clause types listed above, if the contract contains any other legal clauses not mentioned in the list, you must also extract and include them in the output using their exact title as it appears in the contract.

---

## Step 3: Output  
Present the results of your analysis as a valid JSON object where:
- Each key is the exact clause type.
- Each value is the full content of the clause as found in the contract text (keep the same wording, punctuation, and formatting).

The output must be valid JSON with no extra text, notes, or comments — only the JSON object.

Do not fabricate clauses that do not exist.

Do not leave empty keys or placeholders for missing clauses — simply omit them.

---

### The JSON format should be like this:
{{
  "ClauseType": "Clause content here...",
  "ClauseType": "Clause content here..."
}}

---

Here is an example to help you :


contract text :
"
MASTER SERVICE AGREEMENT

This Master Service Agreement (“Agreement”) is entered into by and between Omega Corp (“Contractor”) and Delta Ltd (“Client”) effective as of July 1, 2025.

1. Definitions  
For the purposes of this Agreement, “Confidential Information” includes but is not limited to trade secrets, business plans, and customer data.

2. Scope and Deliverables  
Contractor shall provide IT consulting, cloud migration, and cybersecurity services pursuant to statements of work (“SOWs”) issued under this Agreement.

3. Payment and Invoicing  
Client shall remit payment net 45 days upon receipt of invoice. Invoices are issued monthly and must be disputed within 15 days or deemed accepted.

4. Change Orders  
Any modifications to the scope require written change orders signed by authorized representatives of both parties.

5. Confidentiality and Data Protection  
Parties agree to maintain strict confidentiality, comply with applicable data protection laws (including GDPR), and implement reasonable security measures.

6. Intellectual Property Rights  
Contractor retains all pre-existing IP. Deliverables created under this Agreement shall be owned by Client upon full payment, subject to Contractor’s moral rights.

7. Representations and Warranties  
Contractor represents it has all necessary licenses and will perform work in accordance with industry standards. Client warrants that data provided is accurate and lawful.

8. Limitation of Liability and Disclaimer  
Neither party shall be liable for incidental, punitive, or consequential damages. Liability caps at the total fees paid in the prior 12 months.

9. Indemnification and Defense  
Each party agrees to indemnify, defend, and hold harmless the other against third-party claims arising from negligence or breach of this Agreement.

10. Force Majeure  
Events beyond reasonable control, including acts of government, pandemics, or cyberattacks, excuse non-performance for the duration of the event plus reasonable recovery time.

11. Term, Termination, and Renewal  
Initial term of two years, automatically renewing for one-year periods unless either party gives 90 days prior written notice. Termination for material breach requires 60 days cure.

12. Transition Assistance  
Upon termination, Contractor will provide up to 30 days transition support at standard rates.

13. Dispute Resolution and Arbitration  
Disputes not resolved by good faith negotiation shall proceed to mediation, then final and binding arbitration under ICC rules in New York.

14. Governing Law and Jurisdiction  
Agreement governed by New York law. Jurisdiction exclusive to courts in New York County.

15. Assignment and Subcontracting  
Client may assign rights with consent. Contractor may subcontract duties but remains liable for subcontractor performance.

16. Compliance with Laws  
Both parties shall comply with all applicable laws, regulations, and export controls.

17. Notices  
All communications must be in writing and sent by registered mail or courier.

18. Entire Agreement and Amendments  
This Agreement supersedes all prior agreements and may be amended only by written document signed by authorized representatives.

19. Severability  
If any provision is invalid, remaining provisions shall remain enforceable.

20. Non-Waiver  
Failure to exercise any right shall not constitute waiver.

21. Counterparts  
This Agreement may be executed in counterparts, each considered an original.

22. Further Assurances  
Parties agree to take further actions as necessary to effectuate the Agreement.

IN WITNESS WHEREOF, the parties have caused this Agreement to be duly executed.


Output:
{{
  "Definitions": "For the purposes of this Agreement, “Confidential Information” includes but is not limited to trade secrets, business plans, and customer data.",
  "Scope and Deliverables": "Contractor shall provide IT consulting, cloud migration, and cybersecurity services pursuant to statements of work (“SOWs”) issued under this Agreement.",
  "Payment and Invoicing": "Client shall remit payment net 45 days upon receipt of invoice. Invoices are issued monthly and must be disputed within 15 days or deemed accepted.",
  "Change Orders": "Any modifications to the scope require written change orders signed by authorized representatives of both parties.",
  "Confidentiality and Data Protection": "Parties agree to maintain strict confidentiality, comply with applicable data protection laws (including GDPR), and implement reasonable security measures.",
  "Intellectual Property Rights": "Contractor retains all pre-existing IP. Deliverables created under this Agreement shall be owned by Client upon full payment, subject to Contractor’s moral rights.",
  "Representations and Warranties": "Contractor represents it has all necessary licenses and will perform work in accordance with industry standards. Client warrants that data provided is accurate and lawful.",
  "Limitation of Liability and Disclaimer": "Neither party shall be liable for incidental, punitive, or consequential damages. Liability caps at the total fees paid in the prior 12 months.",
  "Indemnification and Defense": "Each party agrees to indemnify, defend, and hold harmless the other against third-party claims arising from negligence or breach of this Agreement.",
  "Force Majeure": "Events beyond reasonable control, including acts of government, pandemics, or cyberattacks, excuse non-performance for the duration of the event plus reasonable recovery time.",
  "Term, Termination, and Renewal": "Initial term of two years, automatically renewing for one-year periods unless either party gives 90 days prior written notice. Termination for material breach requires 60 days cure.",
  "Transition Assistance": "Upon termination, Contractor will provide up to 30 days transition support at standard rates.",
  "Dispute Resolution and Arbitration": "Disputes not resolved by good faith negotiation shall proceed to mediation, then final and binding arbitration under ICC rules in New York.",
  "Governing Law and Jurisdiction": "Agreement governed by New York law. Jurisdiction exclusive to courts in New York County.",
  "Assignment and Subcontracting": "Client may assign rights with consent. Contractor may subcontract duties but remains liable for subcontractor performance.",
  "Compliance with Laws": "Both parties shall comply with all applicable laws, regulations, and export controls.",
  "Notices": "All communications must be in writing and sent by registered mail or courier.",
  "Entire Agreement and Amendments": "This Agreement supersedes all prior agreements and may be amended only by written document signed by authorized representatives.",
  "Severability": "If any provision is invalid, remaining provisions shall remain enforceable.",
  "Non-Waiver": "Failure to exercise any right shall not constitute waiver.",
  "Counterparts": "This Agreement may be executed in counterparts, each considered an original.",
  "Further Assurances": "Parties agree to take further actions as necessary to effectuate the Agreement."
}}

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
- `reasoning`: A concise, professional explanation of why the contract is approved or not, mentioning key strengths and weaknesses (e.g., missing critical clauses, vague language, unfair terms).

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
Output the result as valid JSON with two fields:
- `approved`: true if the contract is healthy, false if it is not.
- `reasoning`: a clear and professional string summarizing your evaluation.

###Return only a valid JSON object. Do not include intermediate steps, headings, or explanations. Output must contain only valid JSON, no markdown or text around it.
###Do not infer or assume clauses that are not explicitly present in the input JSON. Only reference clauses that exist in the input.

###The JSON should look like this:
{{
  "approved": true or false,
  "reasoning": "Your professional explanation here."
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
  "reasoning": "The contract is approved because it contains all critical clauses necessary to protect both parties, including Definitions, Scope of Work, Payment Terms, Confidentiality, Termination, Force Majeure, Dispute Resolution, Governing Law, Limitation of Liability, Entire Agreement, Indemnification, Notices, Amendment, Assignment, Severability, and Non-Waiver. All clauses are written clearly, with complete, fair, and balanced terms that effectively mitigate legal, financial, and operational risks. Additional helpful clauses, such as Transition Assistance, Data Security, Subcontracting, and Publicity restrictions, further strengthen risk management and operational clarity. No critical clauses are missing, and the contract presents no unreasonable risk to either party."
}}


"""

prompt2 = PromptTemplate.from_template(evaluation_system_prompt)

# Backward-compatible sentinel; pipeline is handled manually in sync helper.
full_pipeline_chain = None


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
        llm_model (Any): The LLM model instance to use (e.g. OpenAI, Anthropic, etc.).

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
        clauses = json.loads(result)

        if not clauses:
            raise ValueError("The model returned an empty clause dictionary.")
        return clauses

    except json.JSONDecodeError as e:
        raise ValueError(f"Model output is not valid JSON: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"Failed to extract clauses: {str(e)}")


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
        assessment = json.loads(result)

        if "approved" not in assessment or "reasoning" not in assessment:
            raise ValueError(
                "The model response does not contain required fields 'approved' and 'reasoning'."
            )

        return assessment

    except json.JSONDecodeError as e:
        raise ValueError(f"Model output is not valid JSON: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"Failed to assess contract health: {str(e)}")


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
