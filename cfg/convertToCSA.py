#!/usr/bin/python3
import subprocess
import sys
import xml.etree.ElementTree as ET
from io import StringIO


blacklist = [
    'strchr',
    'ctime',
    'fflush',
    'fputc',
    'fputs',
    'getenv',
    'printf',
    'setlocale',
    'signal',
    'strchr',
    'strerror',
    'strrchr',
    'system',
    'time',
    'tolower',
    'toupper',
    'va_copy',
    'va_end',
    'va_start',
    'wctomb',
    'memchr'
]

whitelist = [
'select',
'FD_ZERO',
'close',
'htons',
'socket',
'setsockopt',
'FD_ISSET',
'FD_SET',
'connect',
'stat',
'send',
'getsockname',
'poll',
'ntohs',
'accept',
'fstat',
'unlink',
'getaddrinfo',
'strtok_r',
'alarm',
'sendto',
'gettimeofday',
'listen',
'ioctl',
'clock_gettime',
'lseek',
'FD_CLR',
'strtok',
'socketpair',
'recvfrom',
'sigaction',
'setrlimit',
'getrlimit',
'getpid',
'gethostname',
'gethostbyname',
]


def decr(nr):
    return str(int(nr) - 1)


root = ET.parse(sys.argv[1]).getroot()
for function in root.findall('function'):

    pureness = "NoEvalCall"
    if function.find('pure') is not None:
        pureness = "EvalCallAsPure"

    names = function.get('name')
    for name in names.split(","):

        if name.endswith("_l"):
            continue

        # if name in blacklist:
            # continue

        # if name not in whitelist:
            # continue

        if name.startswith("std::"):
            continue

        old_stdout = sys.stdout
        sys.stdout = mystdout = StringIO()

        # Get the signature that is in a comment. Unfortunately comments are
        # skipped from the XML during read.
        sign = subprocess.run(
            ['/bin/grep', str(name) + '(', sys.argv[1]],
            stdout=subprocess.PIPE)
        sign = sign.stdout.decode('utf-8')
        sign = sign.replace(
            '<!--',
            '').replace(
            '-->',
            '').replace(
            '\n',
            '').strip()
        print("// " + sign)

        print("addToFunctionSummaryMap(\"" + str(name) +
              # "\",\nSummary(ArgTypes{}, RetType{}, " + pureness + ")")
              "\",\nSummary(" + pureness + ")")

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
