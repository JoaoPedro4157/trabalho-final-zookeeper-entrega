# Exclusão mútua distribuída com Apache ZooKeeper

Trabalho final de Sistemas Distribuídos I. Um servidor ZooKeeper local coordena o acesso de processos Python a uma seção crítica simulada. Os experimentos mostram o acesso de um único cliente e a disputa entre três clientes independentes.

## Ambiente utilizado

| Componente | Versão |
| --- | --- |
| Linux Mint | 22.3 |
| OpenJDK | 17.0.21.1 |
| Apache ZooKeeper | 3.8.8, modo standalone |
| Python | 3.12.3 |
| Kazoo | 2.11.0 |

## Preparar o ambiente

Execute os comandos a partir da raiz do projeto. No Linux Mint, instale as dependências do sistema se necessário:

~~~bash
sudo apt update && sudo apt install curl openjdk-17-jre-headless python3-venv
~~~

Em uma instalação nova, baixe o pacote binário, confira o SHA-512 e extraia-o na pasta do usuário:

~~~bash
arquivo=apache-zookeeper-3.8.8-bin.tar.gz
pasta_download=$(mktemp -d)

(
    cd "$pasta_download" &&
    curl -fLO "https://dlcdn.apache.org/zookeeper/zookeeper-3.8.8/$arquivo" &&
    curl -fLO "https://downloads.apache.org/zookeeper/zookeeper-3.8.8/$arquivo.sha512" &&
    sha512sum -c "$arquivo.sha512" &&
    mkdir -p "$HOME/.local/opt/trabalho-final-zookeeper" &&
    tar -xzf "$arquivo" -C "$HOME/.local/opt/trabalho-final-zookeeper"
)
~~~

Defina `ZK_DIR` no terminal e use este bloco para configurar uma instalação nova. Se ela já estiver configurada, defina somente `ZK_DIR` e vá para a inicialização.

~~~bash
ZK_DIR="$HOME/.local/opt/trabalho-final-zookeeper/apache-zookeeper-3.8.8-bin"
mkdir -p "$ZK_DIR/data"

cat > "$ZK_DIR/conf/zoo.cfg" <<EOF
tickTime=2000
dataDir=$ZK_DIR/data
clientPort=22181
clientPortAddress=127.0.0.1
admin.enableServer=false
EOF
~~~

Inicialize o servidor e confira a versão e o modo:

~~~bash
"$ZK_DIR/bin/zkServer.sh" version
"$ZK_DIR/bin/zkServer.sh" start
"$ZK_DIR/bin/zkServer.sh" status
~~~

O status deve mostrar `Mode: standalone` e o endereço `127.0.0.1:22181`. Para confirmar o acesso pelo cliente oficial, execute `"$ZK_DIR/bin/zkCli.sh" -server 127.0.0.1:22181` e, após `CONNECTED`, rode:

~~~text
create /teste-ambiente pronto
get /teste-ambiente
delete /teste-ambiente
ls /
quit
~~~

O `get` deve retornar `pronto`. Depois da remoção, `ls /` deve listar a raiz sem `teste-ambiente`.

Na raiz do repositório, prepare o Python:

~~~bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
~~~

## Como funciona o lock

`src/cliente.py` abre uma sessão no ZooKeeper para cada execução do programa. `src/lock_distribuido.py` registra cada pedido como um znode efêmero e sequencial em `/locks/trabalho-final`.

1. O servidor atribui um número sequencial a cada pedido.
2. O cliente com o menor número ativo entra na seção crítica. Os demais observam o pedido imediatamente anterior na fila.
3. Quando esse pedido desaparece, o cliente notificado consulta a fila novamente.
4. Ao sair da seção crítica simulada, o cliente apaga seu próprio znode e registra `LIBERADO`. Se a sessão terminar, o ZooKeeper remove os znodes efêmeros associados a ela.

Os testes usam uma pausa como operação da seção crítica. O `Event` do Python apenas transmite a notificação dentro do processo. A ordem e a decisão de entrada são determinadas pela fila no ZooKeeper.

## Executar os testes

Com o ZooKeeper ligado, defina o endereço da instância e execute os scripts, um por vez.

~~~bash
export ZK_HOSTS=127.0.0.1:22181
bash scripts/teste_individual.sh
bash scripts/teste_concorrente.sh
~~~

Os dois logs incluídos em `resultados/` são da gravação de 24 de novembro de 2026. Uma nova execução substitui os respectivos logs.

Cada linha registra o tempo monotônico em nanossegundos, o horário local, o PID, o cliente, o evento e o pedido. Nas linhas de `ESPERA`, o último campo é o caminho do predecessor observado.

### Teste individual

O script executa `P1` e salva a saída em `resultados/individual.log`. Na gravação, o PID `10175` criou o pedido `0000000004`, entrou às `16:23:19.176`, saiu às `16:23:21.176` e registrou `LIBERADO` às `16:23:21.181`. Os quatro eventos apareceram em ordem:

~~~text
PEDIDO → ENTRADA → SAIDA → LIBERADO
~~~

### Teste concorrente

O script inicia três processos e salva a saída combinada em `resultados/concorrente.log`. Na gravação, os três pedidos chegaram em cerca de três milissegundos. Os intervalos registrados foram:

| Cliente | PID | Sufixo do pedido | Entrada | Saída |
| --- | ---: | --- | --- | --- |
| P1 | 10378 | `0000000005` | 16:24:36.927 | 16:24:39.927 |
| P2 | 10379 | `0000000006` | 16:24:39.938 | 16:24:42.939 |
| P3 | 10380 | `0000000007` | 16:24:42.952 | 16:24:45.952 |

Enquanto `P1` estava na seção crítica, `P2` observava o pedido de `P1` e `P3` observava o de `P2`. Cada cliente entrou após a saída do anterior. Os três registraram `LIBERADO` e a fila ficou vazia. Em outra execução, a ordem dos identificadores pode variar, pois o ZooKeeper ordena pelo número do pedido.

Para inspecionar a fila depois dos testes, execute `"$ZK_DIR/bin/zkCli.sh" -server "$ZK_HOSTS"` e use `ls /locks/trabalho-final`. O resultado esperado com todos os clientes encerrados é `[]`. Para parar o servidor após os testes, execute `"$ZK_DIR/bin/zkServer.sh" stop`.

## Referências

- [Receita de locks do Apache ZooKeeper](https://zookeeper.apache.org/doc/r3.8.8/recipes.html)
- [Guia do cliente de linha de comando](https://zookeeper.apache.org/doc/r3.8.8/zookeeperCLI.html)
- [Documentação do Kazoo](https://kazoo.readthedocs.io/en/latest/basic_usage.html)
