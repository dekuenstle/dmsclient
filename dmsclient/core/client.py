import requests

from datetime import datetime
from .models import Profile, Product, Comment, Event, SaleEntry

__all__ = ['DmsClient']


class DmsClient:
    def __init__(self, token, api_endpoint):
        if token and len(token) > 1:
            self.token = token
        else:
            raise ValueError('Please provide a valid token.')

        self.api_endpoint = api_endpoint

    def _construct_sale_entries(self, dicts):
        profiles = {p.id: p for p in self.profiles}
        products = {p.id: p for p in self.products}
        return [SaleEntry(id=d['id'],
                          profile=profiles[d['profile']],
                          product=products[d['product']],
                          date=datetime.strptime(d['date'],
                                                 '%Y-%m-%dT%H:%M:%S.%f'))
                for d in dicts]

    def _construct_comments(self, dicts):
        profiles = {p.id: p for p in self.profiles}
        return [Comment(profile=profiles[d['profile']],
                        comment=d['comment']) for d in dicts]

    @property
    def profiles(self):
        return self._get('/profiles/', Profile)

    @property
    def current_profile(self):
        return self.profile_by_id('current')

    @property
    def orders(self):
        return self._construct_sale_entries(self._get('/order/'))

    @property
    def sale(self):
        return self.sale_history()

    @property
    def products(self):
        return self._get('/products/', Product)

    @property
    def events(self):
        return self._get('/events/', Event)

    @property
    def comments(self):
        return self._construct_comments(self._get('/comments/'))

    def sale_history(self, num_days=None):
        if num_days is None:
            num_days = ''
        else:
            assert isinstance(num_days, int)
        return self._construct_sale_entries(
            self._get('/sale/{}'.format(num_days)))

    def profile_by_id(self, id):
        assert isinstance(id, int) or id == 'current'
        profile = self._get('/profiles/{}'.format(id), Profile)
        if id == 'current':  # Workaround for mistake in api
            return profile[0]
        else:
            return profile

    def product_by_id(self, id):
        assert isinstance(id, int)
        return self._get('/products/{}'.format(id), Product)

    def add_order(self, product_id, profile_id=None):
        assert isinstance(product_id, int)
        if profile_id is None:
            profile_id = self.current_profile.id
        else:
            assert isinstance(profile_id, int)

        return self._post('/order/',
                          {"profile": profile_id, "product": product_id})

    def add_sale(self, product_id, profile_id=None):
        assert isinstance(product_id, int)
        if profile_id is None:
            profile_id = self.current_profile.id
        else:
            assert isinstance(profile_id, int)

        return self._post('/sale/',
                          {"profile": profile_id, "product": product_id})

    def add_comment(self, comment, profile_id=None):
        assert isinstance(comment, str)
        if profile_id is None:
            profile_id = self.current_profile.id
        else:
            assert isinstance(profile_id, int)

        return self._post('/comments/', {"profile": profile_id,
                                         "comment": comment})

    def add_event(self, name, price_group, is_active):
        return self._post('/events/', {"name": name,
                                       "price_group": price_group,
                                       "active": is_active})

    def _handle_error(self, r):
        try:
            r.raise_for_status()
        except requests.HTTPError as e:
            try:
                error = r.json()
                raise Exception(error, e)
            except Exception as e2:
                raise e2

    def _get(self, api, constructor=None):
        r = requests.get(self.api_endpoint + api,
                         headers={'Authorization': 'Token '+self.token})

        if r.status_code == 200:
            dicts = r.json()
            if constructor is None:
                return dicts
            else:
                if isinstance(dicts, dict):
                    return constructor(**dicts)
                else:
                    return [constructor(**d) for d in dicts]
        else:
            self._handle_error(r)

    def _post(self, api, data):
        r = requests.post(self.api_endpoint + api,
                          json=data,
                          headers={'Authorization': 'Token '+self.token})
        if r.status_code == 201:
            if r.text is not None and len(r.text) > 0:
                return r.json()
        else:
            self._handle_error(r)
