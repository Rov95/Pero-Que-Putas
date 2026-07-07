class ErrorAplicacion(Exception):
    def __init__(self, detalle: str, status_code: int = 400) -> None:
        self.detalle = detalle
        self.status_code = status_code
        super().__init__(detalle)
