import asyncio

import httpx

from vgc_analytics.app import create_app


def test_api_exposes_dataset_and_analysis(database):
    async def scenario():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=create_app(database)),
            base_url="http://test",
        ) as client:
            health = await client.get("/api/health")
            assert health.status_code == 200
            assert health.json()["tournaments"] == 2

            species = await client.get("/api/species")
            assert species.status_code == 200
            assert any(row["id"] == "basculegion" for row in species.json())
            assert [row["teams"] for row in species.json()] == sorted(
                (row["teams"] for row in species.json()), reverse=True
            )

            filtered_species = await client.get("/api/species?min_players=21")
            basculegion = next(row for row in filtered_species.json() if row["id"] == "basculegion")
            assert basculegion["teams"] == 2
            assert (await client.get("/api/species?min_players=25")).json() == []

            options = await client.get("/api/species/basculegion/options")
            assert options.status_code == 200
            assert options.json()["moves"][0]["value"] == "Protect"
            assert options.json()["items"][0]["value"] == "Basculegionite"

            images = await client.get("/static/pokemon-images.json")
            assert images.status_code == 200
            assert {row["id"] for row in species.json()} <= set(images.json())

            result = await client.post("/api/analyze", json={
                "own": {"contains": ["basculegion"]},
                "tournaments": {"min_players": 21},
                "mirrors": "exclude_own_core",
            })
            assert result.status_code == 200
            assert result.json()["record"] == {"wins": 1, "losses": 0, "ties": 1}
            assert result.json()["scope"] == {"tournaments": 1, "matches": 3}

            conditioned = await client.post("/api/analyze", json={
                "own": {
                    "contains": ["basculegion"],
                    "conditions": [{
                        "pokemon_id": "basculegion",
                        "moves": ["Protect"],
                        "item": "Basculegionite",
                        "ability": "Test Ability",
                    }],
                },
                "tournaments": {"min_players": 21},
            })
            assert conditioned.status_code == 200
            assert conditioned.json()["record"] == {"wins": 2, "losses": 1, "ties": 1}

            absent = await client.post("/api/analyze", json={
                "own": {"conditions": [{"pokemon_id": "basculegion", "item": "Missing Item"}]},
            })
            assert absent.status_code == 200
            assert absent.json()["sample"]["matches"] == 0

            team_search = await client.post("/api/teams/search", json={
                "mode": "basic",
                "team": {"contains": ["basculegion"]},
                "tournaments": {"min_players": 21},
            })
            assert team_search.status_code == 200
            assert team_search.json()["total"] == 2
            assert all(len(row["pokemon"]) == 6 for row in team_search.json()["results"])

    asyncio.run(scenario())


def test_react_app_is_served_for_both_routes(database):
    async def scenario():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=create_app(database)),
            base_url="http://test",
        ) as client:
            index = await client.get("/")
            teams = await client.get("/teams")

            assert index.status_code == 200
            assert teams.status_code == 200
            assert index.text == teams.text
            assert '<html lang="en">' in index.text
            assert '<div id="root"></div>' in index.text
            assert 'type="module"' in index.text
            assert "teracrist" not in index.text.lower()

    asyncio.run(scenario())


def test_react_build_assets_are_exposed(database):
    async def scenario():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=create_app(database)),
            base_url="http://test",
        ) as client:
            html = (await client.get("/")).text
            asset_paths = [
                value
                for value in html.replace('"', "'").split("'")
                if value.startswith("/static/assets/")
            ]

            assert asset_paths
            for path in asset_paths:
                response = await client.get(path)
                assert response.status_code == 200
                assert response.content

            images = await client.get("/static/pokemon-images.json")
            assert images.status_code == 200

    asyncio.run(scenario())
