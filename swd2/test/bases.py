from test.bases import WorldTestBase

from .. import SWD2World


class SWD2TestBase(WorldTestBase):
    game = "SteamWorld Dig 2"
    world: SWD2World
