from google.appengine.ext import db
from google.appengine.api import memcache
from datetime import datetime
from lib.pyparsing import Word, Keyword, alphas, ParseException, Literal, CaselessLiteral \
, Combine, Optional, nums, Or, Forward, ZeroOrMore, StringEnd, alphanums, oneOf \
, QuotedString, quotedString, removeQuotes, delimitedList, nestedExpr, Suppress, Group, Regex, operatorPrecedence \
, opAssoc
import math
import sys
import tools
from constants import *
import logging

class ExpressionParser(object):
    opMap = {
        "<" : lambda a,b : a < b,
        "<=" : lambda a,b : a <= b,
        ">" : lambda a,b : a > b,
        ">=" : lambda a,b : a >= b,
        "!=" : lambda a,b : a != b,
        "==" : lambda a,b : a == b,
        "AND" : lambda a,b : a and b,
        "OR" : lambda a,b : a or b
        # "NOT" : lambda x : not a
    }

    FUNCTIONS = [
        "SUM",
        "AVE",
        "MAX",
        "MIN",
        "COUNT",
        "ALARMS",
        "DISTANCE",
        "SQRT",
        "SINCE",
        "LAST_ALARM",
        "NOW",
        "DOT",
        "DELTA"
    ]

    def __init__(self, expr, column=None, analysis=None, run_ms=0, verbose=True):
        self.verbose = verbose
        if self.verbose:
            logging.debug("Building expression parser for %s" % expr)
        self.expr = expr
        self.column = column
        self.analysis = analysis
        self.run_ms = run_ms
        self.record_list = []
        self.alarm_list = []
        self.record = None
        # TODO: Pass prior record for accurate calcuations such as distance
        # self.prior_batch_last_record = prior_batch_last_record
        self.pattern = self._getPattern()
        logging.debug("Initialized expression parser with expression: %s" % expr)


    # Generator to extract operators and operands in pairs
    def operatorOperands(self, tokenlist):
        it = iter(tokenlist)
        while 1:
            try:
                yield (it.next(), it.next())
            except StopIteration:
                break

    def __normalizeNumeric(self, value):
        if not tools.is_numeric(value):
            # Handle unexpected text addition
            value = 0
        return value


    def __evalCurrentValue(self, toks):
        return self.analysis.columnValue(self.column, 0)

    def __evalAggregateColumn(self, toks):
        column = toks[0]
        if not self.record_list:
            raise Exception("Can't evaluate aggregate column without record list")
        if column == 'ts':
            res = [tools.unixtime(r.dt_recorded) for r in self.record_list]
        else:
            res = [r.columnValue(column, 0) for r in self.record_list]
        return [res]

    def __evalSingleColumn(self, toks):
        column = toks[0]
        if not self.record:
            raise Exception("Can't evaluate single column with no record")
        val = self.record.columnValue(column)
        return val

    def __multOp(self, toks):
        value = toks[0]
        _prod = self.__normalizeNumeric(value[0])
        for op,val in self.operatorOperands(value[1:]):
            if op == '*': _prod *= val
            if op == '/':
                _prod /= val
        return _prod

    def __expOp(self, toks):
        value = toks[0]
        res = self.__normalizeNumeric(value[0])
        for op,val in self.operatorOperands(value[1:]):
            if op == '^': res = pow(res, val)
        return res

    def __addOp(self, toks):
        value = toks[0]
        _sum = self.__normalizeNumeric(value[0])
        for op,val in self.operatorOperands(value[1:]):
            if op == '+': _sum += val
            if op == '-': _sum -= val
        return _sum

    def __evalLogicOp(self, toks):
        args = toks[0]
        if self.verbose:
            logging.debug(args)
        val1 = args[0]
        for op, val in self.operatorOperands(args[1:]):
            fn = self.opMap[op]
            val2 = val
            val1 = fn(val1, val2)
        return val1

    def __evalComparisonOp(self, tokens):
        args = tokens[0]
        val1 = args[0]
        for op,val in self.operatorOperands(args[1:]):
            fn = self.opMap[op]
            val2 = val
            if not fn(val1,val2):
                break
            val1 = val2
        else:
            return True
        return False

    def __evalString(self, toks):
        val = toks[0]
        return str(val).upper().strip()

    def __evalConstant(self, toks):
        return float(toks[0])

    def __getArglist(self, args):
        if type(args) is list:
            first = args[0]
            if type(first) is list:
                return first
            return args
        return []

    def __evalFunction(self, toks):
        val = toks[0]
        fnName = val[0].upper()
        args = val[1:]
        args = [arg for arg in args if arg is not None]  # Filter nones
        if not args:
            return 0
        if fnName == 'SUM':
            args = self.__getArglist(args)
            if args:
                return [sum(args)]
            return 0
        elif fnName == 'AVE':
            from tools import average
            args = self.__getArglist(args)
            if args:
                return [average(args)]
            return 0
        elif fnName == 'MAX':
            args = self.__getArglist(args)
            if args:
                res = max(args)
                return [res]
            return 0
        elif fnName == "MIN":
            args = self.__getArglist(args)
            if args:
                return [min(args)]
            return 0
        elif fnName == "COUNT":
            args = self.__getArglist(args)
            return [len(args)]
        elif fnName == "ALARMS":
            from models import Alarm
            # Usage: ALARMS([rule_id])
            # Returns list of alarms in processed batch, optionally filtered by rule_id
            alarm_list = list(self.alarm_list)
            if args and type(args[0]) in [int, long, float]:
                rule_id = int(args[0])
                if rule_id:
                    alarm_list = [al for al in alarm_list if tools.getKey(Alarm, 'rule', al, asID=True) == rule_id]
            return alarm_list
        elif fnName == "DISTANCE":
            dist = 0
            last_gp = None
            args = self.__getArglist(args)
            for gp in args:
                gp = tools.safe_geopoint(gp)
                if last_gp and gp:
                    dist += tools.calcLocDistance(last_gp, gp)
                if gp:
                    last_gp = gp
            return dist  # m
        elif fnName == "SQRT":
            arg = args[0]
            return math.sqrt(arg)
        elif fnName == "SINCE":
            # Returns ms since event (argument), or 0 if none found
            event = args[0]
            since = 0
            now = self.run_ms
            try:
                if event:
                    if type(event) in [long, float]:
                        # Treat as ms timestamp
                        since = now - event
                    elif isinstance(event, basestring):
                        pass
                    elif event.kind() == 'Alarm':
                        since = now - tools.unixtime(event.dt_start)
                    elif event.kind() == 'Record':
                        since = now - tools.unixtime(event.dt_recorded)
            except Exception, e:
                logging.warning("Error in SINCE() - %s" % e)
            return since
        elif fnName == "LAST_ALARM":
            # Takes optional argument of rule ID to filter alarms
            from models import Alarm
            rule_id = None
            last_alarm = None
            if args:
                rule_id = int(args[0])
            alarm_list = list(self.alarm_list)
            if alarm_list:
                if rule_id:
                    alarm_list = [al for al in alarm_list if tools.getKey(Alarm, 'rule', al, asID=True) == rule_id]
                if alarm_list:
                    last_alarm = sorted(alarm_list, key=lambda al : al.dt_end, reverse=True)[0]
                else:
                    last_alarm = self.analysis.sensor.alarm_set.order("-dt_end").get()
            return [last_alarm]
        elif fnName == "NOW":
            return self.run_ms
        elif fnName == "DOT":
            # Calculate dot product. Args 1 and 2 must be numeric aggregate/lists of same size.
            res = 0
            if len(args) == 2:
                if type(args[0]) is list and type(args[1]) is list:
                    import numpy as np
                    res = np.dot(args[0], args[1])
            return [res]
        elif fnName == "DELTA":
            # Calculate delta between each item in an array.
            # Input: X = [1,2,2,2,5,6]
            # Delta: [2-1, 2-2, 2-2, 5-2, 6-5]
            # Result: [1, 0, 0, 3, 1]
            res = 0
            li = args[0]
            if type(li) is list:
                res = []
                for i, item in enumerate(li):
                    diff = 0 # TODO: Correct handling of edge diff (not actually 0)
                    if i+1 < len(li):
                        next = li[i+1]
                        diff = next - item
                    res.append(diff)
                return [res]
            else:
                return [None]
        return 0


    def _getPattern(self):
        arith_expr = Forward()
        comp_expr = Forward()
        logic_expr = Forward()
        LPAR, RPAR, SEMI = map(Suppress, "();")
        identifier = Word(alphas+"_", alphanums+"_")
        multop = oneOf('* /')
        plusop = oneOf('+ -')
        expop = Literal( "^" )
        compop = oneOf('> < >= <= != ==')
        andop = Literal("AND")
        orop = Literal("OR")
        current_value = Literal( "." )
        assign = Literal( "=" )
        # notop = Literal('NOT')
        function = oneOf(' '.join(self.FUNCTIONS))
        function_call = Group(function.setResultsName('fn') + LPAR + Optional(delimitedList(arith_expr)) + RPAR)
        aggregate_column = QuotedString(quoteChar='{', endQuoteChar='}')
        single_column = QuotedString(quoteChar='[', endQuoteChar=']')
        integer = Regex(r"-?\d+")
        real = Regex(r"-?\d+\.\d*")

        # quotedString enables strings without quotes to pass

        operand = \
            function_call.setParseAction(self.__evalFunction) | \
            aggregate_column.setParseAction(self.__evalAggregateColumn) | \
            single_column.setParseAction(self.__evalSingleColumn) | \
            ((real | integer).setParseAction(self.__evalConstant)) | \
            quotedString.setParseAction(self.__evalString).addParseAction(removeQuotes) | \
            current_value.setParseAction(self.__evalCurrentValue) | \
            identifier.setParseAction(self.__evalString)

        arith_expr << operatorPrecedence(operand,
            [
             (expop, 2, opAssoc.LEFT, self.__expOp),
             (multop, 2, opAssoc.LEFT, self.__multOp),
             (plusop, 2, opAssoc.LEFT, self.__addOp),
            ])

        # comp_expr = Group(arith_expr + compop + arith_expr)
        comp_expr << operatorPrecedence(arith_expr,
            [
                (compop, 2, opAssoc.LEFT, self.__evalComparisonOp),
            ])

        logic_expr << operatorPrecedence(comp_expr,
            [
                (andop, 2, opAssoc.LEFT, self.__evalLogicOp),
                (orop, 2, opAssoc.LEFT, self.__evalLogicOp)
            ])

        pattern = logic_expr + StringEnd()
        return pattern

    def _parse_it(self):
        if self.expr:
            # try parsing the input string
            try:
                logging.debug("Parsing: %s" % self.expr)
                memcache.set("1", 1)
                L = self.pattern.parseString(self.expr)
                memcache.delete("1")
                logging.debug("Parsed: %s" % L)
            except ParseException, err:
                L = ['Parse Failure', self.expr]
                if self.verbose:
                    logging.error('Parse Failure')
                    logging.error(err.line)
                    logging.error(" "*(err.column-1) + "^")
                    logging.error(err)
            except:
                e = sys.exc_info()[0]
                logging.error("Other error occurred in parse_it for < %s >: %s" % (self.expr, e))
            else:
                if self.verbose:
                    logging.debug("%s -> %s" % (self.expr, L[0]))
                return L[0]
        return None

    def run(self, record=None, record_list=None, alarm_list=None):
        self.record_list = record_list
        self.alarm_list = alarm_list
        self.record = record
        return self._parse_it()


