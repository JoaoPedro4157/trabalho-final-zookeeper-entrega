from threading import Event

from kazoo.client import KazooState


PREFIXO = "pedido-"


class LockDistribuido:
    def __init__(self, zk, fila):
        self.zk = zk
        self.fila = fila
        self.sessao_interrompida = Event()
        self._mudanca_na_fila = Event()
        self.zk.add_listener(self._mudou_estado)

    def _mudou_estado(self, estado):
        if estado in (KazooState.SUSPENDED, KazooState.LOST):
            self.sessao_interrompida.set()
            self._mudanca_na_fila.set()

    def _notificar(self, _evento):
        self._mudanca_na_fila.set()

    def verificar_conexao(self):
        if self.sessao_interrompida.is_set() or not self.zk.connected:
            raise RuntimeError("Conexão interrompida durante a tentativa de lock.")

    def solicitar(self, cliente):
        self.verificar_conexao()
        self.zk.ensure_path(self.fila)
        return self.zk.create(
            f"{self.fila}/{PREFIXO}",
            cliente.encode("utf-8"),
            ephemeral=True,
            sequence=True,
        )

    def aguardar_turno(self, pedido, registrar_espera):
        meu_nome = pedido.rsplit("/", 1)[-1]

        while True:
            self.verificar_conexao()
            pedidos = [
                nome for nome in self.zk.get_children(self.fila)
                if nome.startswith(PREFIXO)
            ]
            pedidos.sort(key=lambda nome: int(nome.removeprefix(PREFIXO)))
            if meu_nome not in pedidos:
                raise RuntimeError("O pedido do cliente desapareceu da fila.")

            posicao = pedidos.index(meu_nome)
            if posicao == 0:
                self.verificar_conexao()
                return

            anterior = f"{self.fila}/{pedidos[posicao - 1]}"
            self._mudanca_na_fila.clear()
            self.verificar_conexao()
            if self.zk.exists(anterior, watch=self._notificar) is None:
                continue

            registrar_espera(anterior)
            if not self._mudanca_na_fila.wait(timeout=30):
                raise RuntimeError("Tempo limite de espera pelo predecessor.")

    def liberar(self, pedido):
        self.verificar_conexao()
        self.zk.delete(pedido)