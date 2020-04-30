# The MIT License (MIT)
#
# Copyright (c) 2018 OGS
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import sys

def getmembers(obj, pred=None):
    res = []
    for name in dir(obj):
        val = getattr(obj, name)
        if pred is None or pred(val):
            res.append((name, val))
    res.sort()
    return res

def isfunction(obj):
    return isinstance(obj, type(isfunction))

def isgeneratorfunction(obj):
    return isinstance(obj, type(lambda:(yield)))

def isgenerator(obj):
    return isinstance(obj, type(lambda:(yield)()))

class _Class:
    def meth(): pass
_Instance = _Class()

def ismethod(obj):
    return isinstance(obj, type(_Instance.meth))

def isclass(obj):
    return isinstance(obj, type)

def ismodule(obj):
    return isinstance(obj, type(sys))


def getargspec(func):
    raise NotImplementedError("This is over-dynamic function, not supported by MicroPython")

def getmodule(obj, _filename=None):
    return None  # Not known

def getmro(cls):
    return [cls]

def getsourcefile(obj):
    return None  # Not known

def getfile(obj):
    return "<unknown>"

def getsource(obj):
    return "<source redacted to save you memory>"


def currentframe():
    return None

def getframeinfo(frame, context=1):
    return ("<unknown>", -1, "<unknown>", [""], 0)
