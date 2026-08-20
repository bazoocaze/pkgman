"""
exceptions.py – generic pkgman errors with exit codes.
"""


class PkgmanError(Exception):
    """Generic pkgman error. Carries an exit code and a user-facing message.

    Raise from anywhere in the codebase; catch near main for a clean exit
    without a traceback.
    """

    def __init__(self, message: str, exit_code: int = 1) -> None:
        super().__init__(message)
        self.exit_code = exit_code