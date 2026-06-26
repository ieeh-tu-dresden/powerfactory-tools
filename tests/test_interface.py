import logging

from powerfactory_tools.versions.pf2026 import PowerFactoryInterface


class TestInterface:
    def test_init_with_project_name(self, caplog, monkeypatch):
        # Patch out module loading, app connection and project join to avoid
        # requiring the real PowerFactory binaries in CI/local dev.
        def _noop_load_powerfactory_module(*args, **kwargs) -> object:  # noqa: ARG001
            """No-op replacement that mimics loading the PowerFactory module.

            Accepts any args/kwargs to avoid linter warnings about unused
            parameters.
            """
            return object()

        monkeypatch.setattr(
            PowerFactoryInterface,
            "load_powerfactory_module_from_path",
            _noop_load_powerfactory_module,
        )

        def _noop_connect_to_app(*args, **kwargs) -> object:  # noqa: ARG001
            """No-op replacement for connecting to the PowerFactory app."""
            return object()

        monkeypatch.setattr(
            PowerFactoryInterface,
            "connect_to_app",
            _noop_connect_to_app,
        )

        def _noop_join_project(*args, **kwargs) -> None:  # noqa: ARG001
            """No-op replacement for PowerFactoryInterface.join_project used in tests.

            Accepts any positional and keyword arguments to avoid linter warnings
            about unused parameters while keeping the production interface
            unmodified.
            """
            return

        monkeypatch.setattr(
            PowerFactoryInterface,
            "join_project",
            _noop_join_project,
        )

        with caplog.at_level(logging.INFO):
            # Use the interface as a context manager so __exit__ calls close()
            project_name = "test"
            with PowerFactoryInterface(project_name=project_name):
                # nothing to do inside the context, just trigger enter/exit
                pass

            assert "Starting PowerFactory Interface ..." in caplog.text
            assert "Starting PowerFactory Interface ... Done." in caplog.text
            ## due to the no-op monkeypatching, the following commented out error logs can't be collected as AttributeError is not catched in interface.
            ## Thus we can only check that the interface attempts to start and close properly:
            # assert "Could not start PowerFactory Interface. Shutting down ..." in caplog.text
            # assert "Could not activate project." in caplog.text
            # assert "Could not find PowerFactory Module." in caplog.text
            assert "Closing PowerFactory Interface ..." in caplog.text
            assert "Closing PowerFactory Interface ... Done." in caplog.text
