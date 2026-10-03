from bimouia.ui import chunk_lines


def test_chunk_lines_respecte_la_limite():
    lines = ["a" * 10] * 5
    chunks = chunk_lines(lines, 25)
    assert all(len(c) <= 25 for c in chunks)
    assert "\n".join(chunks).count("a") == 50


def test_chunk_lines_vide():
    assert chunk_lines([], 1024) == []
