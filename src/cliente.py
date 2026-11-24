import argparse
import math
import os
from datetime import datetime
from time import monotonic_ns

from kazoo.client import KazooClient
from kazoo.exceptions import KazooException
from kazoo.handlers.threading import KazooTimeoutError

from lock_distribuido import LockDistribuido


FILA = "/locks/trabalho-final"


def registrar(cliente, evento, pedido, detalhe=""):
    instante = monotonic_ns()
    horario = datetime.now().astimezone().isoformat(timespec="milliseconds")
    print(
        f"{instante} {horario} {os.getpid()} {cliente} {evento} {pedido} {detalhe}".rstrip(),
        flush=True,
    )


def main():
    parser = argparse.ArgumentParser(description="Demonstração de um lock com ZooKeeper")
    parser.add_argument("cliente", choices=("P1", "P2", "P3"))
    parser.add_argument("--segundos", type=float, default=3)
    args = parser.parse_args()
    if not math.isfinite(args.segundos) or args.segundos <= 0:
        parser.error("--segundos deve ser um número positivo e finito")

    zk = KazooClient(hosts=os.environ.get("ZK_HOSTS", "127.0.0.1:2181"))
    lock = LockDistribuido(zk, FILA)
    pedido = "-"

    try:
        zk.start(timeout=5)
        pedido = lock.solicitar(args.cliente)
        registrar(args.cliente, "PEDIDO", pedido)
        lock.aguardar_turno(
            pedido,
            lambda anterior: registrar(args.cliente, "ESPERA", pedido, anterior),
        )

        registrar(args.cliente, "ENTRADA", pedido)
        if lock.sessao_interrompida.wait(args.segundos):
            raise RuntimeError("Sessão interrompida na seção crítica simulada.")
        lock.verificar_conexao()
        registrar(args.cliente, "SAIDA", pedido)

        lock.liberar(pedido)
        registrar(args.cliente, "LIBERADO", pedido)
        return 0
    except (KazooException, KazooTimeoutError, RuntimeError) as erro:
        registrar(args.cliente, "ERRO", pedido, str(erro))
        return 1
    finally:
        zk.stop()
        zk.close()


if __name__ == "__main__":
    raise SystemExit(main())