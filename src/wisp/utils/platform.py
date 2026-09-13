import enum
import platform
import subprocess
from pathlib import Path


class PlatformEnum(enum.StrEnum):
    LINUX = "Linux"
    WINDOWS = "Windows"
    MACOS = "Darwin"

    @staticmethod
    def get_platform() -> "PlatformEnum":
        system = platform.system().lower()
        match system:
            case "linux":
                return PlatformEnum.LINUX
            case "windows":
                return PlatformEnum.WINDOWS
            case "darwin":
                return PlatformEnum.MACOS
            case _:
                raise ValueError(f"Unsupported platform: {system}")


def secure_file(path: Path, platform_enum: PlatformEnum | None = None) -> None:
    """Restrict a sensitive file to SYSTEM and built-in Administrators on Windows,
    or to the owner only on Linux and macOS.

    For Linux and macOS, this sets the file permissions to 600 (read/write for owner only).
    For Windows, uses well-known SIDs instead of literal account names because the
    display names ("Administrators", "SYSTEM") are localized on non-English
    Windows installations, which makes icacls fail to resolve them by name
    """

    if platform_enum is None:
        platform_enum = PlatformEnum.get_platform()

    match platform_enum:
        case PlatformEnum.LINUX | PlatformEnum.MACOS:
            path.chmod(0o600)
        case PlatformEnum.WINDOWS:
            subprocess.run(
                [
                    "icacls",
                    str(path),
                    "/inheritance:r",
                    "/grant:r",
                    "*S-1-5-18:F",  # NT AUTHORITY\SYSTEM
                    "*S-1-5-32-544:F",  # BUILTIN\Administrators
                ],
                check=True,
                capture_output=True,
                text=True,
            )
        case _:
            raise ValueError(f"Unsupported platform: {platform_enum}")
