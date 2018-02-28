"""Drink Management System Client.

Usage:
  dms show (user|users|orders|products|events|comments)
  dms show [-d <d>] sale
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


def print_sale_entries(dms, sale_entries):
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


def print_comments(dms, comments):
    table = ((comment.profile.name, comment.comment)
             for comment in comments)
    print(tabulate(sorted(table), headers=['Profile', 'Text']))


def print_events(events):
    table = ((event.name, event.price_group, event.active)
             for event in events)
    print(tabulate(sorted(table), headers=['Name', 'Price Group', 'Active']))


def show(client, args):
    if args['user']:
        print_users([client.current_profile])
    elif args['users']:
        print_users(client.profiles)
    elif args['orders']:
        print_sale_entries(client, client.orders)
    elif args['sale']:
        days = int(args['--days'])
        print_sale_entries(client, client.sale_history(days))
    elif args['products']:
        print_products(client.products)
    elif args['comments']:
        print_comments(client, client.comments)
    elif args['events']:
        print_events(client.events)
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


def _general_sale(client, args, aliases, upper_type, function):
    product_query = ' '.join(args['<product>'])

    choices = dms.search_product(client, product_query, aliases)
    product = select_element(choices, product_query, lambda x: x.name)

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
    _general_sale(client, args, aliases, 'Order', client.add_order)


def buy(client, aliases, args):
    _general_sale(client, args, aliases, 'Buy', client.add_sale)


def comment(client, args):
    text = ' '.join(args['<text>'])
    user_id = None
    user_query = args['--user']
    if user_query is not None:
        u_choices = dms.search_profile(client, user_query)
        user_id = select_element(u_choices, user_query, lambda x: x.name).id
    client.add_comment(text, user_id)
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


def main():
    args = docopt(__doc__, version='dmsclient {}'.format(dms.__version__))
    config = load_config()
    client = dms.DmsClient(config.token, config.api)

    if args['show']:
        show(client, args)
    elif args['order']:
        order(client, config.aliases, args)
    elif args['buy']:
        buy(client, config.aliases, args)
    elif args['comment']:
        comment(client, args)
    elif args['setup'] and args['completion']:
        docopt_completion('dms')
        print('-> start a new shell to test completion')
    else:
        raise NotImplementedError()

if __name__ == "__main__":
    main()
