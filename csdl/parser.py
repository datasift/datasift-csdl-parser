import pyparsing as pp
import re


class CSDLParser(object):

    """Expose the PyParsing exception as to avoid creating import dependencies downstream."""
    ParseException = pp.ParseBaseException

    def __init__(self):
        # supported operators
        operator = pp.Regex(r"<=|>=|<>|\!=|==|<|>|not|in|regex_partial|regex_exact|geo_box|geo_radius|geo_polygon|contains_any|contains_all|substr|contains_near|any|contains_substr|near|contains|wildcard").setName("operator").addParseAction(self.validateOperator)

        # literals
        number = pp.Regex(r"[+-]?\d+(:?\.\d*)?(:?[eE][+-]?\d+)?").setName("number")
        numberList = pp.Group(pp.Literal('[') + number + pp.ZeroOrMore("," + number) + pp.Literal(']')).setName("numberList")
        string = pp.dblQuotedString
        literals = number | numberList | string

        # symbols
        identifier = pp.Regex(r"[a-z][a-z_]+(?:\.[a-z][a-z_]+)*").addParseAction(self.validateIdentifier).setName("identifier")

        # we'll get there...
        subExpr = pp.Forward()

        # predicates
        stream = pp.Group(pp.Literal("stream") + string).setName("stream")
        exists = pp.Group(identifier + pp.Literal("exists")).setName("exists")

        # boolean predicates
        comparison = pp.Group(
            identifier + operator + literals
            | literals + operator + identifier
        ).setName("comparison")

        condition = comparison | stream | exists | subExpr
        subExpr << pp.nestedExpr(content=condition)

        # standard boolean operator precedence
        expr = pp.operatorPrecedence(condition,[
            (pp.CaselessLiteral("not"), 1, pp.opAssoc.RIGHT, ),
            (pp.CaselessLiteral("AND"), 2, pp.opAssoc.LEFT, ),
            (pp.CaselessLiteral("OR"), 2, pp.opAssoc.LEFT, ),
            ])

        # tag "thing" { expr }
        tag = pp.Group(pp.Literal("tag") + pp.quotedString + pp.nestedExpr("{", "}", expr)).setName("tag")

        # return { expr }
        a_return = pp.Group(pp.Literal("return") + pp.nestedExpr("{", "}", expr)).setName("return")

        # a single expression or tag [, tag, ...] return { expression }
        parser = expr | (pp.OneOrMore(tag) + a_return)

        # handle multilines
        parser.setDefaultWhitespaceChars(" \t\n\r")

        # handle // comments
        parser.ignore("//" + pp.restOfLine)
        self.parser = parser

    def parseString(self, s):
        """Parses a given string into an AST."""
        return self.parser.parseString(s)

    def validateIdentifier(self, tokens):
        """Called for every identifier parsed."""
        return tokens

    def validateOperator(self, tokens):
        """Called for every operator parsed."""
        return tokens

    def flatten(self, expr):
        a = []
        contains_sub_expr = False
        if isinstance(expr, list):
            for ex in expr:
                cv, v = self.flatten(ex)
                contains_sub_expr = contains_sub_expr or cv
                if cv:
                    a.append("(")
                    a.append(v)
                    a.append(")")
                else:
                    a.append(v)
        else:
            return False, expr
        return contains_sub_expr, " ".join(a)

parser = CSDLParser()
