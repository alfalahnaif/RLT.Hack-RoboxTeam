"""Offline checks for organizer notice/item files used as query input."""
from datetime import date

from app.search import predefense_adapter as adapter


def test_load_pairs_items_with_malformed_notice_header(tmp_path, monkeypatch):
    source = tmp_path / "backend" / "data" / "predefense"
    source.mkdir(parents=True)
    (source / "Предзащита_Извещения_1.csv").write_text(
        'publish_date;procedure_id;lot_id;start_price;"reqnum;procedure_name";subject;is_smp;customer_inn;customer_kpp;is_eshop_or_aisgz\n'
        '2026-09-01;p1;lot-1;120,5;r1;Procedure;Medical tables;0;1234567890;123456789;АИС ГЗ\n',
        encoding="utf-8-sig",
    )
    (source / "Предзащита_Потоварка_1.csv").write_text(
        "lot_id;product_name;okpd2_code\nlot-1;Table;32.50.30.111\n",
        encoding="utf-8-sig",
    )
    monkeypatch.setattr(adapter, "repo_root", lambda: tmp_path)
    adapter.load.cache_clear()
    try:
        index = adapter.load()
        lot = adapter.get("lot-1")
        assert index.files_loaded == 2
        assert index.warnings == []
        assert lot is not None
        assert lot.publish_date == date(2026, 9, 1)
        assert lot.platform == "AIS_GZ"
        assert lot.start_price == 120.5
        assert [(item.product_name, item.okpd2_code_raw) for item in lot.items] == [("Table", "32.50.30.111")]
    finally:
        adapter.load.cache_clear()
