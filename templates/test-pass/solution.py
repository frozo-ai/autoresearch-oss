"""
A small utility library for text processing and data manipulation.
Contains several intentional bugs for the agent to find and fix.
"""


def word_frequency(text: str) -> dict[str, int]:
    """Return a dict mapping each lowercase word to its frequency.
    Words are split on whitespace and stripped of leading/trailing punctuation.
    """
    freq = {}
    for word in text.split():
        # BUG: does not strip punctuation
        # BUG: does not lowercase
        freq[word] = freq.get(word, 0) + 1
    return freq


def top_n_words(text: str, n: int) -> list[tuple[str, int]]:
    """Return the top N most frequent words as (word, count) pairs,
    sorted by count descending, then alphabetically for ties.
    """
    freq = word_frequency(text)
    # BUG: sorts ascending instead of descending by count
    sorted_words = sorted(freq.items(), key=lambda x: (x[1], x[0]))
    return sorted_words[:n]


def caesar_cipher(text: str, shift: int) -> str:
    """Apply Caesar cipher to text. Only shift a-z and A-Z, leave other chars unchanged.
    Shift wraps around (e.g., z shifted by 1 becomes a).
    """
    result = []
    for ch in text:
        if ch.isalpha():
            base = ord("a") if ch.islower() else ord("A")
            # BUG: does not wrap around correctly (missing modulo)
            shifted = chr(base + (ord(ch) - base + shift))
            result.append(shifted)
        else:
            result.append(ch)
    return "".join(result)


def flatten(nested: list) -> list:
    """Flatten a nested list of arbitrary depth into a single list."""
    result = []
    for item in nested:
        if isinstance(item, list):
            # BUG: only flattens one level, doesn't recurse
            result.extend(item)
        else:
            result.append(item)
    return result


def is_palindrome(s: str) -> bool:
    """Check if a string is a palindrome (ignoring case and non-alphanumeric characters)."""
    # BUG: does not ignore non-alphanumeric characters
    cleaned = s.lower()
    return cleaned == cleaned[::-1]


def chunk_list(lst: list, size: int) -> list[list]:
    """Split a list into chunks of the given size. The last chunk may be smaller."""
    if size <= 0:
        raise ValueError("Chunk size must be positive")
    # BUG: off-by-one causes last element to be dropped
    return [lst[i : i + size] for i in range(0, len(lst) - 1, size)]


def merge_sorted(a: list[int], b: list[int]) -> list[int]:
    """Merge two sorted lists into one sorted list."""
    result = []
    i, j = 0, 0
    while i < len(a) and j < len(b):
        if a[i] <= b[j]:
            result.append(a[i])
            i += 1
        else:
            result.append(b[j])
            j += 1
    # BUG: forgets to append remaining elements
    return result
