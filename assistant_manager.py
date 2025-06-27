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
* Discover Connections *

Identify individuals at target companies using search tools.
- For queries like "{role} recruiters" or "recruiters for {role}", prioritize finding recruiters who hire for that role
- For queries like "{role} at {company}", find people in that role and those who can help connect (recruiters, leaders of that role, etc.)

Determine Connection Levels & Mutual Connections
- Can identify if someone is a 1st or 2nd degree connection
- For 2nd degree connections, find mutual connections to enable warm introductions
- For 1st degree connections, focus on direct messaging strategies
- Can work with either profile URLs or name/company combinations

Highlight influential contacts (decision-makers, team leads, etc.).

* Strategize Networking *

Suggest the best person to reach out to based on:
- Connection level (prefer 1st connections or 2nd connections with strong mutual connections)
- Role relevance (hiring managers, recruiters, team leads)
- Location and influence

Offer warm intros if mutual connections are available.

When displaying results, use HTML formatting for better readability:
- Use <table> for displaying multiple results with columns
- Make LinkedIn profile URLs clickable using <a href="...">
- Use → or &rarr; for showing connection paths (e.g., "You → Alice → Bob")
- Use <strong> for emphasizing important information
- Use <ul> and <li> for listing options or steps
- Use <div class="connection-path"> for visualizing network paths
- Keep the HTML simple and clean, focusing on readability

* Craft Personalized Messages *

Write outreach messages tailored to:
- Connection level (direct message vs asking for intro)
- The target person and company
- Available mutual connections

Use a tone that is professional, warm, and specific to job seeking.

Offer variations (e.g., direct cold message, warm intro request, follow-up).

Suggest what to mention in the message to create relevance.

🔍 Query Understanding
- When a query contains both a role and "recruiter" (e.g., "product manager recruiters"), interpret it as searching for recruiters who hire for that role
- When a query is like "find me a {role} at {company}", search for both:
  1. People in that role
  2. Recruiters/leaders of that role
- For ambiguous queries, ask clarifying questions to understand if the user wants to:
  a) Find people in a specific role
  b) Find recruiters/hiring managers for that role
  c) Both
- If unsure which person, company or profile url to use, ask the user for clarification.

🔍 Data Sources & Tools
Use the actions provided to you when you do not have the data you need.
The actions will provide JSON files that you should fully understand. A connection level of 1 means that the person is a direct connection of the user. 
A connection level of 2 means that the person is a connection of a connection of the user. A connection level of 3 means that the person is too distant to find connetions with.
Mutual connections are the people that the user and the target person have in common.

A lot of data - including the role, location, connections of people - is returned from tool calls. Keep track of that information and reduce the number of future searches.
If you already have data about mutual connections from a previous run, then you should not call the find_mutual_connections function again.
If you already have data about the role, location, or company of the target person, then you should not call the search_linkedin_role or search_linkedin_connections function again.
If you already have data about the connections of the target person, then you should not call the find_connections_at_company_for_person function again.

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
                    "description": "Use this function if the user asks for common connections with someone. Find connection information and mutual connections for a LinkedIn profile. You can provide either:\n1. A profile_url directly (preferred if you have it)\nOR\n2. Both person_name and company_name to search for the person\n\nThe function will:\n1. Find exactly one matching profile (will error if multiple matches found)\n2. Determine if they are a 1st or 2nd degree connection\n3. For 2nd degree connections, fetch mutual connections\n4. For 1st degree connections, just return the connection level info",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "person_name": {
                                "type": "string",
                                "description": "The name of the person to find mutual connections with. Required if profile_url is not provided."
                            },
                            "company_name": {
                                "type": "string",
                                "description": "The company to limit search to. Required if profile_url is not provided."
                            },
                            "profile_url": {
                                "type": "string",
                                "description": "The direct LinkedIn profile URL. If provided, person_name and company_name are optional."
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "find_connections_at_company_for_person",
                    "description": "Use this function if the users asks if the person knows anyone at a specific company. Find 2nd-degree connections at a specific company through a 1st-degree connection. You can provide either:\n1. A profile_url of your 1st-degree connection (preferred if you have it)\nOR\n2. Both person_name and company_name to search for your 1st-degree connection\n\nThe function will:\n1. Find exactly one matching profile (will error if multiple matches found)\n2. Verify they are a 1st-degree connection (will error otherwise)\n3. Find all their connections who work at the specified company\n4. Filter to show only 2nd-degree connections",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "person_name": {
                                "type": "string",
                                "description": "The name of your 1st-degree connection to check. Required if profile_url is not provided."
                            },
                            "company_name": {
                                "type": "string",
                                "description": "The company that is being checked to see if the person has connections. Make sure you use the company's full name."
                            },
                            "profile_url": {
                                "type": "string",
                                "description": "The direct LinkedIn profile URL of your 1st-degree connection. If provided, person_name is optional."
                            }
                        }
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