import re

from datetime import datetime
from .models import Comment, SaleEntry

__all__ = [
    'search_product', 'search_profile',
    'construct_sale_entries', 'construct_comments']


def search_product(query, products, aliases=None):
    """Search products retrieved from dms matching the query.
    Optionally provide a list of aliases of the structure (aliase, prod_name)
    """
    result = list()
    if aliases and len(aliases) > 0:
        alias_match = _search(query, aliases, lambda x: x[0])
        alias_names = [name for _, name in alias_match]
        result.extend([p for p in products if p.name in alias_names])

    prod_match = _search(query, products, lambda x: x.name)

    for p in prod_match:
        if p not in result:
            result.append(p)
    return result


def search_profile(query, profiles):
    profiles = [p for p in profiles if p.allowed_buy]

    def build_name(u): return "{} {} {}".format(
        u.first_name, u.last_name, u.user_name)

    return _search(query, profiles, build_name)


def _search(query, choices, accessor=None):
    """Search for matches of query in choices.
    query.match(choise)
    Optionally provide an accessor:
    query.match(accessor(choise))
    """
    if query is None:
        return choices

    regex = re.compile(query.replace("*", ".*").replace(" ", ".*"),
                       re.IGNORECASE | re.DOTALL)
    if accessor:
        def filter_(x): return regex.search(accessor(x)) is not None
    else:
        def filter_(x): return regex.search(x) is not None

    result = [c for c in choices if filter_(c)]
    return result


def construct_sale_entries(sales, profiles, products):
    profiles = {p.id: p for p in profiles}
    products = {p.id: p for p in products}
    return [SaleEntry(id=s['id'],
                      profile=profiles[s['profile']],
                      product=products[s['product']],
                      date=datetime.strptime(s['date'],
                                             '%Y-%m-%dT%H:%M:%S.%f'))
            for s in sales]


def construct_comments(comments, profiles):
    profiles = {p.id: p for p in profiles}
    return [Comment(profile=profiles[c['profile']],
                    comment=c['comment']) for c in comments]
