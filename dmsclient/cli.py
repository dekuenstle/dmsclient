"""Drink Management System Client.

Usage:
  dms show (user|users|orders|products|events|comments)
  dms show [-d <d>] sales
  dms (order|buy) [-f] [-n <n>] [-u <u>] <product>...
  dms comment [-u <u>] <text>...
  dms setup completion
  dms (-h | --help)
  dms --version

Options:
  -d <days>, --days=<days>  Number of days to show [default: 1].
  -f, --force               Don't ask for confirmation
  -h, --help                Show this screen.
  -n <n>, --number=<n>      Number of bottles
  -u <user>, --user=<user>  (Partial) user's name. E.g. 'stef' for 'Stefan'
  --version                 Show version.
"""
import asyncio
import os
import re
import configparser
import dmsclient as dms
from distutils.util import strtobool

from docopt import docopt
from tabulate import tabulate
from infi.docopt_completion.docopt_completion import docopt_completion


def print_users(users):
    table = ((user.first_name,
              user.last_name,
              "({})".format(user.user_name),
              user.allowed_buy)
             for user in users)
    print(tabulate(sorted(table), headers=['First Name', 'Last Name',
                                           'User Name', 'Allowed to Buy']))


def print_sale_entries(sale_entries):
    table = ((se.date.strftime('%d.%m.%Y %H:%M'),
              se.product.name,
              se.profile.name)
             for se in sale_entries)
    print(tabulate(
        sorted(
            table,
            reverse=True),
        headers=['Date', 'Product', 'Profile']))


def print_products(products):
    def make_price(price):
        """ Sometimes the price is not set. Do not fail in this case but return
        Unknown
        """
        if price is None:
            return "Unknown"
        else:
            return "{:.2f}€".format(price/100)
    table = ((product.name, product.quantity,
              make_price(product.price_cent))
             for product in products)
    print(tabulate(sorted(table), headers=['Name', 'Quantity', 'Price']))


def print_comments(comments):
    table = ((comment.profile.name, comment.comment)
             for comment in comments)
    print(tabulate(sorted(table), headers=['Profile', 'Text']))


def print_events(events):
    table = ((event.name, event.price_group, event.active)
             for event in events)
    print(tabulate(sorted(table), headers=['Name', 'Price Group', 'Active']))


async def show(loop, client, args):
    if args['user']:
        print_users([await client.current_profile])
    elif args['users']:
        print_users(await client.profiles)
    elif args['orders']:
        orders = loop.create_task(client.orders)
        profiles = loop.create_task(client.profiles)
        products = loop.create_task(client.products)
        print_sale_entries(
            dms.construct_sale_entries(
                await orders,
                await profiles,
                await products))
    elif args['sales']:
        days = int(args['--days'])
        sales = loop.create_task(client.sale_history(days))
        profiles = loop.create_task(client.profiles)
        products = loop.create_task(client.products)
        print_sale_entries(
            dms.construct_sale_entries(
                await sales,
                await profiles,
                await products))
    elif args['products']:
        print_products(await client.products)
    elif args['comments']:
        comments = loop.create_task(client.comments)
        profiles = loop.create_task(client.profiles)
        print_comments(
            dms.construct_comments(
                await comments,
                await profiles))
    elif args['events']:
        print_events(await client.events)
    else:
        raise NotImplementedError()


def select_yes_no(question, default_yes=True):
    if default_yes is None:
        question += ' [yes/no] '
    elif default_yes:
        question += ' [YES/no] '
    else:
        question += ' [yes/NO] '

    answer = input(question).strip().lower()
    if answer == '' and default_yes is not None:
        return default_yes
    try:
        return strtobool(answer)
    except ValueError:
        print("Only answer with yes or no.")
        exit(1)


def select_element(choices, query, accessor=None):
    if len(choices) > 5:
        print("Way too many like '{}' found.".format(query))
        exit(1)
    elif len(choices) > 1:
        for i, c in enumerate(choices):
            if accessor:
                print("({}) {}".format(i+1, accessor(c)))
            else:
                print("({}) {}".format(i+1, c))
        choice_id = int(input("Please enter a number between 1 and {}: "
                              .format(len(choices)))) - 1
        if choice_id < 0 or choice_id >= len(choices):
            print("Out of range, stupid.")
            exit(1)
        return choices[choice_id]
    elif len(choices) == 1:
        return choices[0]
    elif len(choices) == 0:
        print("Nothing like '{}' found.".format(query))
        exit(1)


def _query_products(client, product_query, aliases):
    try:
        prod_num = int(product_query)
        products = [client.product_by_id(prod_num)]
    except ValueError:
        products = dms.search_product(client, product_query, aliases)
    except Exception:
        products = []

    return products

async def _query_profiles(client, query):
    try:
        if query is None:
            users = [await client.current_profile]
        else:
            user_id = int(query)
            users = [await client.profile_by_id(user_id)]
    except ValueError:
        users = dms.search_profile(query, await client.profiles)

    return users


def _general_sale(client, args, product, upper_type, function):
    user_query = args['--user']
    if user_query is not None:
        u_choices = dms.search_profile(client, user_query)
        user = select_element(u_choices, user_query, lambda x: x.name)
        user_id = user.id
        user_name = user.name
    else:
        user_id = None

    if user_id is None or user_id == client.current_profile.id:
        user_name = 'yourself'

    if args['--number'] is None:
        number = 1
    else:
        number = int(args['--number'])

    if (args['--force'] or
        select_yes_no('{} {} {} ({:.2f}€) for {}?'
                      .format(upper_type,
                              number,
                              product.name,
                              product.price_cent/100,
                              user_name))):
        for _ in range(number):
            function(product.id, user_id)
        print("{} successful.".format(upper_type))
    else:
        print("Bye.")


def order(client, aliases, args):
    product_query = ' '.join(args['<product>'])
    products = _query_products(client, product_query, aliases)

    filtered = [p for p in products if p.quantity > 0]

    if len(filtered) == 0 and len(products) != 0:
        prod_names = [p.name for p in products]
        print("Sold out: {0}".format(", ".join(prod_names)))
        return
    else:
        product = select_element(filtered, product_query, lambda x: x.name)

    _general_sale(client, args, product, 'Order', client.add_order)


def buy(client, aliases, args):
    product_query = ' '.join(args['<product>'])
    products = _query_products(client, product_query, aliases)

    product = select_element(products, product_query, lambda x: x.name)
    _general_sale(client, args, product, 'Buy', client.add_sale)


async def comment(client, args):
    text = ' '.join(args['<text>'])
    user_query = args['--user']
    users = await _query_profiles(client, user_query)

    if len(users) == 1:
        user = users[0]
    else:
        users = dms.search_profile(user_query, users)
        user = select_element(users, user_query, lambda x: x.name)

    await client.add_comment(text, user.id)
    print("Comment successful.")


def load_config():
    rcfile = os.path.expanduser('~/.dmsrc')

    config = dms.DmsConfig()
    status = config.read(rcfile)
    if status == dms.ReadStatus.NOT_FOUND:
        print('Expected config at {}'. format(rcfile))
        if select_yes_no('Generate?'):
            print('Please enter your token:')
            print('(https://drinks.fachschaft.tf > MyAccount > REST Token)')
            config._set(dms.Sec.GENERAL, 'token', input())
            print('Generating...')
            config.write(rcfile)
        else:
            print('Bye.')
            exit(1)
    elif status == dms.ReadStatus.OUTDATED:
        print('Found config at {}'. format(rcfile))
        print('New version of config available.')
        if select_yes_no('Update config (recommended)?'):
            print('Updating...')
            config.write(rcfile)
    return config


async def async_main(loop):
    args = docopt(__doc__, version='dmsclient {}'.format(dms.__version__))
    config = load_config()

    async with dms.DmsClient(config.token, config.api) as client:
        if args['show']:
            await show(loop, client, args)
        elif args['order']:
            order(client, config.aliases, args)
        elif args['buy']:
            buy(client, config.aliases, args)
        elif args['comment']:
            await comment(client, args)
        elif args['setup'] and args['completion']:
            docopt_completion('dms')
            print('-> start a new shell to test completion')
        else:
            raise NotImplementedError()


def main():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(async_main(loop))


if __name__ == "__main__":
    main()
