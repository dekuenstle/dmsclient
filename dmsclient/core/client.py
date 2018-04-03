import aiohttp
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

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={
                'Authorization': 'Token ' + self.token,
                'Content-type': 'application/json'})
        return self

    async def __aexit__(self, *args):
        await self.session.close()

    @property
    async def profiles(self):
        return await self._get('/profiles/', Profile)

    @property
    async def current_profile(self):
        return await self.profile_by_id('current')

    @property
    async def orders(self):
        return await self._get('/orders/')

    @property
    async def sales(self):
        return await self.sale_history()

    @property
    async def products(self):
        return await self._get('/products/', Product)

    @property
    async def events(self):
        return await self._get('/events/', Event)

    @property
    async def comments(self):
        return await self._get('/comments/')

    async def sale_history(self, num_days=None):
        if num_days is None:
            num_days = ''
        else:
            assert isinstance(num_days, int)
        return await self._get('/sales/{}/'.format(num_days))

    async def profile_by_id(self, id):
        assert isinstance(id, int) or id == 'current'
        return await self._get('/profiles/{}/'.format(id), Profile)

    async def product_by_id(self, id):
        assert isinstance(id, int)
        return await self._get('/products/{}/'.format(id), Product)

    async def add_order(self, product_id, profile_id=None):
        assert isinstance(product_id, int)
        if profile_id is None:
            profile_id = await self.current_profile.id
        else:
            assert isinstance(profile_id, int)

        return await self._post(
            '/orders/',
            {"profile": profile_id, "product": product_id})

    async def add_sale(self, product_id, profile_id=None):
        assert isinstance(product_id, int)
        if profile_id is None:
            profile_id = await self.current_profile.id
        else:
            assert isinstance(profile_id, int)

        return await self._post(
            '/sales/',
            {"profile": profile_id, "product": product_id})

    async def add_comment(self, comment, profile_id=None):
        assert isinstance(comment, str)
        if profile_id is None:
            profile_id = await self.current_profile.id
        else:
            assert isinstance(profile_id, int)

        return await self._post(
            '/comments/',
            {"profile": profile_id, "comment": comment})

    async def add_event(self, name, price_group, is_active):
        return self._post(
            '/events/',
            {"name": name,
             "price_group": price_group,
             "active": is_active})

    async def _get(self, api, constructor=None):
        async with self.session.get(self.api_endpoint + api) as r:
            if not r.raise_for_status():
                dicts = await r.json()
                if constructor is None:
                    return dicts
                else:
                    if isinstance(dicts, dict):
                        return constructor(**dicts)
                    else:
                        return [constructor(**d) for d in dicts]

    async def _post(self, api, data):
        async with self.session.post(self.api_endpoint + api, json=data) as r:
            r.raise_for_status()
