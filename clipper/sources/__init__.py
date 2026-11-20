from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Candidato:
    """Um momento candidato a virar corte."""
    chave: str                 # id único (evita postar repetido)
    plataforma: str            # twitch | kick | youtube
    streamer: str              # nome exibido
    canal: str                 # login/slug/handle
    titulo: str
    url: str                   # link público do clipe/vídeo
    views: int
    criado_em: datetime
    duracao: float
    credito: str               # ex.: twitch.tv/fulano
    vod_id: Optional[str] = None
    vod_offset: Optional[float] = None
    extra: dict = field(default_factory=dict)

    def idade_horas(self, agora: datetime) -> float:
        return max((agora - self.criado_em).total_seconds() / 3600, 0)
