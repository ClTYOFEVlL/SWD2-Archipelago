from .bases import SWD2TestBase


class TestFewCogsCheapShop(SWD2TestBase):
    options = {"cog_amount": 4, "shop_price_percent": 10}


class TestVanillaPrices(SWD2TestBase):
    options = {"shop_price_percent": "vanilla"}
