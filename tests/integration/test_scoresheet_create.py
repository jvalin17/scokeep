"""Create Scoresheet games via API — schema + open-ended start phase."""

from httpx import AsyncClient


async def _auth_playground(client: AsyncClient, name: str = "Scoresheet Schema Room") -> dict:
    create_response = await client.post(
        "/api/playground",
        json={
            "name": name,
            "pin": "4242",
            "players": ["Maria", "Diego", "Priya"],
        },
    )
    playground = create_response.json()
    auth_response = await client.post(
        "/api/playground/auth",
        json={"name": name, "pin": "4242"},
    )
    cookies = {"scokeep_session": auth_response.cookies.get("scokeep_session")}
    return {**playground, "cookies": cookies}


class TestCreateScoresheetGame:
    async def test_create_scoresheet_returns_201_with_entry_phase(self, client: AsyncClient):
        pg = await _auth_playground(client)

        response = await client.post(
            "/api/game",
            json={
                "playground_id": pg["id"],
                "players": ["Maria", "Diego", "Priya"],
                "settings": {
                    "game_type": "scoresheet",
                    "winner": "lowest",
                    "show_totals": False,
                    "allow_negatives": True,
                    "label": "Declare night",
                    "appearance": "interactive",
                },
            },
            cookies=pg["cookies"],
        )

        assert response.status_code == 201, response.text
        body = response.json()
        assert body["settings"]["game_type"] == "scoresheet"
        assert body["settings"]["winner"] == "lowest"
        assert body["settings"]["show_totals"] is False
        assert body["settings"]["allow_negatives"] is True
        assert body["settings"]["label"] == "Declare night"
        assert body["phase"] == "entry"
        assert body["status"] == "active"
        # Open-ended: large cap, not Judgement 3×8
        assert body["total_rounds"] >= 100

    async def test_create_scoresheet_defaults(self, client: AsyncClient):
        pg = await _auth_playground(client, name="Scoresheet Defaults Room")

        response = await client.post(
            "/api/game",
            json={
                "playground_id": pg["id"],
                "players": ["Maria", "Diego"],
                "settings": {"game_type": "scoresheet"},
            },
            cookies=pg["cookies"],
        )

        assert response.status_code == 201, response.text
        body = response.json()
        assert body["settings"]["game_type"] == "scoresheet"
        assert body["settings"]["winner"] == "highest"
        assert body["settings"]["show_totals"] is True
        assert body["settings"]["allow_negatives"] is False
        assert body["phase"] == "entry"

    async def test_create_rejects_unknown_game_type(self, client: AsyncClient):
        pg = await _auth_playground(client, name="Bad Type Room")

        response = await client.post(
            "/api/game",
            json={
                "playground_id": pg["id"],
                "players": ["Maria", "Diego"],
                "settings": {"game_type": "rummy"},
            },
            cookies=pg["cookies"],
        )

        assert response.status_code == 422

    async def test_judgement_create_still_bidding(self, client: AsyncClient):
        pg = await _auth_playground(client, name="Judgement Still Room")

        response = await client.post(
            "/api/game",
            json={
                "playground_id": pg["id"],
                "players": ["Maria", "Diego"],
                "settings": {"game_type": "kachuful", "mode": "rookie", "num_sets": 1},
            },
            cookies=pg["cookies"],
        )

        assert response.status_code == 201, response.text
        body = response.json()
        assert body["settings"]["game_type"] == "kachuful"
        assert body["phase"] == "bidding"
        assert body["total_rounds"] == 8
