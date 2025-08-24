def _maybe_check_api_secret(request=None) -> None:
    # Auth-Check disabled (public mode)
    return


class Settings:
    # Minimal settings, ignore unknown env vars
    def __init__(self):
        self.public = True
        self.auth = False


# Global settings instance
settings = Settings()
