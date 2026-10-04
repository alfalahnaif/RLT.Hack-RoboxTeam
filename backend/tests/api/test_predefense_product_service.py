"""The analysis API can read local pre-defense lots without importing them into history."""
from app.api import product_service
from app.search import predefense_adapter as adapter


def test_procurement_uses_local_notice_before_historical_database(monkeypatch):
    lot = adapter.PredefenseLot(
        "lot-1",
        {
            "publish_date": "2026-09-01",
            "subject": "Medical tables",
            "start_price": "120,5",
            "customer_inn": "1234567890",
            "is_eshop_or_aisgz": "АИС ГЗ",
        },
        [adapter.PredefenseItem(1, "Table", "32.50.30.111")],
    )
    monkeypatch.setattr(adapter, "get", lambda lot_id: lot if lot_id == "lot-1" else None)
    monkeypatch.setattr(
        adapter,
        "validate_category",
        lambda conn, name, code: adapter.ItemCategory(code, "SUPPLIED_ALIGNED", "official category"),
    )

    class NoHistoricalDatabase:
        def execute(self, *args, **kwargs):
            raise AssertionError("pre-defense lookup must not query historical procurement tables")

    response = product_service.procurement(NoHistoricalDatabase(), "lot-1")
    assert response.source == "PREDEFENSE_FILE"
    assert response.platform == "AIS_GZ"
    assert response.start_price == 120.5
    assert response.items[0].okpd2_status == "SUPPLIED_ALIGNED"
