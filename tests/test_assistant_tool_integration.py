import os
import time
import pytest
from openai import OpenAI
from dotenv import load_dotenv
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from assistant_manager import get_assistant

load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")

# Helper to send a message and assert tool call

def assert_tool_call(user_message, expected_tool, expected_args_predicate):
    client = OpenAI(api_key=API_KEY)
    assistant_id = get_assistant(client)
    if not assistant_id:
        pytest.skip("Assistant ID could not be retrieved from assistant_manager.")
    thread = client.beta.threads.create()
    client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=user_message
    )
    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant_id
    )
    for _ in range(30):
        run_status = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
        if run_status.status in ("completed", "failed", "cancelled", "expired", "requires_action"):
            break
        time.sleep(2)
    else:
        pytest.fail("Run did not complete or require action in time")
    if run_status.status == "requires_action":
        required_action = run_status.required_action
        tool_calls = required_action.submit_tool_outputs.tool_calls
        assert len(tool_calls) == 1
        tool_call = tool_calls[0]
        assert tool_call.function.name == expected_tool
        args = tool_call.function.arguments
        # Make args check case-insensitive
        args_lower = args.lower() if isinstance(args, str) else str(args).lower()
        assert expected_args_predicate(args_lower), f"Arguments did not match: {args}"
    else:
        pytest.fail(f"Run did not require action, status: {run_status.status}")

@pytest.mark.skipif(not API_KEY, reason="OpenAI API key not set")
def test_who_do_i_know_at_company_tool_call():
    assert_tool_call(
        "Who do I know at Google?",
        "who_do_i_know_at_company",
        lambda args: "google" in args or args == '{"company": "google"}'
    )

@pytest.mark.skipif(not API_KEY, reason="OpenAI API key not set")
def test_who_works_as_role_at_company_tool_call():
    assert_tool_call(
        "Show me all software engineers at Amazon.",
        "who_works_as_role_at_company",
        lambda args: ("software engineer" in args or "software engineers" in args) and "amazon" in args
    )

@pytest.mark.skipif(not API_KEY, reason="OpenAI API key not set")
def test_who_can_introduce_me_to_person_tool_call():
    assert_tool_call(
        "Can anyone introduce me to Alice Smith at Meta?",
        "who_can_introduce_me_to_person",
        lambda args: "alice smith" in args and "meta" in args
    )

@pytest.mark.skipif(not API_KEY, reason="OpenAI API key not set")
def test_who_can_introduce_me_to_person_by_url_tool_call():
    assert_tool_call(
        "Can anyone introduce me to this person? http://linkedin.com/in/alice-smith",
        "who_can_introduce_me_to_person",
        lambda args: "http://linkedin.com/in/alice-smith" in args
    )

@pytest.mark.skipif(not API_KEY, reason="OpenAI API key not set")
def test_who_does_person_know_at_company_tool_call():
    assert_tool_call(
        "Who does Bob Johnson know at Tesla?",
        "who_does_person_know_at_company",
        lambda args: "bob johnson" in args and "tesla" in args
    )

@pytest.mark.skipif(not API_KEY, reason="OpenAI API key not set")
def test_who_does_person_know_at_company_by_url_tool_call():
    assert_tool_call(
        "Who does this person know at Apple? http://linkedin.com/in/bob-johnson",
        "who_does_person_know_at_company",
        lambda args: "http://linkedin.com/in/bob-johnson" in args and "apple" in args
    ) 

@pytest.mark.skipif(not API_KEY, reason="OpenAI API key not set")
def test_recruiter_for_pm_call():
    assert_tool_call(
        "I'm looking for PM recruiters at OpenAI",
        "who_works_as_role_at_company",
        lambda args: ("recruiters" in args) and "openai" in args
    ) 