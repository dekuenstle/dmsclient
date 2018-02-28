import re

__all__ = ['search_product', 'search_profile']


def search_product(client, query, aliases=None):
    """Search products retrieved from dms matching the query.
    Optionally provide a list of aliases of the structure (aliase, prod_name)
    """
    products = [p for p in client.products if p.quantity > 0]

    result = list()
    if aliases and len(aliases) > 0:
        alias_match = _search_interactive(query, aliases, lambda x: x[0])
        alias_names = [name for _, name in alias_match]
        result.extend([p for p in products if p.name in alias_names])

    prod_match = _search_interactive(query, products, lambda x: x.name)

    for p in prod_match:
        if p not in result:
            result.append(p)
    return result


def search_profile(client, user_query):
    profiles = [u for u in client.profiles if u.allowed_buy]

    def build_name(u): return "{} {} {}".format(
        u.first_name, u.last_name, u.user_name)

    return _search_interactive(user_query, profiles, build_name)


def _search_interactive(query, choices, accessor=None):
    """Search for matches of query in choices.
    query.match(choise)
    Optionally provide an accessor:
    query.match(accessor(choise))
    """
    regex = re.compile(query.replace("*", ".*").replace(" ", ".*"),
                       re.IGNORECASE | re.DOTALL)
    if accessor:
        def filter_(x): return regex.search(accessor(x)) is not None
    else:
        def filter_(x): return regex.search(x) is not None

    result = [c for c in choices if filter_(c)]
    return result
