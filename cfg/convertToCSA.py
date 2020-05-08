#!/usr/bin/python3
import subprocess
import sys
import xml.etree.ElementTree as ET
import re
from io import StringIO


Builtin = [
    'int',
    'size_t',
    'char',
    'unsigned',
    'signed',
    'long',
    'short',
    'void',
    'float',
    'double',
    'const',
    'volatile',
    'restrict'
]


def decr(nr):
    return str(int(nr) - 1)


def transferType(ty):
    ty = list(filter(None, ty.split(' ')))
    res = ''

    for subty in ty:
        if subty != '*' and subty not in Builtin:
            return 'Irrelevant'

    for subty in ty:
        if subty == '*':
            res += 'Ptr'
        elif subty == "size_t":
            res += 'Size'
        elif subty in Builtin:
            res += subty.capitalize()
    res += 'Ty'
    return res


root = ET.parse(sys.argv[1]).getroot()
for function in root.findall('function'):

    pureness = "NoEvalCall"
    if function.find('pure') is not None:
        pureness = "EvalCallAsPure"

    names = function.get('name')
    for name in names.split(","):

        if name.endswith("_l"):
            continue

        if name.startswith("std::"):
            continue

        old_stdout = sys.stdout
        sys.stdout = mystdout = StringIO()

        # Get the signature that is in a comment. Unfortunately comments are
        # skipped from the XML during read.
        sign = subprocess.run(
            ['/bin/grep', '-P', '\\b' + str(name) + '\\(.*\\)\s*;', sys.argv[1]],
            stdout=subprocess.PIPE)
        sign = sign.stdout.decode('utf-8')
        sign = sign.replace(
            '<!--',
            '').replace(
            '-->',
            '').replace(
            '\n',
            '').strip()

        Ret = ''
        Args = []
        if (len(sign)):
            print("// " + sign)
            # Strip of names of args.
            sign = re.sub(r'\w+,', r',', sign)
            sign = re.sub(r'\w+\)', r')', sign)
            # Strip off name of fun.
            sign = re.sub(r'\w+\(', r'(', sign)
            # pointers
            sign = re.sub(r'(\S+)\*', r'\1 *', sign)
            # sign = re.sub(r'\*(\w+)', r'* \1', sign)
            # print("// " + sign)
            # Get the return type.
            Ret = sign.split('(')[0]
            # print("Ret: ", Ret)
            Ret = transferType(Ret)
            # print("Ret: ", Ret)
            Args = sign[sign.find('(') + 1: sign.rfind(')')]
            Args = Args.split(',')
            # print("Args: ", Args)
            Args = [transferType(i) for i in Args]
            # print("Args: ", Args)

        # sys.stdout = old_stdout
        # print(mystdout.getvalue())
        # continue

        print('addToFunctionSummaryMap("{}"\nSummary(ArgTypes{{{}}}, RetType{{{}}}, {})'.
              format(str(name), ','.join(Args), Ret, pureness))

        # print("addToFunctionSummaryMap(\"" + str(name) +
              # # "\",\nSummary(ArgTypes{}, RetType{}, " + pureness + ")")
              # "\",\nSummary(" + pureness + ")")

        returnValue = function.find('returnValue')
        returnValueConstraint = None
        if returnValue is not None:
            if returnValue.text is not None:  # returnValue constraint
                returnValueConstraint = returnValue.text
        if returnValueConstraint is not None:
            print(".Case({})".format(returnValue.text))

        args = function.findall('arg')
        for arg in args:
            if arg is not None:
                nr = arg.get('nr')
                if nr is None or nr == 'any':
                    continue
                nr = decr(nr)

                notnull = arg.find('not-null')
                if notnull is not None:
                    print(".ArgConstraint(NotNull(ArgNo(" + nr + ")))")

                valid = arg.find('valid')
                if valid is not None:
                    if valid.text.endswith(':'):
                        l = valid.text.split(':')
                        print(
                            ".ArgConstraint(ArgumentCondition({}, WithinRange, Range({}, Max)))".format(
                                nr, l[0]))
                    else:
                        print(
                            ".ArgConstraint(ArgumentCondition({}, WithinRange, Range({})))".format(
                                nr, valid.text))

                minsize = arg.find('minsize')
                if minsize is not None:
                    mstype = minsize.get('type')
                    if mstype == 'argvalue':
                        print(
                            ".ArgConstraint(BufferSize({},{}))".format(
                                nr, decr(minsize.get('arg'))))
                    if mstype == 'mul':
                        print(
                            ".ArgConstraint(BufferSize({},{},{}))".format(
                                nr, decr(
                                    minsize.get('arg')), decr(
                                    minsize.get('arg2'))))

        print(");")

        # Print only non-trivial summaries.
        sys.stdout = old_stdout
        if ".ArgConstraint" in mystdout.getvalue() or ".Case" in mystdout.getvalue():
            print(mystdout.getvalue())
