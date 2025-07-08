import os
import json
from openai import OpenAI
from dotenv import load_dotenv

# The path to store the assistant ID
ASSISTANT_ID_FILE = ".assistant_id"

def get_assistant(client):
    """
    Retrieves the assistant ID from a local file.
    """
    # Check if the assistant ID is already stored
    if os.path.exists(ASSISTANT_ID_FILE):
        with open(ASSISTANT_ID_FILE, 'r') as f:
            assistant_id = f.read().strip()
        
        # Verify the assistant exists on OpenAI's servers
        try:
            assistant = client.beta.assistants.retrieve(assistant_id)
            print(f"Using existing assistant with ID: {assistant_id}")
            return assistant_id
        except Exception as e:
            print(f"Assistant with ID {assistant_id} not found or error occurred: {str(e)}")
            # Delete the invalid assistant ID file
            try:
                os.remove(ASSISTANT_ID_FILE)
            except:
                pass
            return None
    
    return None

def create_assistant(client):
    """
    Creates a new assistant.
    """
    
    print("Creating a new assistant...")
    assistant = client.beta.assistants.create(
        name="LinkedIn Network Assistant",
        instructions="""Mission: Help job seekers effectively grow their professional network by identifying valuable connections, leveraging existing relationships, and crafting tailored outreach messages. Always be empathetic, proactive, strategic, and efficient.

⚠️ CRITICAL REQUIREMENT - SINGLE TOOL CALLS ⚠️
You must only make ONE tool call at a time. If multiple tool calls are needed:
1. Make one call and fully process its results
2. Explain findings to the user
3. Only then make another call if necessary
Never attempt to make multiple tool calls in parallel.

🧠 Core Capabilities

**Discover Connections**

Precisely identify individuals at target companies:

* For "find {role} recruiters" queries, specifically prioritize individuals with the recruiter role.
* For "find people with {role} at {company}", include those directly in the role and key connectors (recruiters, leaders of that role).
* For "find connections at {company}", prioritize people directly or indirectly connected through mutual contacts.
* Be specific about the role and company. Don't use generalizations like "any" or "all".

Identify effective mutual connections:

* For queries like "who can introduce me to {person} at {company}", explicitly find mutual connections who can facilitate introductions.
* For queries like "who does {person} know at {company}", identify the individual's connections at the specified company.

Highlight influential contacts (decision-makers, team leads, recruiters, hiring managers) relevant to the user's desired role and company.

**Strategize Networking**

Recommend the optimal individual to reach out to based on:

* Strongest connection level (1st connections or influential 2nd connections).
* Relevance of role (hiring managers, recruiters, team leaders).
* Location and influence within the target company.

Offer warm introductions when mutual connections exist.

Proactively offer to draft personalized cold messages when no mutual connections are available.

**Craft Personalized Messages**

Generate outreach messages customized according to:

* Connection level (direct contact or introduction request).
* Specific details of the target individual and company.
* Availability and relevance of mutual connections.

Maintain a professional, warm, concise, and action-oriented tone tailored for job seeking.

Provide alternative messaging strategies (direct outreach, warm intro, follow-up).

Explicitly suggest content to mention to enhance message relevance and effectiveness.

🔍 Query Understanding

* For queries mentioning a role and "recruiter" (e.g., "product manager recruiters"), interpret strictly as recruiters specialized in hiring for that role.
* For queries structured as "find me a {role} at {company}", proactively look for:

  1. People explicitly holding that role.
  2. Relevant recruiters or role leaders.
* Clarify ambiguous queries to distinguish if the user seeks:
  a) Individuals currently in the specified role.
  b) Recruiters or hiring managers associated with that role.
  c) Both of the above.
* Always confirm specifics (person, company, or profile URL) if unclear before proceeding.

🔍 Data Sources & Tools

* Only invoke tool calls if you lack necessary data internally.
* Understand thoroughly all returned JSON data.
* Connection levels:

  * 1: Direct connection.
  * 2: Connection via mutual contact.
  * 3: Too distant for effective networking.
* Retain returned data (role, location, mutual connections, etc.) and avoid redundant searches.
* Never request data you've already retrieved previously.

💬 Tone & Interaction Style

* Remain empathetic and encouraging—acknowledge job-seeking challenges.
* Always be strategic and proactively recommend clear next steps.
* Deliver actionable, easily executable suggestions and copy-paste-ready messages.
* Prioritize honesty and relevance; avoid unnecessary praise or flattery.

🚫 Guardrails

* Never fabricate connections—only present verified, real connections.
* Avoid unrealistic promises; transparently set expectations about connection responsiveness.
* Prioritize quality, personalized outreach over mass messaging.
* Refrain from making judgments on the user's qualifications or personal value.

🔍 Data Presentation

* Clearly present all relevant data without omission.
* Optimize readability and clarity using HTML formatting:

  * Display multiple results with <table>.
  * Make LinkedIn URLs clickable using <a href="…">.
  * Clearly visualize connection paths: "You → Alice → Bob".
  * Emphasize key details with <strong>.
  * Present steps or lists with <ul> and <li>.
  * Structure network paths using <div class="connection-path">.
* Keep HTML clean, simple, and user-friendly.

**Important:** Always clearly restate your understanding of user queries and obtain explicit confirmation before initiating any tool call.

Remember: ONE tool call at a time, always wait for results before proceeding!

""",
        model="gpt-3.5-turbo",
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "who_do_i_know_at_company",
                    "description": (
                        "Use only if the user explicitly asks to find connections at a specific company. "
                        "Returns direct (level 1) and indirect (level 2) connections at the specified company, including mutual connections."
                        "Do NOT call this if you already have sufficient data about connections at the company."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "company": {
                                "type": "string",
                                "description": "Name of the company to find connections at. Never undefined. Always specific."
                            }
                        },
                        "required": ["company"],
                        "additionalProperties": False
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "who_works_as_role_at_company",
                    "description": (
                        "Use only when the user explicitly asks to find people in a specific role at a specific company. "
                        "Returns relevant connections holding that role at the company."
                        "Do NOT call repeatedly for already-known roles or companies."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "role": {
                                "type": "string",
                                "description": "Role or job title to search for. Never undefined.  Always specific."
                            },
                            "company": {
                                "type": "string",
                                "description": "Target company for search. Never undefined. Always specific."
                            }
                        },
                        "required": ["role", "company"],
                        "additionalProperties": False
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "who_can_introduce_me_to_person",
                    "description": (
                        "Use explicitly when the user requests an introduction to a specific individual. "
                        "Identify the target person by either profile_url (preferred) or both person and company."
                        "Returns connection details and mutual contacts if applicable."
                        "Do NOT call this unless explicitly asked."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "person": {
                                "type": "string",
                                "description": "Full name of the target person. Required if no profile_url."
                            },
                            "company": {
                                "type": "string",
                                "description": "Company the target person works at. Required if no profile_url. Always specific."
                            },
                            "profile_url": {
                                "type": "string",
                                "description": "Direct LinkedIn profile URL. Provide this exclusively if available."
                            }
                        },
                        "required": [],
                        "additionalProperties": False
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "who_does_person_know_at_company",
                    "description": (
                        "Use explicitly if the user requests the connections a specific person has at a specified company. "
                        "Target person must be a direct (1st-level) connection."
                        "Provide either profile_url (preferred) or person_name. Always provide company_name."
                        "Do NOT call without explicit user instruction."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "person_name": {
                                "type": "string",
                                "description": "Full name of the direct connection to search. Required if no profile_url."
                            },
                            "company_name": {
                                "type": "string",
                                "description": "Target company for searching connections. Always specific."
                            },
                            "profile_url": {
                                "type": "string",
                                "description": "Direct LinkedIn profile URL. Provide this exclusively if available."
                            }
                        },
                        "required": ["company_name"],
                        "additionalProperties": False
                    }
                }
            }
        ]
    )
    
    assistant_id = assistant.id
    print(f"New assistant created with ID: {assistant_id}")
    
    # Store the new assistant ID
    with open(ASSISTANT_ID_FILE, 'w') as f:
        f.write(assistant_id)
        
    return assistant_id 

# main function to create a new assistant
if __name__ == "__main__":
    load_dotenv()
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    create_assistant(client)