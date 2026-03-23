from pm_bot.adapters.polymarket.geoblock_client import GeoblockStatus, parse_geoblock_status


def test_parse_geoblock_status() -> None:
    status = parse_geoblock_status(
        {
            "blocked": True,
            "ip": "203.0.113.42",
            "country": "US",
            "region": "NY",
        }
    )

    assert status == GeoblockStatus(
        blocked=True,
        ip="203.0.113.42",
        country="US",
        region="NY",
    )
