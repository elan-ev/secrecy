#!/usr/bin/env python3

import sys
import string


def read_file(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()

def category(char):
    if char in string.ascii_letters:
        return 'letter'
    if char in string.digits:
        return 'digit'
    return 'punctuation'

# # Probability of a letter occuring ...
# class LetterProb:
#     # ... independent of context.
#     at_start = 0.0

#     # ... after a specific other one. (These are always lowercase.)
#     after_letter = {}

#     # ... after punctuation.
#     after_punct = 0.0

#     # ... after a digit.
#     after_digit = 0.0

#     # ... after a character not listed in any other `after_*`.
#     after_rest = 0.0

#     def __str__(self):
#         return (
#             f'\n   at_start:     {self.at_start}'
#             # f'\n   after_letter: {self.after_letter}' +
#             # f'\n   after_punct:  {self.after_punct:.5e}' +
#             # f'\n   after_digit:  {self.after_digit:.5e}' +
#             # f'\n   after_rest:   {self.after_rest:.5e}'
#             )



def main():
    bigrams = {}

    punctuation = r'!#$%&()+*,./:;<=>?@_{|}~-\^[]'
    allchars = "\0" + string.ascii_letters + string.digits + punctuation
    for c in allchars:
        bigrams[c] = {}
        for d in allchars:
            bigrams[c][d] = 0


    content = read_file(sys.argv[1])
    total_char_count = 0
    for line in content.splitlines():
        for i in range(len(line)):
            total_char_count += 1
            char = chr(line[i])
            prev = "\0" if i == 0 else chr(line[i - 1])
            if char.isupper() and prev.isupper():
                char = char.lower()
                prev = prev.lower()

            bigrams[prev][char] += 1


    total_at_start = sum(bigrams["\0"].values())

    # Count all chars following any punctuation
    total_after_punct = sum([sum(bigrams[punct].values()) for punct in punctuation])

    # Count all chars following any digit
    total_after_digit = sum([sum(bigrams[digit].values()) for digit in string.digits])

    total_after_letter = dict(
        [(letter, sum(bigrams[letter].values())) for letter in string.ascii_lowercase]
    )

    for letter in string.ascii_letters:
        # Calculate the total number of times this character appeared with a
        # specific previous character.
        num_first = bigrams["\0"][letter]
        num_prev_punct = sum([bigrams[prev][letter] for prev in punctuation])
        num_prev_digit = sum([bigrams[prev][letter] for prev in string.digits])

        p_at_start = num_first / total_at_start
        p_after_punct = num_prev_punct / total_after_punct
        p_after_digit = num_prev_digit / total_after_digit

        after_letters = ""
        for prev in string.ascii_lowercase:
            p = bigrams[prev][letter] / total_after_letter[prev]
            after_letters += f'"{prev}": {p:.4e}, '


        print(
            f'"{letter}": LetterProbability('
            + f'{p_at_start:.4e}, {p_after_digit:.4e}, {p_after_punct:.4e}, '
            + f'{{ {after_letters} }})'
        )


    # chars_sorted = [(k, v) for k, v in char_counts.items()]
    # chars_sorted.sort(key=lambda t: t[1], reverse=True)
    # for char, count in chars_sorted[:100]:
    #     print(f'{chr(char)} => {count}')

    # bigrams_sorted = [(k, v) for k, v in bigram_counts.items()]
    # bigrams_sorted.sort(key=lambda t: t[1], reverse=True)
    # for bigram, count in bigrams_sorted:
    #     print(f'{bigram} => {count}')



if __name__ == "__main__":
    main()
