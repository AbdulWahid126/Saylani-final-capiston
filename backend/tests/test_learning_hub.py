"""Focused unit and integration tests for TASK-015: Beginner Learning Hub & Curated Resource Discovery.

Covers:
1. Curriculum category retrieval and ordering.
2. Lesson summaries listing, category filtering, difficulty filtering, and text search.
3. Individual lesson retrieval by ID and by slug, with 404 handling.
4. Curated resources multi-attribute filtering (topic, difficulty, cost, type, search).
5. Curated resources pagination and invalid query parameters validation (HTTP 422).
6. Single resource retrieval and 404 handling.
7. Authentication enforcement (HTTP 401 without valid JWT).
8. URL validity, publisher hygiene, and data integrity of all curated resources.
9. Empty search result handling.
10. Deterministic mathematical accuracy in hypothetical risk calculations.
"""

from typing import Any

import pytest
from httpx import AsyncClient

from app.learning_data.content import CURATED_RESOURCES, CURRICULUM_LESSONS
from app.schemas.learning import CostClassification, DifficultyLevel, ResourceType
from app.services.learning_service import LearningService


async def create_auth_user(client: AsyncClient, email: str) -> dict[str, Any]:
    """Helper to register and log in a test user, returning auth headers and user id."""
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "SecurePassword123!"},
    )
    assert reg.status_code == 201
    user_id = reg.json()["id"]

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "SecurePassword123!"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    return {
        "user_id": user_id,
        "token": token,
        "headers": {"Authorization": f"Bearer {token}"},
    }


# ==============================================================================
# 1. CURRICULUM CATEGORY TESTS
# ==============================================================================


def test_service_curriculum_categories():
    """Unit test: verify LearningService returns all 6 curriculum categories with correct metadata."""
    service = LearningService()
    categories = service.get_categories()

    assert len(categories) == 6
    expected_ids = [
        "forex-fundamentals",
        "risk-management",
        "technical-analysis",
        "smc",
        "ict",
        "psychology",
    ]
    actual_ids = [c.id for c in categories]
    assert actual_ids == expected_ids

    # Verify orders are strictly sequential
    for i, cat in enumerate(categories):
        assert cat.order == i + 1
        assert cat.lesson_count > 0
        assert cat.title
        assert cat.short_description
        assert cat.icon


@pytest.mark.asyncio
async def test_api_curriculum_categories_authenticated(async_client: AsyncClient):
    """Integration test: GET /api/v1/learning/categories returns 200 with all categories."""
    user = await create_auth_user(async_client, "learning_user_cat@example.com")
    resp = await async_client.get("/api/v1/learning/categories", headers=user["headers"])
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 6
    assert data[0]["id"] == "forex-fundamentals"
    assert data[1]["id"] == "risk-management"


# ==============================================================================
# 2. LESSON RETRIEVAL & FILTERING TESTS
# ==============================================================================


def test_service_lessons_filtering():
    """Unit test: verify lesson filtering by category, difficulty, and search keyword."""
    service = LearningService()

    # Total lessons
    all_lessons = service.get_lessons()
    assert len(all_lessons) == 14

    # Filter by category
    risk_lessons = service.get_lessons(category_id="risk-management")
    assert len(risk_lessons) == 3
    assert all(lesson.category_id == "risk-management" for lesson in risk_lessons)

    # Filter by difficulty
    beg_lessons = service.get_lessons(difficulty=DifficultyLevel.BEGINNER)
    assert len(beg_lessons) > 0
    assert all(lesson.difficulty == DifficultyLevel.BEGINNER for lesson in beg_lessons)

    adv_lessons = service.get_lessons(difficulty=DifficultyLevel.ADVANCED)
    assert len(adv_lessons) == 2
    assert all(lesson.difficulty == DifficultyLevel.ADVANCED for lesson in adv_lessons)

    # Search keyword
    pip_lessons = service.get_lessons(search="spread")
    assert len(pip_lessons) >= 1
    assert any(
        "spread" in lesson.title.lower() or "spread" in lesson.short_description.lower()
        for lesson in pip_lessons
    )

    # Case-insensitivity check
    ict_search = service.get_lessons(search="ICT")
    assert len(ict_search) >= 2


@pytest.mark.asyncio
async def test_api_lessons_list_and_filters(async_client: AsyncClient):
    """Integration test: GET /api/v1/learning/lessons with query filters."""
    user = await create_auth_user(async_client, "learning_user_lessons@example.com")

    # List all
    res_all = await async_client.get("/api/v1/learning/lessons", headers=user["headers"])
    assert res_all.status_code == 200
    data_all = res_all.json()
    assert data_all["total"] == 14
    assert len(data_all["items"]) == 14

    # Filter by category
    res_smc = await async_client.get(
        "/api/v1/learning/lessons",
        params={"category_id": "smc"},
        headers=user["headers"],
    )
    assert res_smc.status_code == 200
    data_smc = res_smc.json()
    assert data_smc["total"] == 2
    assert all(item["category_id"] == "smc" for item in data_smc["items"])

    # Search filter
    res_search = await async_client.get(
        "/api/v1/learning/lessons",
        params={"search": "drawdown"},
        headers=user["headers"],
    )
    assert res_search.status_code == 200
    data_search = res_search.json()
    assert data_search["total"] >= 1
    assert any("drawdown" in item["slug"] for item in data_search["items"])


@pytest.mark.asyncio
async def test_api_lesson_detail_by_id_and_slug(async_client: AsyncClient):
    """Integration test: GET /api/v1/learning/lessons/{id} by ID and by slug."""
    user = await create_auth_user(async_client, "learning_user_detail@example.com")

    # Retrieve by ID
    res_id = await async_client.get(
        "/api/v1/learning/lessons/risk-deterministic-position-sizing",
        headers=user["headers"],
    )
    assert res_id.status_code == 200
    data_id = res_id.json()
    assert data_id["id"] == "risk-deterministic-position-sizing"
    assert data_id["slug"] == "deterministic-position-sizing"
    assert len(data_id["learning_objectives"]) >= 2
    assert len(data_id["key_terms"]) >= 1
    assert data_id["hypothetical_example"] is not None
    assert "Lot Size" in data_id["hypothetical_example"]["calculation"]
    assert len(data_id["common_mistakes"]) >= 2
    assert data_id["recap"]
    assert "EDUCATIONAL NOTICE" in data_id["disclaimer"]

    # Retrieve by slug
    res_slug = await async_client.get(
        "/api/v1/learning/lessons/deterministic-position-sizing",
        headers=user["headers"],
    )
    assert res_slug.status_code == 200
    assert res_slug.json()["id"] == "risk-deterministic-position-sizing"


@pytest.mark.asyncio
async def test_api_lesson_not_found(async_client: AsyncClient):
    """Integration test: GET /api/v1/learning/lessons/{invalid} returns 404."""
    user = await create_auth_user(async_client, "learning_user_404@example.com")
    res = await async_client.get(
        "/api/v1/learning/lessons/nonexistent-lesson-slug-xyz",
        headers=user["headers"],
    )
    assert res.status_code == 404
    body = res.json()
    assert body["error"]["code"] == "NOT_FOUND"
    assert "not found" in body["error"]["message"].lower()


# ==============================================================================
# 3. CURATED RESOURCES TESTS
# ==============================================================================


def test_service_curated_resources_filtering():
    """Unit test: verify resource filtering across topic, difficulty, cost, and type."""
    service = LearningService()

    # All resources
    items, total, pages = service.get_resources(page=1, page_size=20)
    assert total == 14
    assert len(items) == 14
    assert pages == 1

    # Filter by cost: Free vs Paid
    free_items, free_total, _ = service.get_resources(cost=CostClassification.FREE)
    assert free_total == 11
    assert all(r.cost == CostClassification.FREE for r in free_items)

    paid_items, paid_total, _ = service.get_resources(cost=CostClassification.PAID)
    assert paid_total == 3
    assert all(r.cost == CostClassification.PAID for r in paid_items)

    # Filter by resource type: Books
    books, book_total, _ = service.get_resources(resource_type=ResourceType.BOOK)
    assert book_total == 3
    assert all(r.resource_type == ResourceType.BOOK for r in books)
    book_publishers = [b.publisher for b in books]
    assert any("Mark Douglas" in p for p in book_publishers)
    assert any("Brett N. Steenbarger" in p for p in book_publishers)
    assert any("John J. Murphy" in p for p in book_publishers)

    # Filter by topic: Risk Management
    risk_res, risk_tot, _ = service.get_resources(topic="Risk Management")
    assert risk_tot >= 2

    # Search by publisher keyword
    cftc_res, cftc_tot, _ = service.get_resources(search="CFTC")
    assert cftc_tot >= 1
    assert "CFTC" in cftc_res[0].publisher


@pytest.mark.asyncio
async def test_api_curated_resources_pagination(async_client: AsyncClient):
    """Integration test: GET /api/v1/learning/resources pagination with page and page_size."""
    user = await create_auth_user(async_client, "learning_user_res_page@example.com")

    # Page 1, size 5
    res_p1 = await async_client.get(
        "/api/v1/learning/resources",
        params={"page": 1, "page_size": 5},
        headers=user["headers"],
    )
    assert res_p1.status_code == 200
    p1 = res_p1.json()
    assert p1["page"] == 1
    assert p1["page_size"] == 5
    assert p1["total"] == 14
    assert p1["total_pages"] == 3
    assert len(p1["items"]) == 5

    # Page 2, size 5
    res_p2 = await async_client.get(
        "/api/v1/learning/resources",
        params={"page": 2, "page_size": 5},
        headers=user["headers"],
    )
    assert res_p2.status_code == 200
    p2 = res_p2.json()
    assert p2["page"] == 2
    assert len(p2["items"]) == 5

    # Ensure items on page 1 and page 2 are distinct
    p1_ids = {r["id"] for r in p1["items"]}
    p2_ids = {r["id"] for r in p2["items"]}
    assert p1_ids.isdisjoint(p2_ids)

    # Page 3, size 5 (remaining 4 items)
    res_p3 = await async_client.get(
        "/api/v1/learning/resources",
        params={"page": 3, "page_size": 5},
        headers=user["headers"],
    )
    assert res_p3.status_code == 200
    p3 = res_p3.json()
    assert len(p3["items"]) == 4


@pytest.mark.asyncio
async def test_api_curated_resources_invalid_query_params(async_client: AsyncClient):
    """Integration test: verify query parameter validation rejects invalid page and page_size with 422."""
    user = await create_auth_user(async_client, "learning_user_val_err@example.com")

    # page < 1
    res_p0 = await async_client.get(
        "/api/v1/learning/resources",
        params={"page": 0, "page_size": 10},
        headers=user["headers"],
    )
    assert res_p0.status_code == 422

    # page_size < 1
    res_s0 = await async_client.get(
        "/api/v1/learning/resources",
        params={"page": 1, "page_size": 0},
        headers=user["headers"],
    )
    assert res_s0.status_code == 422

    # page_size > 100
    res_s101 = await async_client.get(
        "/api/v1/learning/resources",
        params={"page": 1, "page_size": 101},
        headers=user["headers"],
    )
    assert res_s101.status_code == 422


@pytest.mark.asyncio
async def test_api_single_resource_and_404(async_client: AsyncClient):
    """Integration test: GET /api/v1/learning/resources/{id} and 404 on missing resource."""
    user = await create_auth_user(async_client, "learning_user_res_detail@example.com")

    # Valid resource
    res = await async_client.get(
        "/api/v1/learning/resources/cftc-forex-basics",
        headers=user["headers"],
    )
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == "cftc-forex-basics"
    assert "Commodity Futures Trading Commission" in data["publisher"]
    assert data["verified"] is True
    assert data["badge"] == "[VERIFIED RESOURCE]"

    # Non-existent resource
    res_404 = await async_client.get(
        "/api/v1/learning/resources/unknown-resource-id-999",
        headers=user["headers"],
    )
    assert res_404.status_code == 404
    assert res_404.json()["error"]["code"] == "NOT_FOUND"


# ==============================================================================
# 4. AUTHENTICATION & SECURITY ENFORCEMENT TESTS
# ==============================================================================


@pytest.mark.asyncio
async def test_learning_endpoints_require_authentication(async_client: AsyncClient):
    """Verify that all learning endpoints reject unauthenticated requests with HTTP 401."""
    # 1. Categories
    res_cat = await async_client.get("/api/v1/learning/categories")
    assert res_cat.status_code == 401

    # 2. Lessons list
    res_les = await async_client.get("/api/v1/learning/lessons")
    assert res_les.status_code == 401

    # 3. Lesson detail
    res_ld = await async_client.get("/api/v1/learning/lessons/currency-pairs-pips-spreads")
    assert res_ld.status_code == 401

    # 4. Resources list
    res_res = await async_client.get("/api/v1/learning/resources")
    assert res_res.status_code == 401

    # 5. Resource detail
    res_rd = await async_client.get("/api/v1/learning/resources/cftc-forex-basics")
    assert res_rd.status_code == 401


# ==============================================================================
# 5. RESOURCE DATA INTEGRITY & URL VERIFICATION TESTS
# ==============================================================================


def test_curated_resources_url_and_data_integrity():
    """Verify that every curated resource has a valid HTTPS URL, valid publisher, and no referral links."""
    assert len(CURATED_RESOURCES) >= 12

    recognized_domains = (
        "cftc.gov",
        "bis.org",
        "babypips.com",
        "investopedia.com",
        "penguinrandomhouse.com",
        "wiley.com",
        "metatrader5.com",
        "cmegroup.com",
        "newyorkfed.org",
    )

    for resource in CURATED_RESOURCES:
        url_str = str(resource.url)
        # Must be HTTPS
        assert url_str.startswith("https://"), f"URL {url_str} must use secure HTTPS"

        # Must be from a recognized educational or institutional domain
        has_valid_domain = any(domain in url_str for domain in recognized_domains)
        assert has_valid_domain, f"URL {url_str} is not from a recognized reputable domain"

        # No referral parameters
        assert "ref=" not in url_str
        assert "aff=" not in url_str
        assert "tag=" not in url_str

        # Required fields must not be empty
        assert resource.id.strip()
        assert resource.title.strip()
        assert resource.publisher.strip()
        assert resource.description.strip()
        assert resource.verified is True
        assert resource.last_reviewed


# ==============================================================================
# 6. EMPTY CATALOG SEARCH RESULTS TESTS
# ==============================================================================


@pytest.mark.asyncio
async def test_empty_catalog_search_results(async_client: AsyncClient):
    """Verify searching for nonexistent terms returns empty array and total=0 without errors."""
    user = await create_auth_user(async_client, "learning_user_empty_res@example.com")

    # Search lessons
    res_l = await async_client.get(
        "/api/v1/learning/lessons",
        params={"search": "completelynonexistenttradingword12345"},
        headers=user["headers"],
    )
    assert res_l.status_code == 200
    assert res_l.json()["total"] == 0
    assert res_l.json()["items"] == []

    # Search resources
    res_r = await async_client.get(
        "/api/v1/learning/resources",
        params={"search": "completelynonexistentpublisher99999"},
        headers=user["headers"],
    )
    assert res_r.status_code == 200
    body = res_r.json()
    assert body["total"] == 0
    assert body["total_pages"] == 0
    assert body["items"] == []


# ==============================================================================
# 7. DETERMINISTIC MATHEMATICAL ACCURACY TESTS
# ==============================================================================


def test_deterministic_hypothetical_risk_calculations():
    """Verify deterministic math in the position sizing and risk lessons."""
    # Find position sizing lesson
    pos_lesson = next(
        (
            lesson
            for lesson in CURRICULUM_LESSONS
            if lesson.id == "risk-deterministic-position-sizing"
        ),
        None,
    )
    assert pos_lesson is not None
    example = pos_lesson.hypothetical_example
    assert example is not None

    # Deterministic check: $25,000 balance * 1% risk = $250 risk.
    # 25 pips * $10/pip = $250. Lot size = $250 / $250 = 1.00 lot.
    assert "1.00 standard lot" in example.calculation
    assert "$250.00" in example.calculation
    assert example.badge == "[HYPOTHETICAL EXAMPLE]"

    # Find spread calculation lesson
    spread_lesson = next(
        (lesson for lesson in CURRICULUM_LESSONS if lesson.id == "fx-pairs-pips-spreads"),
        None,
    )
    assert spread_lesson is not None
    assert spread_lesson.hypothetical_example is not None
    assert "2.0 pips" in spread_lesson.hypothetical_example.calculation
    assert "$20.00" in spread_lesson.hypothetical_example.calculation
