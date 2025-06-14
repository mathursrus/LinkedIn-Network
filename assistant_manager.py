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
            client.beta.assistants.retrieve(assistant_id)
            print(f"Using existing assistant with ID: {assistant_id}")
            return assistant_id
        except Exception:
            print(f"Assistant with ID {assistant_id} not found. ")

def create_assistant(client):
    """
    Creates a new assistant.
    """
    
    print("Creating a new assistant...")
    assistant = client.beta.assistants.create(
        name="LinkedIn Network Assistant",
        instructions="""Mission: Help job seekers grow their network by identifying valuable professional connections, leveraging existing relationships, and crafting tailored outreach messages. Be empathetic, proactive, and strategic.

🧠 Core Capabilities
Discover Connections

Identify individuals at target companies using search tools.

Determine mutual connections between user and target individuals.

Highlight influential contacts (decision-makers, team leads, etc.).

Strategize Networking

Suggest the best person to reach out to based on role, location, and influence.

Offer warm intros if mutual connections are available.

Visualize network paths clearly (e.g., "You know Alice, who knows Bob at Google").

Craft Personalized Messages

Write outreach messages tailored to the target person and company.

Use a tone that is professional, warm, and specific to job seeking.

Offer variations (e.g., direct cold message, warm intro request, follow-up).

Provide Research & Insights

Look up recent news about companies and people.

Give context on company culture, recent hires, or initiatives.

Suggest what to mention in the message to create relevance.

🔍 Data Sources & Tools
Use the actions provided to you when you do not have the data you need.
The actions will provide JSON files that you should fully understand. A connection level of 1 means that the person is a direct connection of the user. 
A connection level of 2 means that the person is a connection of a connection of the user. Mutual connections are the people that the user and the target person have in common.
If you already have data about mutual connections from a previous run, then you should not call the find_mutual_connections function again.
If you already have data about the role, location, or company of the target person, then you should not call the search_linkedin_role or search_linkedin_connections function again.
The role, location of people is directly available from the first search for either the company or the person. Use that information instead of searching for it again.

💬 Tone & Interaction Style
Be empathetic and supportive—job seeking is hard.

Be strategic and proactive—always help the user take the next step.

Be clear and actionable—offer copy-paste ready messages and decision-making help.

Avoid flattery; focus on value and honesty.

🚫 Guardrails
Dont fabricate connections—always use real data or direct users to get it.

Dont overpromise—some connections may not reply or help.

Dont suggest spamming—quality outreach over quantity.

Avoid making direct judgments about users qualifications or worth.

✅ Example Use Cases
"Help me connect with someone at Spotify in Product Management."

"I want to message the Head of Data at Airbnb. Can you help?"

"Who do I know that works at Stripe?"

"Can you write a message asking for an intro to Jane Doe at Netflix?"
""",
        model="gpt-3.5-turbo",
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "search_linkedin_connections",
                    "description": "Search for LinkedIn connections at a specific company. The results will contain people who work at that company who the user is directly connected to (connection level 1) as well as people who work at that company are are connected to the user through other mutual connections. Each mutual connection will also have their details provided so you can use it for the future.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "company_name": {
                                "type": "string",
                                "description": "The name of the company to search for connections"
                            },
                             "connection_degree": {
                                "type": "string",
                                "enum": ["1st", "2nd", "both"],
                                "description": "The degree of connections to search for",
                                "default": "both"
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum number of results to return",
                                "default": 50
                            }
                        },
                        "required": ["company_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_linkedin_role",
                    "description": "Search for LinkedIn connections with a specific role at a company.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "role_name": {
                                "type": "string",
                                "description": "The role or job title to search for"
                            },
                            "company_name": {
                                "type": "string",
                                "description": "The company to limit the search to"
                            }
                        },
                        "required": ["role_name", "company_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "find_mutual_connections",
                    "description": "Search for common connections between two people on LinkedIn. Only call this function if you dont already have this data from a company wide connections search.",
                     "parameters": {
                        "type": "object",
                        "properties": {
                             "person_name": {
                                "type": "string",
                                "description": "The name of the person to find mutual connections with"
                            },
                            "company_name": {
                                "type": "string",
                                "description": "The company to limit search to"
                            },
                             "max_results": {
                                "type": "integer",
                                "description": "Maximum number of results to return",
                                "default": 50
                            }
                        },
                        "required": ["person_name", "company_name"]
                    }
                }
            },
             {
                "type": "function",
                "function": {
                    "name": "find_connections_at_company_for_person",
                    "description": "Finds out if a person in your network knows anyone at a specific company.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "person_name": {
                                "type": "string",
                                "description": "The name of the person in your network to check."
                            },
                            "company_name": {
                                "type": "string",
                                "description": "The company to see if the person has connections at."
                            }
                        },
                        "required": ["person_name", "company_name"]
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