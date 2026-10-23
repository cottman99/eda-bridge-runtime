from eda_bridge_runtime.source_symbols import describe_symbols


def test_symbol_description_reads_source_without_running_it(tmp_path):
    (tmp_path / "sdk.py").write_text(
        'raise RuntimeError("must not run")\n'
        "class Design:\n"
        "    def add_wire(self, points: list, *, width=1):\n"
        '        """Create the requested wire."""\n'
        "        pass\n",
        encoding="utf-8",
    )
    result = describe_symbols([tmp_path], "add_wire", version="2026")
    item = result["results"][0]
    assert "width=1" in item["signature"]
    assert item["line"] == 3
    assert item["source_kind"] == "sdk_source"
    assert item["runtime_verified"] is False
