# APP COPA LOGÍSTICA 2026

Sistema web de gamificação e acompanhamento de pontuação da campanha promocional **Copa Logística 2026** para operações de entrega.

## Sobre o Projeto

Aplicação web desenvolvida para engajar entregadores e dar transparência em tempo real durante campanhas de metas e incentivos:

* **Entregadores (Drivers):** Consulta individual de pontuação, posição atual no ranking, critérios de desempate e extrato detalhado de pontos conquistados por turno.
* **Gestão Operacional (Admin):** Painel gerencial com ranking completo dos entregadores, filtros por modal e métricas consolidadas de desempenho.

### Período da Campanha

**08/06/2026** até **19/07/2026**

### Estrutura de Premiação (Exemplo)

| Posição | Prêmio |
| :--- | :--- |
| 1º lugar | R\$ 10.000 |
| 2º lugar | R\$ 6.000 |
| 3º lugar | R\$ 4.000 |
| 4º e 5º | R\$ 2.000 cada |
| 6º e 7º | R\$ 1.000 cada |
| 8º ao 15º | R\$ 500 cada |

## Tecnologias

* **Python 3.10+**
* **Streamlit** — Interface web responsiva (mobile-first para entregadores)
* **Pandas** — Processamento, regras de negócio e cálculos de pontuação
* **PyArrow** — Leitura otimizada em formato colunar Parquet
* **OpenPyXL** — Suporte a planilhas Excel na ingestão de dados

## Estrutura do Projeto

```text
app_promo/
├── app.py                              # Ponto de entrada principal
├── assets/
│   └── style.css                       # Tema visual (dark mode)
├── data/
│   ├── base_entregadores.parquet       # Base cadastral de entregadores
│   ├── perfomance_entregadores.parquet # Histórico de turnos e performance
│   ├── bolao_participantes.parquet     # Pontuação extra do bolão
│   └── jogos_copa.parquet              # Calendário de partidas da campanha
├── src/
│   ├── login.py                        # Autenticação segregada (Driver / Admin)
│   ├── driver.py                       # Painel individual do entregador
│   └── admin.py                        # Painel administrativo da operação
├── requirements.txt                    # Dependências do projeto
└── README.md
```

## Instalação e Execução Local

### 1. Clone o repositório

```bash
git clone https://github.com/owlboy13/app-copa-logistica.git
cd app-copa-logistica/app_promo
```

### 2. Crie e ative o ambiente virtual

```bash
python -m venv venv_promo

# Linux / Mac
source venv_promo/bin/activate

# Windows
venv_promo\Scripts\activate
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. Prepare os dados

Certifique-se de que os 4 arquivos `.parquet` (`base_entregadores.parquet`, `perfomance_entregadores.parquet`, `bolao_participantes.parquet` e `jogos_copa.parquet`) estejam dentro da pasta `data/`.

### 5. Execute a aplicação

```bash
streamlit run app.py
```

O sistema estará disponível em `http://localhost:8501`.

## Acessos (Modo Demonstração)

### Entregador (Driver)

* **URL:** `http://localhost:8501`
* **CPF de teste:** `11111111111` (ou qualquer CPF fictício gerado na base de demonstração)

### Administrador (Gestão)

* **URL:** `http://localhost:8501/?admin=1`
* **Login:** CNPJ + Senha configurados via variáveis de ambiente ou em `src/login.py`

> **Nota de Privacidade:** Todos os dados incluídos na base de demonstração deste repositório são 100% sintéticos/fictícios.

## Regras de Pontuação

| Critério | Pontos | Elite (2x) |
| :--- | :--- | :--- |
| Turno jogo Brasil\* | +10 | +20 |
| Turno Final\* | +10 | +20 |
| Tempo online $\ge 75\%$ | +5 | +10 |
| Aceitação $\ge 75\%$ | +3 | +6 |
| Conclusão $\ge 95\%$ | +2 | +4 |
| Cada turno atuado | +1 | +2 |
| Bolão da Copa | +1 | +2 |

*\*Mediante cumprimento dos critérios operacionais da campanha.*

### Critérios de Desempate

1. Maior número de pedidos entregues
2. Menor número de corridas rejeitadas

## Esquema dos Dados

### `base_entregadores.parquet`

| Coluna | Tipo | Descrição |
| :--- | :--- | :--- |
| `ID` | `str` (UUID) | Identificador único do entregador |
| `Nome` | `str` | Nome completo |
| `CPF` | `str` | Documento utilizado no login |
| `Modal` | `str` | Tipo de veículo (`Moto`, `Bike`) |
| `ELITE` | `str` | `SIM` / `NÃO` (multiplicador $2\times$ nos pontos) |

### `perfomance_entregadores.parquet`

| Coluna | Descrição |
| :--- | :--- |
| `id_da_pessoa_entregadora` | Chave estrangeira relacionada ao `ID` da base |
| `data_do_periodo` | Data de referência do turno |
| `tempo_disponivel_escalado` | Tempo total escalado (minutos) |
| `tempo_disponivel_absoluto` | Tempo efetivo online (minutos) |
| `duracao_do_periodo` | Duração da janela do turno |
| `numero_de_corridas_aceitas` | Total de corridas aceitas |
| `numero_de_corridas_ofertadas` | Total de corridas ofertadas |
| `numero_de_corridas_rejeitadas` | Total de corridas rejeitadas |
| `numero_de_corridas_completadas` | Total de corridas finalizadas |
| `numero_de_pedidos_aceitos_e_concluidos` | Total de entregas concluídas com sucesso |

## Licença

Este projeto está sob a licença MIT.