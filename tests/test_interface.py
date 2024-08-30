import logging

from powerfactory_tools.versions.pf2024 import PowerFactoryInterface


class TestInterface:
    def test_init(self, caplog):
        with caplog.at_level(logging.INFO):
            PowerFactoryInterface(
                project_name="test",
            )

            assert "Could not start PowerFactory Interface. Shutting down..." in caplog.text
            assert "Closing PowerFactory Interface..." in caplog.text
            assert "Closing PowerFactory Interface... Done." in caplog.text
