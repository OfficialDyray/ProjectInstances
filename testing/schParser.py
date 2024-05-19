# Taken from https://github.com/pyparsing/pyparsing/blob/master/examples/sexpParser.py
# Thank you pyparsing!

# sexpParser.py
#
# Demonstration of the pyparsing module, implementing a simple S-expression
# parser.
#
# Updates:
#  November, 2011 - fixed errors in precedence of alternatives in simpleString;
#      fixed exception raised in verifyLen to properly signal the input string
#      and exception location so that markInputline works correctly; fixed
#      definition of decimal to accept a single '0' and optional leading '-'
#      sign; updated tests to improve parser coverage
#
# Copyright 2007-2011, by Paul McGuire
#
"""
BNF reference: http://theory.lcs.mit.edu/~rivest/sexp.txt

<sexp>    	:: <string> | <list>
<string>   	:: <display>? <simple-string> ;
<simple-string>	:: <raw> | <token> | <base-64> | <hexadecimal> |
                   <quoted-string> ;
<display>  	:: "[" <simple-string> "]" ;
<raw>      	:: <decimal> ":" <bytes> ;
<decimal>  	:: <decimal-digit>+ ;
        -- decimal numbers should have no unnecessary leading zeros
<bytes>     -- any string of bytes, of the indicated length
<token>    	:: <tokenchar>+ ;
<base-64>  	:: <decimal>? "|" ( <base-64-char> | <whitespace> )* "|" ;
<hexadecimal>   :: "#" ( <hex-digit> | <white-space> )* "#" ;
<quoted-string> :: <decimal>? <quoted-string-body>
<quoted-string-body> :: "\"" <bytes> "\""
<list>     	:: "(" ( <sexp> | <whitespace> )* ")" ;
<whitespace> 	:: <whitespace-char>* ;
<token-char>  	:: <alpha> | <decimal-digit> | <simple-punc> ;
<alpha>       	:: <upper-case> | <lower-case> | <digit> ;
<lower-case>  	:: "a" | ... | "z" ;
<upper-case>  	:: "A" | ... | "Z" ;
<decimal-digit> :: "0" | ... | "9" ;
<hex-digit>     :: <decimal-digit> | "A" | ... | "F" | "a" | ... | "f" ;
<simple-punc> 	:: "-" | "." | "/" | "_" | ":" | "*" | "+" | "=" ;
<whitespace-char> :: " " | "\t" | "\r" | "\n" ;
<base-64-char> 	:: <alpha> | <decimal-digit> | "+" | "/" | "=" ;
<null>        	:: "" ;
"""
#
# ------------------------Start of my imports-------------------------
#

from pathlib import PurePath

#
# ------------------------End of my imports-------------------------
#

import pyparsing as pp
from base64 import b64decode


def verify_length(s, l, t):
    t = t[0]
    if t.len is not None:
        t1len = len(t[1])
        if t1len != t.len:
            raise pp.ParseFatalException(
                s, l, "invalid data of length {}, expected {}".format(t1len, t.len)
            )
    return t[1]


# define punctuation literals
LPAR, RPAR, LBRK, RBRK, LBRC, RBRC, VBAR, COLON = (
    pp.Suppress(c).setName(c) for c in "()[]{}|:"
)

decimal = pp.Regex(r"-?0|[1-9]\d*").setParseAction(lambda t: int(t[0]))
hexadecimal = ("#" + pp.Word(pp.hexnums)[1, ...] + "#").setParseAction(
    lambda t: int("".join(t[1:-1]), 16)
)
bytes = pp.Word(pp.printables)
raw = pp.Group(decimal("len") + COLON + bytes).setParseAction(verify_length)
base64_ = pp.Group(
    pp.Optional(decimal | hexadecimal, default=None)("len")
    + VBAR
    + pp.Word(pp.alphanums + "+/=")[1, ...].setParseAction(
        lambda t: b64decode("".join(t))
    )
    + VBAR
).setParseAction(verify_length)

real = pp.Regex(r"[+-]?\d+\.\d*([eE][+-]?\d+)?").setParseAction(
    lambda tokens: float(tokens[0])
)
token = pp.Word(pp.alphanums + "-./_:*+=!<>")
qString = pp.Group(
    pp.Optional(decimal, default=None)("len")
    + pp.dblQuotedString.setParseAction(pp.removeQuotes)
).setParseAction(verify_length)

simpleString = real | base64_ | raw | decimal | token | hexadecimal | qString

display = LBRK + simpleString + RBRK
string_ = pp.Optional(display) + simpleString

sexp = pp.Forward()
sexpList = pp.Group(LPAR + sexp[...] + RPAR)
sexp <<= string_ | sexpList

#
# ------------------------Start of my code-------------------------
#

# See: https://dev-docs.kicad.org/en/file-formats/sexpr-schematic/

def clean_single_lists(myList):
    if len(myList)>1:
        return myList
    else:
        return clean_single_lists(myList[0])

def sch_traverse(propertyList):

    buildingDict = {}

    for x in propertyList:

        # the first item in each list is the keyword used for matching
        match x.pop(0):
            case "kicad_sch":
                return sch_traverse(x)

            case "sheet":
                buildingDict.setdefault("sheet", [])

                sheetDict = sch_traverse(x)
                buildingDict["sheet"].append(sheetDict)

            case "property":
                buildingDict.setdefault("property", {})

                sheetPropertyName = x.pop(0)
                sheetPropertyValue = x.pop(0)
                # otherData = sch_traverse(x) # Is just placement/format data
                buildingDict["property"][sheetPropertyName] = sheetPropertyValue
            
            case "uuid":
                buildingDict["uuid"] = x[0]
                
            # Add more types later

    return buildingDict

    
class kicadSchematic:
    def __init__(self, schematicFile: PurePath):
        if not isinstance(schematicFile, PurePath) :
            raise ValueError
        if not schematicFile.exists():
            raise FileNotFoundError
        
        self.__file = schematicFile
        with open(schematicFile, "r") as file:
            parsedList = sexp.parseString(file.read())
        
        self.__schDict = sch_traverse(parsedList)
        
    def get_subsch(self):
        return [ x for x in self.__schDict["sheet"]]

    def get_subsheet_files(self):
        return set([x["property"]["Sheetfile"] for x in self.get_sheets()])
    