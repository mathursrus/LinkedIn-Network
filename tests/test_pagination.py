import pytest
import asyncio
from linkedin_network_builder import initialize_browser, navigate_all_pages, extract_people_from_page

async def run_pagination_test(search_url, max_pages=None, expected_count=None):
    browser, page, p = await initialize_browser()
    assert browser is not None and page is not None
    print("Running run_pagination_test")
    try:
        await page.goto(search_url)
        print("Navigated to search_url ", page.url)
        if max_pages is not None:
            results = await navigate_all_pages(page, extract_people_from_page, max_pages=max_pages)
        else:
            results = await navigate_all_pages(page, extract_people_from_page)
        assert isinstance(results, list)
        if expected_count is not None:
            assert len(results) == expected_count, f"Expected {expected_count} results, got {len(results)}"
        for person in results:
            assert "name" in person
            assert "profile_url" in person
    finally:
        await browser.close()
        await p.stop()

@pytest.mark.asyncio
async def test_navigate_all_pages_3_pages():
    url = "https://www.linkedin.com/search/results/people/?keywords=engineer&origin=GLOBAL_SEARCH_HEADER"
    print("Starting test_navigate_all_pages_3_pages")
    await run_pagination_test(url, max_pages=3, expected_count=30)

@pytest.mark.asyncio
async def test_navigate_all_pages_anthropic():
    url = "https://www.linkedin.com/search/results/people/?company=Anthropic&network=%5B%22F%22%5D&origin=GLOBAL_SEARCH_HEADER"
    await run_pagination_test(url, expected_count=1)