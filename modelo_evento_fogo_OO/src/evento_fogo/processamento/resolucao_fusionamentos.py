
from shared.models.evento import Eventos as EventoFogo


class ResolvedorFusionamentos:

    def resolver_grupo(
        self,
        grupo: list[EventoFogo],
    ) -> tuple[EventoFogo, list[EventoFogo]]:

        if not grupo:
            raise ValueError(
                "Não é possível resolver um grupo vazio."
            )

        evento_absorvedor = min(
            grupo,
            key=lambda evento: (
                evento.data_inicio,
                -evento.quantidade_focos(),
                (
                    evento.id_evento
                    if evento.id_evento is not None
                    else float("inf")
                ),
            ),
        )

        eventos_absorvidos = [
            evento
            for evento in grupo
            if evento is not evento_absorvedor
        ]

        return evento_absorvedor, eventos_absorvidos

    def resolver_grupos(
        self,
        grupos: list[list[EventoFogo]],
    ) -> list[tuple[EventoFogo, list[EventoFogo]]]:

        return [
            self.resolver_grupo(grupo)
            for grupo in grupos
        ]
    