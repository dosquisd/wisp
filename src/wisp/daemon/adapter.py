import subprocess
from abc import ABC, abstractmethod
from pathlib import Path

from wisp.utils import PlatformEnum, logger


class BaseAdapter(ABC):
    WG_CONF_PATH: Path
    __type: PlatformEnum

    @staticmethod
    def _run(cmd: list[str]) -> subprocess.CompletedProcess:
        """Run a command, raising on non-zero exit, capturing text output."""
        logger.debug(f"[daemon] running: {' '.join(cmd)}")
        return subprocess.run(cmd, check=True, text=True, capture_output=True)

    @abstractmethod
    def connect(self, config_content: str) -> subprocess.CompletedProcess:
        """Connect the local tunnel using the given WireGuard config content."""
        raise NotImplementedError(
            f"{self.__class__.__name__}.connect() must be implemented by subclasses"
        )

    @abstractmethod
    def disconnect(self) -> subprocess.CompletedProcess:
        """Disconnect the local tunnel."""
        raise NotImplementedError(
            f"{self.__class__.__name__}.disconnect() must be implemented by subclasses"
        )

    @abstractmethod
    def status(self) -> subprocess.CompletedProcess:
        """Return the status of the local tunnel."""
        raise NotImplementedError(
            f"{self.__class__.__name__}.status() must be implemented by subclasses"
        )


class LinuxAdapter(BaseAdapter):
    WG_CONF_PATH: Path = Path("/etc/wireguard/wg0.conf")

    __type: PlatformEnum = PlatformEnum.LINUX

    def connect(self, config_content: str) -> subprocess.CompletedProcess:
        self.WG_CONF_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.WG_CONF_PATH.write_text(config_content)
        self.WG_CONF_PATH.chmod(0o600)
        return self._run(["wg-quick", "up", "wg0"])

    def disconnect(self) -> subprocess.CompletedProcess:
        """Disconnect the local tunnel."""
        return self._run(["wg-quick", "down", "wg0"])

    def status(self) -> subprocess.CompletedProcess:
        """Return the status of the local tunnel."""
        return subprocess.run(["wg", "show", "wg0"], capture_output=True, text=True)


class WindowsAdapter(BaseAdapter):
    WG_CONF_PATH: Path

    __type: PlatformEnum = PlatformEnum.WINDOWS

    def connect(self, config_content: str) -> subprocess.CompletedProcess:
        raise NotImplementedError("Windows adapter is not implemented yet.")

    def disconnect(self) -> subprocess.CompletedProcess:
        raise NotImplementedError("Windows adapter is not implemented yet.")

    def status(self) -> subprocess.CompletedProcess:
        raise NotImplementedError("Windows adapter is not implemented yet.")


class MacOSAdapter(BaseAdapter):
    WG_CONF_PATH: Path

    __type: PlatformEnum = PlatformEnum.MACOS

    def connect(self, config_content: str) -> subprocess.CompletedProcess:
        raise NotImplementedError("macOS adapter is not implemented yet.")

    def disconnect(self) -> subprocess.CompletedProcess:
        raise NotImplementedError("macOS adapter is not implemented yet.")

    def status(self) -> subprocess.CompletedProcess:
        raise NotImplementedError("macOS adapter is not implemented yet.")


def get_adapter() -> BaseAdapter:
    """Return the appropriate adapter for the current platform."""
    platform_enum = PlatformEnum.get_platform()
    match platform_enum:
        case PlatformEnum.LINUX:
            return LinuxAdapter()
        case PlatformEnum.WINDOWS:
            return WindowsAdapter()
        case PlatformEnum.MACOS:
            return MacOSAdapter()
        case _:
            raise ValueError(f"Unsupported platform: {platform_enum}")
