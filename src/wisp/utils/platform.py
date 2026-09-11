import enum
import platform


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
