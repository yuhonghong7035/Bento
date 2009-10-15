from pyparsing import \
        Literal, WordStart, CharsNotIn, LineEnd, alphas, Word, \
        indentedBlock, OneOrMore, ZeroOrMore, OnlyOnce, \
        Group, empty, lineEnd, FollowedBy, col, alphanums, \
        Forward, Optional, delimitedList, \
        ParseException, ParseFatalException

#---------------------------------
#       Grammar definition
#---------------------------------
# Literals
colon = Literal(':').suppress()
string = WordStart() + CharsNotIn('\n')
word = Word(alphas)
newline = LineEnd().suppress()
module_name = word + ZeroOrMore(Literal('.') + word)

indent_stack = [1]

def checkPeerIndent(s,l,t):
    cur_col = col(l,s)
    if cur_col != indent_stack[-1]:
        if (not indent_stack) or cur_col > indent_stack[-1]:
            raise ParseFatalException(s, l, "illegal nesting")
        raise ParseException(s, l, "not a peer entry")

def checkSubIndent(s,l,t):
    cur_col = col(l,s)
    if cur_col > indent_stack[-1]:
        indent_stack.append(cur_col)
    else:
        raise ParseException(s, l, "not a subentry")

def checkUnindent(s,l,t):
    if l >= len(s):
        return
    cur_col = col(l,s)
    if not(cur_col < indent_stack[-1] and cur_col <= indent_stack[-2]):
        raise ParseException(s, l, "not an unindent")

def doUnindent():
    indent_stack.pop()

INDENT = lineEnd.suppress() + empty + empty.copy().setParseAction(checkSubIndent)
UNDENT = FollowedBy(empty).setParseAction(checkUnindent)
UNDENT.setParseAction(doUnindent)

stmt = Forward()
stmt.setParseAction(checkPeerIndent)

grammar = Group(OneOrMore(empty + stmt))

# metadata fields
name = Literal('Name')
name_definition = name + colon + word

summary = Literal('Summary')
summary_definition = summary + colon + string

indented_string = string.copy()
indented_string.setParseAction(checkPeerIndent)
multiline_string = Group(OneOrMore(empty + indented_string))

description_definition = Group(
        Literal("Description") + colon +
        INDENT + multiline_string + UNDENT)

metadata_field = (description_definition | name_definition | summary_definition)
stmt << metadata_field

#------------------------------
#       Parse actions
#------------------------------
def parse_name(s, loc, toks):
    print "= Name is =\n\t%s" % toks[1]

def parse_summary(s, loc, toks):
    print "= Summary is =\n\t%s" % toks[1]

def parse_description(s, loc, toks):
    print "= Description is =\n\t%s" % "\n\t".join([str(i) for i in toks[0][1]])

name_definition.setParseAction(parse_name)
summary_definition.setParseAction(parse_summary)
description_definition.setParseAction(parse_description)

if __name__ == '__main__':
    data = """\
Name: numpy
Description:
    NumPy is a general-purpose array-processing package designed to
    efficiently manipulate large multi-dimensional arrays of arbitrary
    records without sacrificing too much speed for small multi-dimensional
    arrays.  NumPy is built on the Numeric code base and adds features
    introduced by numarray as well as an extended C-API and the ability to
    create arrays of arbitrary type which also makes NumPy suitable for
    interfacing with general-purpose data-base applications.
    .
    There are also basic facilities for discrete fourier transform,
    basic linear algebra and random number generation.
Summary: array processing for numbers, strings, records, and objects.
"""
    grammar.parseString(data)
