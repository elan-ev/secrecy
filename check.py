#!/usr/bin/env python3

from typing import Dict, List, Optional
import math
import os
import re
import string
import subprocess
import sys



# ----- Utilities --------------------------------------------------------------------------------

def read_file(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()

def eprint(msg: str):
    print(msg, file=sys.stderr)

class Context:
    """Utility type to keep track of error state and emit errors"""

    errored = False
    commit: Optional[str] = None

    def error(self, path: str, msg: str):
        self.errored = True
        print(f'ERROR in {path}{self.commit_output()} => {msg}', file=sys.stderr)

    def line_error(self, path: str, line: int, msg: str):
        self.errored = True
        print(f'ERROR in {path}:{line}{self.commit_output()} => {msg}', file=sys.stderr)

    def commit_output(self):
        if self.commit is not None:
            return f' (at {self.commit})';
        else:
            return ""


# ----- Entropy Utilities ------------------------------------------------------------------------

PASSWORD_CHARS = r'!#$%&()+*,./:;<=>?@_{|}~-\^[]' + string.ascii_letters + string.digits

class TruncatedProbs:
    """A mapping from string to probability, which is truncated. All remaining
    elements divide the remaining probability evenly.
    """

    probs: Dict[str, float] = {}
    rest = 0.0

    def __init__(self, probs: Dict[str, float]):
        self.probs = probs
        self.rest = (1.0 - sum(probs.values())) / (len(PASSWORD_CHARS) - len(probs))

    def get(self, prev: str):
        if prev in self.probs:
            return self.probs[prev]
        return self.rest


class LetterProbability:
    """Probabilities of a letter occurring in a specific context."""

    at_start = 0.0
    after_digit = 0.0
    after_punct = 0.0
    after_letter: TruncatedProbs

    def __init__(
        self,
        at_start: float,
        after_digit: float,
        after_punct: float,
        after_letter: Dict[str, float]
    ):
        self.at_start = at_start
        self.after_digit = after_digit
        self.after_punct = after_punct
        self.after_letter = TruncatedProbs(after_letter)



class Probabilities:
    """Probabilities of any character occuring in any context"""

    letters: Dict[str, LetterProbability] = {}

    def prob(self, prev: Optional[str], char: str) -> float:
        if char in string.ascii_letters:
            probs = self.letters[char]
            if prev is None:
                return probs.at_start
            if prev in string.ascii_letters:
                if prev.isupper() and char.isupper():
                    return self.letters[char.lower()].after_letter.get(prev.lower())
                return probs.after_letter.get(prev.lower())

            if prev in string.digits:
                return probs.after_digit
            return probs.after_punct


        else:
            raise

PROBS = Probabilities()
PROBS.letters = {
    "a": LetterProbability(5.1670e-02, 8.3916e-03, 5.0477e-02, { "a": 8.3089e-03, "b": 1.0205e-01, "c": 1.8566e-01, "d": 1.0117e-01, "e": 2.8784e-02, "f": 5.6009e-02, "g": 4.9973e-02, "h": 8.2230e-02, "i": 2.4837e-02, "j": 2.4482e-02, "k": 1.5873e-02, "l": 1.6755e-01, "m": 1.0629e-01, "n": 6.8962e-02, "o": 2.7389e-02, "p": 1.0664e-01, "q": 3.3058e-02, "r": 5.4054e-02, "s": 9.0698e-03, "t": 1.4048e-01, "u": 7.3992e-03, "v": 2.6058e-02, "w": 2.5785e-02, "x": 1.2658e-02, "y": 1.1792e-03, "z": 4.3409e-01 }),
    "b": LetterProbability(8.1691e-03, 5.5944e-03, 1.9418e-02, { "a": 2.2474e-02, "b": 3.1435e-02, "c": 2.4673e-04, "d": 2.4457e-02, "e": 5.2384e-03, "f": 2.1269e-03, "g": 2.1265e-03, "h": 5.0690e-03, "i": 2.8790e-02, "j": 3.7665e-03, "k": 5.1587e-02, "l": 1.9225e-03, "m": 5.4435e-02, "n": 4.8225e-04, "o": 2.4899e-03, "p": 7.2913e-04, "q": 1.2397e-02, "r": 8.1653e-04, "s": 5.5304e-04, "t": 5.6790e-04, "u": 6.1783e-02, "v": 3.0656e-03, "w": 3.7369e-04, "x": 1.1507e-03, "y": 8.2547e-03, "z": 2.2727e-03 }),
    "c": LetterProbability(4.6053e-02, 1.9580e-03, 4.8749e-02, { "a": 5.5630e-02, "b": 9.1116e-04, "c": 1.7641e-02, "d": 4.1806e-03, "e": 4.9846e-02, "f": 3.5448e-04, "g": 1.3291e-03, "h": 9.2368e-02, "i": 9.1698e-02, "j": 1.1299e-02, "k": 6.9444e-03, "l": 1.3310e-03, "m": 1.1732e-03, "n": 9.8380e-02, "o": 1.1333e-02, "p": 2.5520e-03, "q": 1.2397e-02, "r": 6.6139e-02, "s": 2.5993e-02, "t": 4.5219e-02, "u": 1.6648e-02, "v": 3.0656e-04, "w": 1.4948e-03, "x": 2.6122e-01, "y": 5.8962e-04, "z": 0.0000e+00 }),
    "d": LetterProbability(3.0532e-02, 4.1958e-03, 3.0423e-02, { "a": 6.6234e-02, "b": 4.5558e-04, "c": 3.7010e-04, "d": 6.2709e-03, "e": 3.9585e-02, "f": 1.0635e-03, "g": 1.8607e-03, "h": 2.2529e-03, "i": 5.5088e-02, "j": 1.8832e-03, "k": 2.9762e-03, "l": 1.8042e-02, "m": 5.8658e-03, "n": 6.4911e-02, "o": 2.8419e-02, "p": 6.0153e-03, "q": 8.2645e-03, "r": 2.7680e-02, "s": 8.8486e-04, "t": 7.0987e-04, "u": 3.9031e-02, "v": 1.2262e-03, "w": 0.0000e+00, "x": 4.7181e-02, "y": 5.8962e-04, "z": 6.8182e-03 }),
    "e": LetterProbability(4.8708e-02, 3.6364e-03, 3.5107e-02, { "a": 1.0446e-02, "b": 2.2733e-01, "c": 1.8529e-01, "d": 2.6777e-01, "e": 3.2943e-03, "f": 4.7146e-02, "g": 2.1903e-01, "h": 1.8389e-01, "i": 6.4713e-02, "j": 3.8418e-01, "k": 2.0337e-01, "l": 2.7551e-01, "m": 2.6115e-01, "n": 2.1605e-02, "o": 4.2930e-04, "p": 1.4692e-01, "q": 2.4793e-02, "r": 1.8062e-01, "s": 2.1347e-01, "t": 1.4020e-01, "u": 2.7007e-02, "v": 3.5254e-01, "w": 3.8864e-02, "x": 4.6030e-03, "y": 5.2476e-02, "z": 9.5455e-02 }),
    "f": LetterProbability(2.6345e-02, 1.4825e-02, 3.6062e-02, { "a": 4.4314e-03, "b": 5.0114e-03, "c": 2.0972e-03, "d": 3.1355e-03, "e": 2.4140e-02, "f": 2.9068e-02, "g": 3.8809e-02, "h": 1.4081e-03, "i": 6.1877e-03, "j": 5.6497e-03, "k": 1.9742e-01, "l": 2.9577e-04, "m": 1.4078e-03, "n": 2.9128e-02, "o": 1.3480e-02, "p": 2.5520e-03, "q": 1.2397e-02, "r": 3.2661e-04, "s": 4.4243e-04, "t": 2.8395e-04, "u": 3.6996e-03, "v": 1.8394e-03, "w": 3.7369e-04, "x": 2.3015e-03, "y": 1.7689e-03, "z": 4.5455e-03 }),
    "g": LetterProbability(1.2254e-03, 1.1189e-03, 1.4188e-02, { "a": 5.0012e-02, "b": 4.5558e-04, "c": 1.4804e-03, "d": 4.5987e-03, "e": 7.8846e-03, "f": 3.1904e-03, "g": 1.0367e-02, "h": 1.4081e-03, "i": 3.3860e-02, "j": 1.3183e-02, "k": 1.3889e-02, "l": 4.4366e-04, "m": 5.3965e-03, "n": 1.2693e-01, "o": 1.5626e-02, "p": 2.9165e-03, "q": 8.2645e-03, "r": 6.9650e-02, "s": 7.7425e-04, "t": 7.0987e-05, "u": 2.4972e-02, "v": 5.2115e-03, "w": 1.8685e-03, "x": 2.3015e-03, "y": 2.9481e-03, "z": 4.5455e-03 }),
    "h": LetterProbability(2.5835e-02, 4.7552e-03, 2.0009e-02, { "a": 6.3306e-04, "b": 1.3667e-03, "c": 1.7160e-01, "d": 1.6722e-03, "e": 3.2403e-04, "f": 7.7987e-03, "g": 1.4088e-02, "h": 5.6322e-04, "i": 2.5782e-04, "j": 5.6497e-03, "k": 2.9762e-03, "l": 3.2535e-03, "m": 1.0793e-02, "n": 2.8935e-04, "o": 1.0303e-03, "p": 4.1378e-02, "q": 8.2645e-03, "r": 4.8992e-04, "s": 3.4841e-02, "t": 6.0552e-02, "u": 0.0000e+00, "v": 8.2771e-03, "w": 1.8685e-03, "x": 1.1507e-03, "y": 1.7689e-03, "z": 8.4091e-02 }),
    "i": LetterProbability(1.7461e-02, 5.3147e-03, 2.4193e-02, { "a": 4.9537e-02, "b": 1.8223e-02, "c": 4.0711e-03, "d": 1.7684e-01, "e": 1.8902e-03, "f": 2.1411e-01, "g": 7.9745e-02, "h": 1.3208e-01, "i": 6.0158e-04, "j": 9.4162e-03, "k": 5.0595e-02, "l": 8.5773e-02, "m": 1.4993e-01, "n": 2.2666e-02, "o": 1.5712e-02, "p": 5.9789e-02, "q": 1.2397e-02, "r": 1.0386e-01, "s": 3.3072e-02, "t": 1.5099e-01, "u": 6.4928e-02, "v": 3.1576e-01, "w": 2.4327e-01, "x": 2.7618e-02, "y": 2.3585e-03, "z": 3.6364e-02 }),
    "j": LetterProbability(1.2254e-03, 6.7133e-03, 8.5039e-03, { "a": 0.0000e+00, "b": 6.3781e-03, "c": 3.7010e-04, "d": 6.2709e-04, "e": 1.0801e-04, "f": 3.5448e-04, "g": 2.6582e-04, "h": 1.1264e-03, "i": 4.2970e-04, "j": 9.4162e-03, "k": 9.9206e-04, "l": 2.9577e-04, "m": 7.0389e-04, "n": 7.7160e-04, "o": 1.5025e-02, "p": 7.2913e-04, "q": 8.2645e-03, "r": 1.6331e-04, "s": 2.2121e-04, "t": 4.2592e-04, "u": 5.5494e-04, "v": 2.1459e-03, "w": 7.4738e-04, "x": 1.1507e-03, "y": 2.3585e-03, "z": 9.0909e-03 }),
    "k": LetterProbability(1.1233e-03, 4.7552e-03, 5.9573e-03, { "a": 3.1653e-04, "b": 0.0000e+00, "c": 2.8868e-02, "d": 4.1806e-04, "e": 6.4805e-04, "f": 7.0897e-04, "g": 1.3291e-03, "h": 5.6322e-04, "i": 5.1564e-04, "j": 1.6949e-02, "k": 1.9841e-03, "l": 1.3310e-03, "m": 2.3463e-03, "n": 2.2184e-03, "o": 5.9243e-03, "p": 3.4634e-03, "q": 1.2397e-02, "r": 3.8540e-02, "s": 2.3228e-03, "t": 0.0000e+00, "u": 0.0000e+00, "v": 9.1968e-04, "w": 3.7369e-04, "x": 4.6030e-03, "y": 1.1792e-03, "z": 6.8182e-03 }),
    "l": LetterProbability(1.0211e-02, 3.3566e-03, 1.1096e-02, { "a": 4.4473e-02, "b": 1.9317e-01, "c": 2.6770e-02, "d": 6.5426e-02, "e": 3.2403e-02, "f": 3.3038e-01, "g": 6.2467e-02, "h": 2.5345e-03, "i": 9.7370e-02, "j": 1.1299e-02, "k": 4.9603e-03, "l": 2.7211e-02, "m": 3.1441e-02, "n": 1.6107e-02, "o": 7.0233e-02, "p": 5.0492e-02, "q": 5.3719e-02, "r": 5.1441e-03, "s": 5.7516e-03, "t": 3.1944e-03, "u": 4.7170e-02, "v": 1.8394e-03, "w": 7.4738e-04, "x": 1.0357e-02, "y": 1.4151e-02, "z": 4.5455e-03 }),
    "m": LetterProbability(1.5828e-02, 5.5944e-03, 2.0873e-02, { "a": 4.4235e-02, "b": 7.2893e-03, "c": 9.8692e-04, "d": 9.8035e-02, "e": 3.0999e-02, "f": 1.4179e-03, "g": 1.5683e-02, "h": 1.1264e-02, "i": 2.3634e-02, "j": 1.5066e-02, "k": 1.9841e-03, "l": 3.2535e-03, "m": 3.2614e-02, "n": 1.8326e-03, "o": 3.6233e-02, "p": 5.6507e-03, "q": 1.2397e-02, "r": 7.4304e-03, "s": 6.7470e-03, "t": 8.2345e-03, "u": 3.9216e-02, "v": 3.0656e-04, "w": 4.2227e-02, "x": 6.0990e-02, "y": 1.3738e-01, "z": 2.2727e-03 }),
    "n": LetterProbability(5.2078e-03, 4.4755e-03, 2.1146e-02, { "a": 1.0192e-01, "b": 5.0114e-02, "c": 1.6038e-03, "d": 2.9264e-03, "e": 1.6039e-01, "f": 1.4179e-03, "g": 9.0377e-03, "h": 5.6322e-03, "i": 1.8374e-01, "j": 5.6497e-03, "k": 8.9286e-03, "l": 1.4789e-04, "m": 9.8545e-03, "n": 1.0706e-02, "o": 2.3654e-01, "p": 8.0204e-03, "q": 4.1322e-03, "r": 2.5966e-02, "s": 4.6455e-03, "t": 1.7037e-03, "u": 4.3840e-02, "v": 3.0656e-04, "w": 6.0164e-02, "x": 2.3015e-03, "y": 1.4741e-02, "z": 4.5455e-03 }),
    "o": LetterProbability(4.0335e-02, 2.2378e-03, 4.0246e-02, { "a": 3.9566e-04, "b": 7.0159e-02, "c": 1.7839e-01, "d": 4.3269e-02, "e": 1.1449e-02, "f": 1.2726e-01, "g": 1.2228e-02, "h": 6.0546e-02, "i": 1.2264e-01, "j": 2.6365e-02, "k": 2.9762e-03, "l": 8.7548e-02, "m": 9.0568e-02, "n": 3.2793e-02, "o": 6.6970e-03, "p": 4.2836e-02, "q": 1.2397e-02, "r": 1.2330e-01, "s": 9.1251e-02, "t": 3.1731e-02, "u": 3.6996e-04, "v": 1.8056e-01, "w": 2.3318e-01, "x": 3.4522e-03, "y": 1.1792e-02, "z": 3.6364e-02 }),
    "p": LetterProbability(6.8518e-02, 1.3147e-02, 4.9568e-02, { "a": 3.8696e-02, "b": 2.2779e-03, "c": 8.6356e-04, "d": 2.2993e-03, "e": 1.8740e-02, "f": 2.8359e-03, "g": 1.0633e-03, "h": 2.5345e-03, "i": 1.6672e-02, "j": 1.6949e-02, "k": 1.9841e-03, "l": 1.3310e-03, "m": 6.8278e-02, "n": 1.7361e-03, "o": 5.2889e-02, "p": 2.6613e-02, "q": 1.6529e-02, "r": 8.1653e-04, "s": 2.6767e-02, "t": 3.4571e-02, "u": 6.7333e-02, "v": 4.9050e-03, "w": 3.3632e-03, "x": 3.4522e-02, "y": 1.7335e-01, "z": 9.0909e-03 }),
    "q": LetterProbability(0.0000e+00, 3.6364e-03, 5.4570e-04, { "a": 1.1079e-03, "b": 2.2779e-03, "c": 2.4673e-04, "d": 4.1806e-04, "e": 3.0242e-03, "f": 0.0000e+00, "g": 1.0633e-03, "h": 8.4483e-04, "i": 9.4534e-04, "j": 0.0000e+00, "k": 1.9841e-03, "l": 2.9577e-04, "m": 5.3965e-03, "n": 1.9290e-04, "o": 3.4344e-04, "p": 3.6456e-04, "q": 2.4793e-02, "r": 2.4496e-04, "s": 1.6591e-03, "t": 2.1296e-04, "u": 5.5494e-04, "v": 6.1312e-04, "w": 1.4948e-03, "x": 0.0000e+00, "y": 5.8962e-04, "z": 6.8182e-03 }),
    "r": LetterProbability(3.5127e-02, 4.1958e-03, 1.1596e-02, { "a": 9.9628e-02, "b": 3.1891e-02, "c": 2.4426e-02, "d": 4.1806e-03, "e": 1.8064e-01, "f": 6.0262e-02, "g": 3.9341e-02, "h": 6.7587e-03, "i": 1.9337e-02, "j": 7.5330e-03, "k": 1.9841e-03, "l": 1.4789e-04, "m": 1.6424e-03, "n": 1.9290e-04, "o": 2.2564e-01, "p": 2.4681e-01, "q": 1.2397e-02, "r": 9.9616e-03, "s": 7.6319e-03, "t": 5.7713e-02, "u": 2.1587e-01, "v": 4.5984e-03, "w": 1.3079e-02, "x": 4.6030e-03, "y": 1.7689e-03, "z": 6.8182e-03 }),
    "s": LetterProbability(1.2397e-01, 3.3566e-03, 7.4170e-02, { "a": 1.1292e-01, "b": 8.2005e-03, "c": 9.2524e-03, "d": 1.1497e-02, "e": 9.0511e-02, "f": 9.2166e-03, "g": 7.1770e-02, "h": 2.5345e-03, "i": 3.6525e-02, "j": 2.8625e-01, "k": 6.6468e-02, "l": 6.1372e-02, "m": 3.0033e-02, "n": 3.8291e-02, "o": 1.9833e-02, "p": 3.0077e-02, "q": 8.2645e-03, "r": 3.6580e-02, "s": 3.6169e-02, "t": 4.6852e-02, "u": 1.3929e-01, "v": 3.0656e-04, "w": 4.1480e-02, "x": 1.2658e-02, "y": 4.4811e-02, "z": 6.8182e-03 }),
    "t": LetterProbability(5.8103e-02, 5.0350e-03, 3.0059e-02, { "a": 1.3302e-01, "b": 2.2779e-03, "c": 7.6733e-02, "d": 4.8077e-03, "e": 6.8586e-02, "f": 7.0897e-03, "g": 2.6582e-03, "h": 1.2729e-01, "i": 1.1636e-01, "j": 1.8832e-03, "k": 3.9683e-03, "l": 6.9654e-02, "m": 3.5195e-03, "n": 2.4190e-01, "o": 1.2965e-02, "p": 7.6923e-02, "q": 8.2645e-03, "r": 4.1480e-02, "s": 2.2995e-01, "t": 3.9611e-02, "u": 1.6371e-01, "v": 3.9853e-03, "w": 1.1211e-03, "x": 1.5305e-01, "y": 3.5377e-03, "z": 2.2727e-03 }),
    "u": LetterProbability(4.4828e-02, 3.3566e-03, 1.9372e-02, { "a": 3.6876e-02, "b": 1.1526e-01, "c": 4.6755e-02, "d": 4.3687e-02, "e": 1.2961e-03, "f": 2.8359e-03, "g": 2.3126e-02, "h": 3.5483e-02, "i": 8.5940e-05, "j": 7.5330e-03, "k": 1.7857e-02, "l": 4.5401e-02, "m": 1.4547e-02, "n": 6.8480e-03, "o": 9.1955e-02, "p": 3.1170e-02, "q": 3.5537e-01, "r": 4.4909e-03, "s": 1.3494e-02, "t": 1.5333e-02, "u": 7.3992e-04, "v": 9.1968e-04, "w": 0.0000e+00, "x": 5.7537e-03, "y": 1.1792e-03, "z": 4.5455e-03 }),
    "v": LetterProbability(3.8803e-03, 1.1469e-02, 7.9582e-03, { "a": 5.6263e-02, "b": 1.8223e-03, "c": 7.4019e-04, "d": 2.0903e-03, "e": 4.2934e-02, "f": 7.0897e-04, "g": 2.9240e-03, "h": 8.4483e-04, "i": 2.9134e-02, "j": 0.0000e+00, "k": 8.9286e-03, "l": 5.1760e-03, "m": 2.5809e-03, "n": 5.6906e-03, "o": 2.1465e-02, "p": 2.0598e-02, "q": 8.2645e-03, "r": 3.4131e-02, "s": 2.7652e-03, "t": 2.8395e-04, "u": 7.3992e-04, "v": 0.0000e+00, "w": 3.7369e-04, "x": 0.0000e+00, "y": 1.1792e-03, "z": 4.5455e-03 }),
    "w": LetterProbability(1.0007e-02, 2.5175e-03, 3.2242e-02, { "a": 1.5035e-03, "b": 3.1891e-03, "c": 1.2337e-04, "d": 6.2709e-04, "e": 3.3213e-02, "f": 7.0897e-04, "g": 2.6582e-04, "h": 2.8161e-04, "i": 6.8752e-04, "j": 1.1299e-02, "k": 5.9524e-03, "l": 2.9577e-04, "m": 4.6926e-04, "n": 2.4113e-03, "o": 4.5591e-02, "p": 2.0051e-03, "q": 4.1322e-03, "r": 8.9818e-04, "s": 7.5655e-02, "t": 3.5494e-04, "u": 3.6996e-04, "v": 6.1312e-04, "w": 7.5112e-02, "x": 6.9045e-03, "y": 2.3585e-03, "z": 4.5455e-03 }),
    "x": LetterProbability(1.0211e-03, 7.8322e-03, 5.5480e-03, { "a": 3.4027e-03, "b": 4.5558e-04, "c": 3.7010e-04, "d": 6.2709e-04, "e": 2.2358e-02, "f": 6.7352e-03, "g": 1.0633e-03, "h": 0.0000e+00, "i": 1.5469e-03, "j": 1.8832e-03, "k": 2.9762e-03, "l": 7.3943e-04, "m": 1.1732e-03, "n": 9.6451e-05, "o": 5.6667e-03, "p": 1.0937e-03, "q": 1.2397e-02, "r": 8.1653e-05, "s": 2.2121e-04, "t": 2.8395e-04, "u": 1.1469e-02, "v": 3.0656e-04, "w": 1.1211e-03, "x": 2.0713e-02, "y": 2.3585e-03, "z": 4.5455e-03 }),
    "y": LetterProbability(0.0000e+00, 6.1538e-03, 6.3665e-04, { "a": 1.2028e-02, "b": 1.6856e-02, "c": 1.2337e-03, "d": 3.9716e-03, "e": 3.7803e-03, "f": 3.1904e-03, "g": 2.6582e-03, "h": 5.6322e-04, "i": 3.4376e-04, "j": 3.7665e-03, "k": 9.9206e-04, "l": 4.1556e-02, "m": 5.1619e-03, "n": 2.2569e-02, "o": 6.0101e-04, "p": 1.8228e-03, "q": 2.0661e-02, "r": 3.3641e-02, "s": 6.8576e-03, "t": 2.9815e-02, "u": 9.2490e-04, "v": 1.2262e-03, "w": 1.1211e-03, "x": 1.9563e-02, "y": 4.1274e-03, "z": 1.3636e-02 }),
    "z": LetterProbability(2.0423e-04, 2.5175e-03, 7.2760e-04, { "a": 2.0575e-03, "b": 4.5558e-04, "c": 1.2337e-04, "d": 4.1806e-04, "e": 1.0801e-04, "f": 1.4179e-03, "g": 2.3923e-03, "h": 5.3506e-03, "i": 9.2815e-03, "j": 3.7665e-03, "k": 3.9683e-03, "l": 1.4789e-04, "m": 7.0389e-04, "n": 5.7870e-04, "o": 8.5859e-05, "p": 0.0000e+00, "q": 1.2397e-02, "r": 8.1653e-05, "s": 3.3182e-04, "t": 7.0987e-05, "u": 5.3644e-03, "v": 0.0000e+00, "w": 4.7085e-02, "x": 3.4522e-03, "y": 1.0613e-02, "z": 6.8182e-03 }),
    "A": LetterProbability(5.4120e-03, 5.5944e-03, 2.1146e-02, { "a": 1.5827e-04, "b": 1.8223e-03, "c": 3.5776e-03, "d": 4.8077e-03, "e": 2.9702e-03, "f": 0.0000e+00, "g": 8.2403e-03, "h": 1.0138e-02, "i": 0.0000e+00, "j": 0.0000e+00, "k": 9.9206e-04, "l": 2.8098e-03, "m": 2.5809e-03, "n": 7.7160e-04, "o": 1.3737e-03, "p": 1.0937e-03, "q": 8.2645e-03, "r": 3.5111e-03, "s": 1.8803e-03, "t": 1.9876e-03, "u": 0.0000e+00, "v": 0.0000e+00, "w": 1.1211e-03, "x": 8.4005e-02, "y": 1.1792e-03, "z": 2.2727e-03 }),
    "B": LetterProbability(1.1233e-03, 8.9510e-03, 1.2733e-03, { "a": 7.9133e-05, "b": 1.8223e-03, "c": 2.4673e-04, "d": 1.8813e-03, "e": 2.1602e-04, "f": 1.4179e-03, "g": 7.9745e-04, "h": 1.1264e-03, "i": 4.2970e-04, "j": 1.8832e-03, "k": 3.9683e-03, "l": 0.0000e+00, "m": 4.6926e-04, "n": 1.6397e-03, "o": 0.0000e+00, "p": 3.6456e-04, "q": 4.1322e-03, "r": 1.6331e-04, "s": 9.9547e-04, "t": 2.1296e-04, "u": 0.0000e+00, "v": 0.0000e+00, "w": 7.4738e-04, "x": 1.0357e-02, "y": 1.0024e-02, "z": 4.5455e-03 }),
    "C": LetterProbability(1.9402e-03, 2.5175e-03, 7.1396e-03, { "a": 3.1653e-04, "b": 4.5558e-04, "c": 1.2337e-04, "d": 2.0903e-04, "e": 1.7281e-03, "f": 1.4179e-03, "g": 5.3163e-04, "h": 3.9426e-03, "i": 4.2970e-04, "j": 0.0000e+00, "k": 3.9683e-03, "l": 2.8098e-03, "m": 7.0389e-04, "n": 3.8580e-04, "o": 0.0000e+00, "p": 1.6405e-03, "q": 4.1322e-03, "r": 2.1230e-03, "s": 7.7425e-04, "t": 3.3364e-03, "u": 5.5494e-04, "v": 6.1312e-04, "w": 1.1211e-03, "x": 1.1507e-03, "y": 1.7689e-03, "z": 4.5455e-03 }),
    "D": LetterProbability(7.7606e-03, 2.7972e-03, 1.2824e-02, { "a": 1.3453e-03, "b": 1.3667e-03, "c": 2.4673e-04, "d": 2.0903e-04, "e": 2.1062e-03, "f": 0.0000e+00, "g": 1.3291e-03, "h": 2.8161e-04, "i": 2.5782e-04, "j": 1.8832e-03, "k": 0.0000e+00, "l": 1.4789e-04, "m": 2.3463e-04, "n": 9.6451e-05, "o": 2.5758e-04, "p": 7.2913e-04, "q": 0.0000e+00, "r": 1.4697e-02, "s": 2.2121e-04, "t": 1.2778e-03, "u": 3.6996e-04, "v": 3.0656e-04, "w": 3.7369e-04, "x": 0.0000e+00, "y": 2.3585e-03, "z": 2.2727e-03 }),
    "E": LetterProbability(7.8628e-03, 6.4336e-03, 1.7417e-02, { "a": 7.9133e-05, "b": 0.0000e+00, "c": 1.7271e-03, "d": 4.8077e-03, "e": 5.9405e-04, "f": 3.5448e-03, "g": 3.4556e-03, "h": 2.8161e-04, "i": 8.5940e-05, "j": 1.8832e-03, "k": 9.9206e-04, "l": 1.4789e-04, "m": 1.1732e-03, "n": 5.2083e-03, "o": 2.1465e-03, "p": 0.0000e+00, "q": 4.1322e-03, "r": 2.1230e-03, "s": 1.8803e-03, "t": 2.4846e-03, "u": 0.0000e+00, "v": 6.1312e-04, "w": 1.8685e-03, "x": 2.3015e-03, "y": 1.1792e-03, "z": 2.2727e-03 }),
    "F": LetterProbability(3.6761e-03, 7.2727e-03, 2.2738e-03, { "a": 3.1653e-04, "b": 0.0000e+00, "c": 0.0000e+00, "d": 4.1806e-04, "e": 1.6741e-03, "f": 1.0635e-03, "g": 2.5518e-02, "h": 0.0000e+00, "i": 0.0000e+00, "j": 1.8832e-03, "k": 9.9206e-04, "l": 5.9154e-04, "m": 0.0000e+00, "n": 6.6551e-03, "o": 2.3182e-03, "p": 7.2913e-04, "q": 4.1322e-03, "r": 1.3881e-03, "s": 1.8803e-03, "t": 5.1821e-03, "u": 3.6996e-04, "v": 0.0000e+00, "w": 1.1211e-03, "x": 2.3015e-03, "y": 8.8443e-03, "z": 4.5455e-03 }),
    "G": LetterProbability(7.1480e-04, 2.5175e-03, 7.7308e-04, { "a": 1.5827e-04, "b": 1.3667e-03, "c": 1.2337e-04, "d": 4.1806e-04, "e": 0.0000e+00, "f": 0.0000e+00, "g": 1.0633e-03, "h": 0.0000e+00, "i": 1.7188e-04, "j": 1.8832e-03, "k": 9.9206e-04, "l": 0.0000e+00, "m": 4.6926e-04, "n": 9.6451e-05, "o": 0.0000e+00, "p": 5.4685e-04, "q": 0.0000e+00, "r": 2.4496e-04, "s": 1.1061e-04, "t": 7.0987e-05, "u": 0.0000e+00, "v": 3.0656e-04, "w": 7.4738e-04, "x": 0.0000e+00, "y": 1.7689e-03, "z": 4.5455e-03 }),
    "H": LetterProbability(8.1691e-04, 3.0769e-03, 1.8190e-03, { "a": 1.5827e-04, "b": 4.5558e-04, "c": 6.1683e-04, "d": 2.0903e-04, "e": 1.0801e-04, "f": 1.0280e-02, "g": 6.6454e-03, "h": 7.0403e-03, "i": 2.5782e-04, "j": 3.7665e-03, "k": 0.0000e+00, "l": 1.4789e-04, "m": 0.0000e+00, "n": 5.0154e-03, "o": 0.0000e+00, "p": 5.4685e-04, "q": 8.2645e-03, "r": 4.8992e-04, "s": 4.6455e-03, "t": 1.2778e-03, "u": 1.8498e-04, "v": 3.0656e-04, "w": 0.0000e+00, "x": 0.0000e+00, "y": 1.7689e-03, "z": 4.5455e-03 }),
    "I": LetterProbability(8.1691e-04, 2.5175e-03, 2.0464e-03, { "a": 7.9133e-05, "b": 4.5558e-04, "c": 3.7010e-04, "d": 4.1806e-04, "e": 1.9982e-03, "f": 1.0635e-03, "g": 4.2531e-03, "h": 1.4081e-03, "i": 2.5782e-04, "j": 3.7665e-03, "k": 0.0000e+00, "l": 0.0000e+00, "m": 9.3853e-04, "n": 1.8326e-03, "o": 1.7172e-04, "p": 7.2913e-04, "q": 8.2645e-03, "r": 1.7147e-03, "s": 6.6364e-04, "t": 2.8395e-04, "u": 7.3992e-04, "v": 0.0000e+00, "w": 1.8685e-03, "x": 1.1507e-03, "y": 5.8962e-04, "z": 0.0000e+00 }),
    "J": LetterProbability(5.1057e-04, 1.6783e-03, 6.8213e-04, { "a": 7.9133e-05, "b": 0.0000e+00, "c": 0.0000e+00, "d": 0.0000e+00, "e": 1.6201e-04, "f": 3.5448e-04, "g": 2.6582e-04, "h": 5.6322e-04, "i": 8.5940e-05, "j": 0.0000e+00, "k": 1.9841e-03, "l": 1.4789e-04, "m": 0.0000e+00, "n": 2.8935e-04, "o": 8.5859e-05, "p": 1.8228e-04, "q": 0.0000e+00, "r": 2.4496e-04, "s": 2.2121e-04, "t": 2.8395e-04, "u": 1.8498e-04, "v": 9.1968e-04, "w": 7.4738e-04, "x": 3.4522e-03, "y": 1.7689e-03, "z": 9.0909e-03 }),
    "K": LetterProbability(0.0000e+00, 3.0769e-03, 1.8190e-04, { "a": 1.5827e-04, "b": 0.0000e+00, "c": 0.0000e+00, "d": 2.0903e-04, "e": 1.6201e-04, "f": 0.0000e+00, "g": 0.0000e+00, "h": 0.0000e+00, "i": 8.5940e-05, "j": 3.7665e-03, "k": 9.9206e-04, "l": 0.0000e+00, "m": 4.6926e-04, "n": 9.6451e-05, "o": 2.5758e-04, "p": 1.8228e-04, "q": 8.2645e-03, "r": 4.8992e-04, "s": 1.2167e-03, "t": 1.4197e-04, "u": 0.0000e+00, "v": 6.1312e-04, "w": 3.7369e-04, "x": 1.1507e-03, "y": 5.8962e-04, "z": 2.2727e-03 }),
    "L": LetterProbability(8.1691e-04, 2.2378e-03, 3.3197e-03, { "a": 2.3740e-04, "b": 0.0000e+00, "c": 0.0000e+00, "d": 1.8813e-03, "e": 8.6407e-04, "f": 7.0897e-04, "g": 5.3163e-04, "h": 2.8161e-03, "i": 2.4063e-03, "j": 7.5330e-03, "k": 1.9841e-03, "l": 0.0000e+00, "m": 0.0000e+00, "n": 2.8935e-04, "o": 3.4344e-04, "p": 1.8228e-04, "q": 0.0000e+00, "r": 1.7147e-03, "s": 3.3182e-04, "t": 4.2592e-04, "u": 1.8498e-04, "v": 6.1312e-04, "w": 0.0000e+00, "x": 0.0000e+00, "y": 2.3585e-03, "z": 2.2727e-03 }),
    "M": LetterProbability(1.8380e-03, 3.0769e-03, 5.3661e-03, { "a": 0.0000e+00, "b": 9.1116e-04, "c": 1.2337e-04, "d": 3.7625e-03, "e": 1.6201e-04, "f": 1.0635e-03, "g": 2.6582e-04, "h": 1.6897e-03, "i": 8.5940e-05, "j": 3.7665e-03, "k": 2.9762e-03, "l": 5.9154e-04, "m": 2.3463e-04, "n": 5.3048e-03, "o": 6.0101e-04, "p": 7.2913e-04, "q": 0.0000e+00, "r": 4.3276e-03, "s": 6.6364e-04, "t": 2.1296e-04, "u": 1.8498e-04, "v": 6.1312e-04, "w": 4.1106e-03, "x": 3.4522e-03, "y": 1.1792e-03, "z": 0.0000e+00 }),
    "N": LetterProbability(5.1057e-04, 2.5175e-03, 1.8190e-03, { "a": 3.1653e-04, "b": 0.0000e+00, "c": 1.2337e-04, "d": 1.6722e-03, "e": 1.2961e-03, "f": 3.5448e-04, "g": 1.0633e-03, "h": 2.8161e-04, "i": 2.5782e-04, "j": 0.0000e+00, "k": 9.9206e-04, "l": 7.3943e-04, "m": 4.9273e-03, "n": 9.6451e-04, "o": 0.0000e+00, "p": 1.8228e-04, "q": 8.2645e-03, "r": 3.2661e-04, "s": 8.8486e-04, "t": 3.5494e-04, "u": 0.0000e+00, "v": 3.0656e-04, "w": 0.0000e+00, "x": 1.1507e-03, "y": 1.1792e-02, "z": 9.0909e-03 }),
    "O": LetterProbability(3.0634e-03, 3.9161e-03, 1.4097e-03, { "a": 0.0000e+00, "b": 0.0000e+00, "c": 0.0000e+00, "d": 1.2542e-03, "e": 1.0801e-03, "f": 3.5448e-04, "g": 0.0000e+00, "h": 1.1264e-03, "i": 3.4376e-04, "j": 0.0000e+00, "k": 9.9206e-04, "l": 1.4789e-04, "m": 1.8771e-03, "n": 4.8225e-04, "o": 1.7172e-04, "p": 3.6456e-04, "q": 8.2645e-03, "r": 2.2863e-03, "s": 1.1061e-04, "t": 2.1296e-04, "u": 1.8498e-04, "v": 3.0656e-04, "w": 1.4948e-03, "x": 0.0000e+00, "y": 1.4741e-02, "z": 4.5455e-03 }),
    "P": LetterProbability(1.1233e-03, 3.6364e-03, 3.5471e-03, { "a": 3.1653e-04, "b": 0.0000e+00, "c": 1.2337e-04, "d": 1.2542e-03, "e": 6.4805e-03, "f": 3.5448e-04, "g": 1.8607e-03, "h": 1.2109e-02, "i": 1.2891e-03, "j": 5.6497e-03, "k": 5.9524e-03, "l": 3.9929e-03, "m": 7.0389e-03, "n": 4.1474e-03, "o": 3.4344e-04, "p": 1.6405e-03, "q": 0.0000e+00, "r": 4.7359e-03, "s": 2.8758e-03, "t": 1.8457e-03, "u": 5.1794e-03, "v": 3.0656e-04, "w": 1.4948e-03, "x": 2.3015e-03, "y": 8.1958e-02, "z": 0.0000e+00 }),
    "Q": LetterProbability(0.0000e+00, 2.5175e-03, 9.0950e-04, { "a": 0.0000e+00, "b": 9.1116e-04, "c": 1.2337e-04, "d": 8.3612e-04, "e": 5.9405e-04, "f": 0.0000e+00, "g": 1.5949e-03, "h": 0.0000e+00, "i": 0.0000e+00, "j": 1.8832e-03, "k": 0.0000e+00, "l": 4.4366e-04, "m": 7.0389e-04, "n": 0.0000e+00, "o": 4.2930e-04, "p": 1.8228e-04, "q": 4.1322e-03, "r": 1.6331e-04, "s": 1.1061e-04, "t": 0.0000e+00, "u": 0.0000e+00, "v": 3.0656e-04, "w": 7.4738e-04, "x": 2.3015e-03, "y": 1.1792e-03, "z": 0.0000e+00 }),
    "R": LetterProbability(5.9532e-02, 3.0769e-03, 2.4557e-03, { "a": 3.1653e-04, "b": 9.1116e-04, "c": 1.2337e-04, "d": 6.2709e-03, "e": 1.1881e-03, "f": 3.1904e-03, "g": 1.3291e-03, "h": 4.2242e-03, "i": 8.5940e-05, "j": 1.8832e-03, "k": 2.9762e-03, "l": 2.0704e-03, "m": 4.6926e-04, "n": 1.9290e-04, "o": 9.4445e-04, "p": 1.8228e-04, "q": 4.1322e-03, "r": 5.2258e-03, "s": 0.0000e+00, "t": 1.4907e-03, "u": 5.5494e-04, "v": 3.0656e-04, "w": 7.4738e-04, "x": 1.1507e-03, "y": 5.8962e-04, "z": 4.5455e-03 }),
    "S": LetterProbability(9.3945e-03, 4.4755e-03, 1.3233e-02, { "a": 1.1870e-03, "b": 9.1116e-04, "c": 1.2337e-04, "d": 1.4632e-03, "e": 7.0206e-03, "f": 3.5448e-04, "g": 2.1265e-03, "h": 6.4770e-03, "i": 8.5940e-05, "j": 9.4162e-03, "k": 4.9603e-03, "l": 7.3943e-04, "m": 1.8771e-03, "n": 3.7616e-03, "o": 9.4445e-04, "p": 7.2913e-04, "q": 1.2397e-02, "r": 3.1028e-03, "s": 1.6038e-02, "t": 2.2006e-03, "u": 3.6996e-04, "v": 0.0000e+00, "w": 4.4843e-03, "x": 1.1507e-02, "y": 6.1321e-02, "z": 2.2727e-03 }),
    "T": LetterProbability(1.8380e-03, 4.7552e-03, 4.6385e-03, { "a": 2.3740e-04, "b": 1.1845e-02, "c": 2.5907e-03, "d": 2.7174e-03, "e": 7.5606e-04, "f": 1.0635e-03, "g": 0.0000e+00, "h": 4.5058e-03, "i": 0.0000e+00, "j": 3.7665e-03, "k": 9.9206e-04, "l": 2.2183e-03, "m": 4.2234e-03, "n": 1.3503e-03, "o": 1.7172e-04, "p": 0.0000e+00, "q": 0.0000e+00, "r": 3.1845e-03, "s": 3.3182e-04, "t": 4.9691e-04, "u": 1.6648e-03, "v": 9.1968e-04, "w": 7.4738e-04, "x": 0.0000e+00, "y": 1.1792e-03, "z": 4.5455e-03 }),
    "U": LetterProbability(6.1268e-04, 3.3566e-03, 1.5098e-02, { "a": 1.5827e-04, "b": 9.1116e-04, "c": 1.2337e-04, "d": 2.9264e-03, "e": 1.0801e-04, "f": 7.0897e-04, "g": 1.3291e-03, "h": 1.9713e-03, "i": 1.7188e-04, "j": 1.8832e-03, "k": 0.0000e+00, "l": 1.1831e-03, "m": 1.8771e-03, "n": 1.4468e-03, "o": 2.5758e-04, "p": 2.3697e-03, "q": 0.0000e+00, "r": 8.1653e-05, "s": 1.8803e-03, "t": 1.4197e-04, "u": 0.0000e+00, "v": 6.1312e-04, "w": 1.1211e-03, "x": 0.0000e+00, "y": 1.1792e-03, "z": 0.0000e+00 }),
    "V": LetterProbability(6.1268e-04, 4.4755e-03, 8.2765e-03, { "a": 3.1653e-04, "b": 1.8223e-03, "c": 0.0000e+00, "d": 0.0000e+00, "e": 3.4563e-03, "f": 1.4179e-03, "g": 0.0000e+00, "h": 1.1264e-03, "i": 8.5940e-05, "j": 3.7665e-03, "k": 1.9841e-03, "l": 0.0000e+00, "m": 4.6926e-04, "n": 1.7361e-03, "o": 8.5859e-05, "p": 1.8228e-04, "q": 8.2645e-03, "r": 6.5322e-04, "s": 1.1061e-03, "t": 3.5494e-04, "u": 0.0000e+00, "v": 0.0000e+00, "w": 3.7369e-04, "x": 3.4522e-03, "y": 1.1792e-03, "z": 4.5455e-03 }),
    "W": LetterProbability(1.6338e-03, 4.4755e-03, 1.6371e-03, { "a": 2.3740e-04, "b": 4.5558e-04, "c": 1.2337e-04, "d": 0.0000e+00, "e": 1.0261e-03, "f": 0.0000e+00, "g": 2.6582e-04, "h": 5.6322e-04, "i": 1.7188e-04, "j": 9.4162e-03, "k": 0.0000e+00, "l": 1.4789e-04, "m": 4.6926e-04, "n": 3.8580e-04, "o": 8.5859e-05, "p": 5.4685e-04, "q": 4.1322e-03, "r": 4.8992e-04, "s": 0.0000e+00, "t": 2.1296e-04, "u": 0.0000e+00, "v": 0.0000e+00, "w": 7.4738e-04, "x": 3.4522e-03, "y": 1.7689e-03, "z": 2.2727e-03 }),
    "X": LetterProbability(1.0211e-04, 2.7972e-03, 9.0950e-04, { "a": 2.3740e-04, "b": 1.8223e-03, "c": 1.2337e-04, "d": 6.2709e-04, "e": 2.7002e-04, "f": 0.0000e+00, "g": 0.0000e+00, "h": 2.8161e-04, "i": 8.5940e-05, "j": 5.6497e-03, "k": 0.0000e+00, "l": 0.0000e+00, "m": 2.3463e-04, "n": 2.8935e-04, "o": 8.5859e-05, "p": 0.0000e+00, "q": 8.2645e-03, "r": 8.1653e-05, "s": 2.2121e-04, "t": 0.0000e+00, "u": 1.8498e-04, "v": 3.0656e-04, "w": 0.0000e+00, "x": 2.3015e-03, "y": 1.7689e-03, "z": 2.2727e-03 }),
    "Y": LetterProbability(7.1480e-04, 1.6783e-03, 6.8213e-04, { "a": 0.0000e+00, "b": 4.5558e-04, "c": 4.9346e-04, "d": 2.0903e-04, "e": 1.6201e-04, "f": 3.5448e-04, "g": 0.0000e+00, "h": 5.6322e-04, "i": 8.5940e-05, "j": 0.0000e+00, "k": 0.0000e+00, "l": 1.4789e-04, "m": 1.1732e-03, "n": 2.8935e-04, "o": 0.0000e+00, "p": 1.8228e-04, "q": 0.0000e+00, "r": 0.0000e+00, "s": 0.0000e+00, "t": 1.4197e-04, "u": 0.0000e+00, "v": 3.0656e-04, "w": 0.0000e+00, "x": 1.1507e-03, "y": 5.8962e-04, "z": 0.0000e+00 }),
    "Z": LetterProbability(0.0000e+00, 3.9161e-03, 1.3643e-04, { "a": 1.5827e-04, "b": 4.5558e-04, "c": 1.2337e-04, "d": 0.0000e+00, "e": 1.0801e-04, "f": 0.0000e+00, "g": 1.0633e-03, "h": 0.0000e+00, "i": 2.5782e-04, "j": 1.8832e-03, "k": 1.9841e-03, "l": 2.9577e-04, "m": 9.3853e-04, "n": 1.9290e-04, "o": 1.0303e-03, "p": 3.6456e-04, "q": 4.1322e-03, "r": 0.0000e+00, "s": 2.2121e-04, "t": 0.0000e+00, "u": 1.8498e-04, "v": 6.1312e-04, "w": 3.7369e-04, "x": 1.1507e-03, "y": 0.0000e+00, "z": 0.0000e+00 }),
}




# ----- Actual checks trying to detect secrets ---------------------------------------------------

def check_file(ctx: Context, content: bytes, path: str):
    check_vault(ctx, content, path)
    check_private_key(ctx, content, path)
    check_string_entropy(ctx, content, path)


def check_vault(ctx: Context, content: bytes, path: str):
    """Checks for unencrypted Ansible vaults

    Emits an error if the filename is "vault" but the file does not start with
    "$ANSIBLE_VAULT", OR if any line starts with `vault_` and has a colon in it
    (thus resembling a variable assignment).
    """
    if os.path.basename(path) == "vault" and not content.startswith(b"$ANSIBLE_VAULT"):
        ctx.error(path, f'has filename "vault" but does not start with "$ANSIBLE_VAULT"')
        return

    for lineno, line in enumerate(content.splitlines(), start=1):
        if line.startswith(b"vault_") and b":" in line:
            linestr = line.decode(errors="replace")
            ctx.line_error(path, lineno, f'looks like a vault variable definition: {linestr}')


def check_private_key(ctx: Context, content: bytes, path: str):
    pattern = re.compile(b"-----BEGIN .+PRIVATE KEY-----")
    for lineno, line in enumerate(content.splitlines(), start=1):
        if pattern.search(line) is not None:
            linestr = line.decode(errors="replace")
            ctx.line_error(path, lineno, f'unencrypted private key: {linestr}')

def check_string_entropy(ctx: Context, content: bytes, path: str):
    # The pattern we expect the password to be in. Includes all ASCII characters
    # except for space, control characters and quotation marks. We also assume
    # that passwords are at least 6 characters long. If yours are shorter, you
    # should feel bad.
    pwpattern = r'([A-Za-z]{6,})'
    #pwpattern = r'([A-Za-z0-9!#$%&()+*,./:;<=>?@_{|}~\-\^\[\]\\]{6,})'

    # We expect the passwords in certain contexts, e.g. surounded by "".
    pattern = re.compile(f'"{pwpattern}"|\'{pwpattern}\'|>{pwpattern}<'.encode())

    for lineno, line in enumerate(content.splitlines(), start=1):
        for match in pattern.finditer(line):
            inner_bytes = [group for group in match.groups() if group is not None][0]
            inner = inner_bytes.decode() # TODO: handle non utf8

            entropy = 0.0
            for i, c in enumerate(inner):
                prev = inner[i - 1] if i != 0 else None
                p = PROBS.prob(prev, c)
                min = 0.000001
                # if p < min:
                #     p = min
                entropy += p * len(PASSWORD_CHARS)
                # print(f'  {prev}{c} - {p:.4}')
                # entropy += p * math.log(p, 2)
            # entropy = -entropy
            # entropy = 1 / (entropy / len(inner))
            entropy /= len(inner)
            entropy = 1 / entropy

            if entropy > 0.5:
                ctx.line_error(path, lineno, f'high entropy string: "{inner}" (entropy {entropy})')
                # print(f'{inner} => {entropy}')





# ----- Main: entry points -----------------------------------------------------------------------

def main():
    ctx = Context()

    if len(sys.argv) < 2:
        print_help()
    elif len(sys.argv) == 2 and sys.argv[1] == "--staged":
        check_staged(ctx)
    elif len(sys.argv) == 4 and sys.argv[1] == "--between":
        check_between(ctx, sys.argv[2], sys.argv[3])
    elif len(sys.argv) == 2:
        check_current(ctx, sys.argv[1])
    else:
        print_help()

    if ctx.errored:
        eprint("")
        eprint("Potentially found unencrypted secrets!")
        sys.exit(1)

def print_help():
    print("Missing argument. Usage:")
    print("")
    print("Checking a single given file or all files in a given directory:")
    print("    check <path>")
    print("")
    print("Checking all files that are currently staged by git (useful for pre-commit hook):")
    print("    check --staged")
    print("")
    print("Checking all files that were changed somewhere between two commits. This is")
    print("useful for pre-receive git hooks as only checking the final files does not")
    print("tell you if secrets are hiding somewhere in the git history. This command")
    print("checks the commits given by this command: `git rev-list base^ target`.")
    print("    check --between <base-commit> <target-commit>")

def check_staged(ctx: Context):
    """Checks all files that are currently staged. Useful in pre-commit hook"""

    files = subprocess.check_output(["git", "diff", "--staged", "--name-only"])
    for file in files.splitlines():
        filestr = file.decode()
        content = read_file(filestr)
        check_file(ctx, content, filestr)

def check_between(ctx: Context, base: str, target: str):
    """Checks all files changed in all commits between the two given ones.

    "Between" in the git commit graph is a bit vague. Precisely: all commits are
    inspected that are reachable from 'target' but are not reachable from
    'base'. This maps very nicely to the intuitive notion of "new commits" in a
    pre-receive hook.
    """

    commits = subprocess.check_output(["git", "rev-list", f'^{base}', target])
    for rawcommit in commits.splitlines():
        commit = rawcommit.decode()

        # Setting the commit in the context for better error message
        ctx.commit = commit

        # Receive all files that were somehow changed in that commit, excluding
        # the files that were removed.
        cmd = ["git", "diff", "--diff-filter=d", "--name-only", f'{commit}^', commit]
        files = subprocess.check_output(cmd)
        for file in files.splitlines():
            filestr = file.decode()
            content = subprocess.check_output(["git", "show", f'{commit}:{filestr}'])
            check_file(ctx, content, filestr)


def check_current(ctx: Context, path: str):
    """Checks all files in 'path' in their current version (not using git)"""

    if os.path.isfile(path):
        content = read_file(path)
        check_file(ctx, content, path)
    else:
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                fullpath = os.path.join(dirpath, filename);
                content = read_file(fullpath)
                check_file(ctx, content, fullpath)




if __name__ == "__main__":
    main()
