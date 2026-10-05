"""Natural sort: page_2 comes before page_10."""

from backend.core.sort import natural_key


def test_numeric_names_sort_numerically():
    names = ["page_10.jpg", "page_2.jpg", "page_1.jpg"]
    assert sorted(names, key=natural_key) == [
        "page_1.jpg",
        "page_2.jpg",
        "page_10.jpg",
    ]


def test_mixed_names_sort_stably():
    names = ["cover.jpg", "page_2.jpg", "back.jpg", "page_10.jpg"]
    assert sorted(names, key=natural_key) == [
        "back.jpg",
        "cover.jpg",
        "page_2.jpg",
        "page_10.jpg",
    ]


def test_names_without_digits_keep_alpha_order():
    names = ["b.jpg", "a.jpg"]
    assert sorted(names, key=natural_key) == ["a.jpg", "b.jpg"]
