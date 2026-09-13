class Verhoeff:
    """
    Implementation of Verhoeff Algorithm for 12-digit Indian Aadhaar number validation.
    Used for UID checksum validation and tampering check.
    """

    # Multiplication table d
    d = [
        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
        [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
        [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
        [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
        [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
        [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
        [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
        [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
        [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
        [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]
    ]

    # Permutation table p
    p = [
        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
        [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
        [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
        [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
        [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
        [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
        [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
        [7, 0, 4, 6, 9, 1, 3, 2, 5, 8]
    ]

    # Inverse table inv
    inv = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]

    @classmethod
    def validate(cls, number_str: str) -> bool:
        """
        Validates a 12-digit Aadhaar number string using Verhoeff algorithm.
        Returns True if checksum is valid.
        """
        clean_num = "".join(filter(str.isdigit, str(number_str)))
        if len(clean_num) != 12:
            return False

        c = 0
        inverted_num = list(map(int, reversed(clean_num)))

        for i, item in enumerate(inverted_num):
            c = cls.d[c][cls.p[i % 8][item]]

        return c == 0
