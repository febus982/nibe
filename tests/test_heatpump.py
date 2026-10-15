import unittest
from unittest.mock import Mock

import pytest

from nibe.coil import CoilData
from nibe.exceptions import CoilNotFoundException, ModelIdentificationFailed
from nibe.heatpump import HeatPump, Model, ProductInfo, Series


class HeatpumpTestCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.heat_pump = HeatPump(Model.F1255)
        await self.heat_pump.initialize()

        assert len(self.heat_pump._address_to_coil) > 100

    def test_get_coils(self):
        coils = self.heat_pump.get_coils()
        assert isinstance(coils, list)

    def test_get_coil_by_returns_same(self):
        coil_address = 40004

        a = self.heat_pump.get_coil_by_address(coil_address)
        b = self.heat_pump.get_coil_by_address(str(coil_address))

        assert coil_address == a.address

        assert a is b

        c = self.heat_pump.get_coil_by_name("bt1-outdoor-temperature-40004")

        assert a is c

    def test_get_missing_coil_raises_exception(self):
        with pytest.raises(CoilNotFoundException):
            self.heat_pump.get_coil_by_address(0xFFFF)

        with pytest.raises(CoilNotFoundException):
            self.heat_pump.get_coil_by_name("no-beer-today")

    def test_listener(self):
        mock = Mock()
        coil = self.heat_pump.get_coil_by_address(40004)
        self.heat_pump.subscribe(self.heat_pump.COIL_UPDATE_EVENT, mock)

        mock.assert_not_called()

        coil_data = CoilData(coil, 14)
        self.heat_pump.notify_coil_update(coil_data)

        mock.assert_called_with(coil_data)

    def test_listener_with_exception(self):
        mock = Mock(side_effect=Exception("Test exception that needs to be logged"))
        coil = self.heat_pump.get_coil_by_address(40004)
        self.heat_pump.subscribe(self.heat_pump.COIL_UPDATE_EVENT, mock)

        coil_data = CoilData(coil, 14)
        self.heat_pump.notify_coil_update(
            coil_data
        )  # Error should be logged but not thrown out


class HeatpumpIntialization(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.heat_pump = HeatPump()

    async def test_initalize_with_model(self):
        self.heat_pump.model = Model.F1255
        await self.heat_pump.initialize()
        self.heat_pump.get_coil_by_address(43420)
        assert self.heat_pump.model is Model.F1255

    async def test_initalize_with_product_info(self):
        product_info = ProductInfo("F1255-12 R", 0)
        self.heat_pump.product_info = product_info
        await self.heat_pump.initialize()
        self.heat_pump.get_coil_by_address(43420)
        assert self.heat_pump.product_info is product_info

    async def test_initalization_failed(self):
        with pytest.raises(AssertionError):
            await self.heat_pump.initialize()


@pytest.mark.parametrize(
    "model,series",
    [
        (Model.F370, Series.F),
        (Model.F372, Series.F),
        (Model.F470, Series.F),
        (Model.F730, Series.F),
        (Model.F750, Series.F),
        (Model.F1145, Series.F),
        (Model.F1155, Series.F),
        (Model.F1245, Series.F),
        (Model.F1255, Series.F),
        (Model.F1345, Series.F),
        (Model.F1355, Series.F),
        (Model.SMO20, Series.F),
        (Model.SMO40, Series.F),
        (Model.SMOS40, Series.S),
        (Model.VVM225, Series.F),
        (Model.VVM310, Series.F),
        (Model.VVM320, Series.F),
        (Model.VVM325, Series.F),
        (Model.VVM500, Series.F),
        (Model.VVMS320, Series.S),
        (Model.VVMS325, Series.S),
        (Model.VVMS500, Series.S),
        (Model.S320, Series.S),
        (Model.S325, Series.S),
        (Model.S330, Series.S),
        (Model.S332, Series.S),
        (Model.S735, Series.S),
        (Model.S1155, Series.S),
        (Model.S1255, Series.S),
        (Model.S1156, Series.S),
        (Model.S1256, Series.S),
        (Model.S2125, Series.S),
    ],
)
def test_series(model: Model, series: Series):
    heat_pump = HeatPump(model)
    assert heat_pump.series == series


class ProductInfoTestCase(unittest.TestCase):
    def test_identify_model(self):
        product_info = ProductInfo("F1255-12 R", 0)

        assert product_info.identify_model() == Model.F1255

        product_info = ProductInfo("F1155-16", 0)

        assert product_info.identify_model() == Model.F1155

    def test_identify_model_error(self):
        product_info = ProductInfo("Tehowatti Air", 0)

        with pytest.raises(ModelIdentificationFailed):
            product_info.identify_model()


if __name__ == "__main__":
    unittest.main()


@pytest.mark.parametrize(
    ("address", "title", "size", "factor", "write"),
    [
        (42506, "Desired room temperature for zone 1", "s32", 10, True),
        (42584, "Desired room temperature for zone 40", "s32", 10, True),
        (45010, "Supply Line Set Point Heating 1", "s16", 10, True),
        (45552, "Block new compressor", "u8", 1, True),
        (46015, "Energy price 00:00 - 01:00", "s32", 1, True),
        (46065, "Charging method hot water", "u8", 1, True),
        (32446, "Outd. liq. line sensor (BT39)", "s16", 10, False),
        (35209, "External reading of BT1 activated", "u8", 1, False),
        (35987, "External reading of BT50 activated", "u8", 1, False),
        # Holding variants are kept for firmwares that still expose them
        (45209, "External reading of BT1 activated", "u8", 1, True),
        (45987, "External reading of BT50 activated", "u8", 1, True),
    ],
)
async def test_smos40_firmware_registers(
    address: int, title: str, size: str, factor: int, write: bool
):
    heat_pump = HeatPump(Model.SMOS40)
    await heat_pump.initialize()
    coil = heat_pump.get_coil_by_address(address)
    assert coil.title == title
    assert coil.size == size
    assert coil.factor == factor
    assert coil.is_writable is write


async def test_smos40_hot_water_temperature_limits():
    heat_pump = HeatPump(Model.SMOS40)
    await heat_pump.initialize()
    for address in (40060, 40061, 40064, 40065):
        assert heat_pump.get_coil_by_address(address).max == 70.0
