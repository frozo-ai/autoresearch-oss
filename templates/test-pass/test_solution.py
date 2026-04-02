"""Test suite for solution.py — 10 tests covering all functions."""

import pytest
from solution import (
    word_frequency,
    top_n_words,
    caesar_cipher,
    flatten,
    is_palindrome,
    chunk_list,
    merge_sorted,
)


def test_word_frequency_basic():
    text = "the cat sat on the mat"
    result = word_frequency(text)
    assert result == {"the": 2, "cat": 1, "sat": 1, "on": 1, "mat": 1}


def test_word_frequency_punctuation_and_case():
    text = "Hello, hello! HELLO."
    result = word_frequency(text)
    assert result == {"hello": 3}


def test_top_n_words():
    text = "apple banana apple cherry banana apple"
    result = top_n_words(text, 2)
    assert result == [("apple", 3), ("banana", 2)]


def test_caesar_cipher_basic():
    assert caesar_cipher("abc", 3) == "def"
    assert caesar_cipher("XYZ", 3) == "ABC"


def test_caesar_cipher_wrap():
    assert caesar_cipher("xyz", 3) == "abc"
    assert caesar_cipher("Hello, World!", 13) == "Uryyb, Jbeyq!"


def test_flatten_deep():
    nested = [1, [2, [3, [4, 5]], 6], 7]
    assert flatten(nested) == [1, 2, 3, 4, 5, 6, 7]


def test_is_palindrome():
    assert is_palindrome("A man, a plan, a canal: Panama") is True
    assert is_palindrome("race a car") is False


def test_chunk_list():
    assert chunk_list([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]
    assert chunk_list([1, 2, 3], 3) == [[1, 2, 3]]
    assert chunk_list([1], 5) == [[1]]


def test_chunk_list_error():
    with pytest.raises(ValueError):
        chunk_list([1, 2], 0)


def test_merge_sorted():
    assert merge_sorted([1, 3, 5], [2, 4, 6]) == [1, 2, 3, 4, 5, 6]
    assert merge_sorted([], [1, 2, 3]) == [1, 2, 3]
    assert merge_sorted([1, 2], []) == [1, 2]
