# VRP — Distribuição de Medicamentos e Insumos (RMSP)

Sistema de otimização de rotas para distribuição de medicamentos e insumos hospitalares
na Região Metropolitana de São Paulo, desenvolvido como Tech Challenge Fase 2 — FIAP Pós-Tech.

O sistema resolve o **Problema de Roteamento de Veículos (VRP)** usando um **Algoritmo Genético**,
com visualização em tempo real das rotas sobre o mapa geográfico real da Grande SP (OpenStreetMap).

---

## Sumário

- [Contexto e Requisitos](#contexto-e-requisitos)
- [Arquitetura do Projeto](#arquitetura-do-projeto)
- [Pré-requisitos](#pré-requisitos)
- [Instalação](#instalação)
- [Como Executar](#como-executar)
- [Funcionamento do Algoritmo Genético](#funcionamento-do-algoritmo-genético)
- [Restrições Implementadas](#restrições-implementadas)
- [Prioridades de Entrega](#prioridades-de-entrega)
- [Visualização](#visualização)
- [Configurações Ajustáveis](#configurações-ajustáveis)

---

## Contexto e Requisitos

**Projeto escolhido:** Projeto 2 — Otimização de Rotas para Distribuição de Medicamentos e Insumos.

| Requisito do PDF | Onde está implementado |
|---|---|
| Representação genética adequada para rotas | `core/algorithm.py`, `vrp/decoder.py` |
| Operador de seleção (torneio) | `tsp.py` → `tournament_selection()` |
| Operador de crossover (OX) | `genetic_algorithm.py` → `order_crossover()` |
| Operador de mutação (adaptativa) | `genetic_algorithm.py` → `mutate()` |
| Função fitness: distância + prioridade + restrições | `core/fitness.py` → `calculo_fitness()` |
| Prioridades de entrega fixas por cidade | `tsp.py` → `CITY_PRIORITY` |
| Cidades críticas sempre visitadas primeiro | `vrp/decoder.py` → `_sort_by_priority()` |
| Capacidade limitada dos veículos | `domain/models.py` → `Vehicle.capacity` |
| Autonomia limitada dos veículos | `domain/models.py` → `Vehicle.max_distance` |
| Múltiplos veículos (VRP) | `vrp/decoder.py` → `VRPDecoder.decode()` |
| Visualização das rotas em mapa real (OSM) | `draw_functions.py`, `map_background.py` |
| Integração com LLM (relatórios, instruções) | `llm_report.py` → `generate_report()` |
| Refinamento local (2-opt) | `core/fitness.py` → `two_opt()` |
| Dataset real (39 cidades RMSP) | `benchmark_greater_sp.py` |

---

## Arquitetura do Projeto

```
genetic_algorithm_tsp/
│
├── tsp.py                    # Entry point — loop principal do AG e visualização
├── genetic_algorithm.py      # Operadores genéticos: crossover OX, mutação, ordenação
├── draw_functions.py         # Visualização: gráficos fitness/KM e rotas no mapa
├── benchmark_greater_sp.py   # Dataset: 39 municípios da RMSP com lat/lon
├── llm_report.py             # Integração LLM: geração de relatórios e instruções
├── map_background.py         # Download e cache de tiles OpenStreetMap
├── environment.yml           # Ambiente Conda com todas as dependências
│
├── core/
│   ├── algorithm.py          # Geração de população inicial (aleatória, NN, convex)
│   └── fitness.py            # Função fitness multiobjetivo + refinamento 2-opt
│
├── domain/
│   ├── models.py             # Entidades: DeliveryPoint, Vehicle, Route
│   └── problem.py            # VRPProblem — agrega depot, pontos e frota
│
└── vrp/
    └── decoder.py            # Decodifica cromossomo → rotas respeitando restrições
```

### Fluxo de dados

```
benchmark_greater_sp.py
        │  39 cidades (lat/lon)
        ▼
    tsp.py
        │  Cria VRPProblem (depot + delivery_points + vehicles)
        │  Define prioridades fixas via CITY_PRIORITY
        ▼
core/algorithm.py
        │  População inicial híbrida
        │  (30% aleatório + 30% nearest neighbour + 40% convex-like)
        ▼
    [loop AG]
        │
        ├─► vrp/decoder.py
        │       _sort_by_priority() → garante críticos primeiro
        │       decode()            → List[Route]
        │
        ├─► core/fitness.py
        │       calculo_fitness()   → score normalizado
        │       two_opt()           → refinamento local no melhor
        │
        ├─► genetic_algorithm.py
        │       sort_population(), tournament_selection()
        │       order_crossover(), mutate()
        │
        └─► draw_functions.py + map_background.py
                Renderiza mapa OSM + rotas coloridas + gráficos
```

---

## Pré-requisitos

- Python **3.9** ou superior
- [Anaconda](https://www.anaconda.com/download) ou [Miniconda](https://docs.conda.io/en/latest/miniconda.html) (recomendado)

---

## Instalação

### Opção 1 — Conda (recomendado)

```bash
# 1. Clone ou extraia o projeto
cd genetic_algorithm_tsp

# 2. Crie o ambiente com todas as dependências
conda env create --file environment.yml

# 3. Ative o ambiente
conda activate fiap_tsp

# 4. Instale dependências adicionais (mapa de fundo)
pip install requests pillow
```

### Opção 2 — pip + venv

```bash
cd genetic_algorithm_tsp

# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux/macOS
python -m venv .venv
source .venv/bin/activate

# Instale as dependências
pip install pygame matplotlib numpy requests pillow
```

### Dependências principais

| Pacote | Versão mínima | Uso |
|---|---|---|
| `pygame` | 2.0 | Janela de visualização e renderização |
| `matplotlib` | 3.5 | Gráficos de fitness e distância KM |
| `numpy` | 1.21 | Operações numéricas auxiliares |
| `requests` | 2.27 | Download de tiles OSM |
| `Pillow` | 9.0 | Processamento de imagens dos tiles |

---

## Como Executar

```bash
# Certifique-se de estar dentro da pasta do projeto com o ambiente ativo
cd genetic_algorithm_tsp
python tsp.py
```

**Na primeira execução**, o sistema baixa automaticamente os tiles do mapa
OpenStreetMap para a pasta `.map_cache/`. Isso pode levar alguns segundos.
As execuções seguintes carregam do cache e são instantâneas.

**Controles durante a execução:**
- `Q` ou fechar a janela → encerra o algoritmo
- O sistema encerra automaticamente após **400 gerações sem melhoria no melhor fitness global**

**Console durante a execução:**
```
Gen   45 | Fitness: 0.6353 | KM: 666.5 | Melhor: 0.6353 (12 sem melhoria)
[restart] Reinicializando 50 indivíduos para escapar do ótimo local...
Gen   46 | Fitness: 0.6201 | KM: 648.2 | Melhor: 0.6201 (0 sem melhoria)
```

---

## Funcionamento do Algoritmo Genético

### Representação
Cada **cromossomo** é uma permutação de IDs dos pontos de entrega.
O `VRPDecoder` converte essa permutação em rotas reais, sempre
colocando cidades críticas primeiro (`_sort_by_priority()`).

### Inicialização da população (híbrida)

| Estratégia | Proporção | Objetivo |
|---|---|---|
| Aleatória | 30% | Diversidade genética |
| Nearest Neighbour | 30% | Qualidade local |
| Convex-like (angular) | 40% | Estrutura geográfica |

### Operadores genéticos

| Operador | Implementação | Descrição |
|---|---|---|
| Seleção | Torneio (k=3) | Baixa pressão seletiva — preserva diversidade |
| Crossover | Order Crossover (OX) | Preserva ordem relativa, evita duplicatas |
| Mutação | Adjacent Swap adaptativa | Taxa sobe durante estagnação, desce com melhoria |
| Elitismo | Top-5 | Os 5 melhores são preservados a cada geração |
| Refinamento | 2-opt (5 iter.) | Aplicado ao melhor indivíduo de cada geração |

### Mecanismo anti-estagnação
Quando o melhor fitness global não melhora por **160 gerações consecutivas**
(40% do limite), metade da população é substituída por indivíduos aleatórios
novos — forçando exploração de novas regiões do espaço de busca.

### Critério de parada
O algoritmo encerra quando o **melhor fitness global** não melhora por
**400 gerações consecutivas**.

---

## Restrições Implementadas

| Restrição | Como funciona |
|---|---|
| **Capacidade** | Quando `carga_atual + demand > vehicle.capacity`, fecha a rota atual e avança para o próximo veículo |
| **Autonomia** | Quando `distância + próximo + retorno_depot > max_distance`, fecha a rota |
| **Múltiplos veículos** | O decoder avança sequencialmente pela frota ao fechar cada rota |
| **Prioridade garantida** | `_sort_by_priority()` reordena o cromossomo antes de decodificar |
| **Balanceamento** | A função fitness penaliza alta variância de carga entre rotas |

### Configuração dos veículos

| Veículo | Capacidade | Autonomia | Perfil |
|---|---|---|---|
| V1 | 150 unid. | 5000 px | Leve — atendimento local |
| V2 | 150 unid. | 5000 px | Leve — atendimento local |
| V3 | 500 unid. | 8000 px | Pesado — distribuição regional |

---

## Prioridades de Entrega

As prioridades são **fixas por cidade**, definidas no dicionário `CITY_PRIORITY` em `tsp.py`.
O decoder **garante estruturalmente** que cidades críticas sejam sempre visitadas antes
das de alta prioridade, que por sua vez são visitadas antes das normais.

| Cidade | Prioridade | Nível |
|---|---|---|
| São Paulo | 3 | Crítica |
| Guarulhos | 3 | Crítica |
| Santo André | 3 | Crítica |
| Suzano | 3 | Crítica |
| Mogi das Cruzes | 2 | Alta |
| Mauá | 2 | Alta |
| Demais 32 cidades | 1 | Normal |

Para alterar as prioridades, edite o dicionário `CITY_PRIORITY` em `tsp.py`.

---

## Visualização

A janela (1500×800px) é dividida em duas áreas:

**Lado esquerdo (450px) — Painéis de monitoramento:**
- Gráfico superior: evolução do **fitness normalizado** por geração
- Gráfico inferior: evolução da **distância total em KM reais** (fórmula Haversine)
  com o valor atual anotado e legenda de cores por veículo

**Lado direito — Mapa da RMSP:**
- Fundo: tiles reais do OpenStreetMap (cacheados em `.map_cache/`)
- Rotas coloridas por veículo: vermelho=V1, azul=V2, verde=V3
- Pontos com círculo duplo na cor do veículo
- Labels com fundo semitransparente: `Nº°VX NomeCidade`
- Depósito (Barueri) marcado em verde com círculo maior
- Margem de 60px em todas as bordas — cidades nunca cortadas


---

## Integração com LLM

O sistema integra com **OpenAI GPT-4o-mini** para geração automática de relatórios
operacionais ao final de cada execução do AG.

### Configuração da chave de API

```bash
# Copie o arquivo de exemplo
cp .env.example .env

# Edite e coloque sua chave (obtenha em https://platform.openai.com/api-keys)
OPENAI_API_KEY=sk-sua-chave-aqui
```

### Como ativar

| Quando | Como |
|---|---|
| **Automático** | Ao convergir, o relatório é gerado e salvo em `relatorios/` |
| **Manual** | Pressione **`L`** durante a execução para gerar a qualquer momento |

### O que é gerado

O LLM recebe o contexto completo da operação e gera 4 seções:

**1. Instruções por Motorista** — sequência de cidades, quantidades, horários estimados (partindo às 08h), destaque para entregas críticas com ⚠

**2. Relatório de Eficiência** — distância por veículo, taxa de utilização de capacidade, comparativo entre veículos

**3. Alertas de Prioridade Crítica** — confirmação de que São Paulo, Guarulhos, Santo André e Suzano estão nas primeiras posições, horários estimados de chegada

**4. Resumo Executivo** — 5 linhas para o gestor com métricas principais e recomendações operacionais

### Sem chave configurada

Se `OPENAI_API_KEY` não estiver definida, o sistema exibe o contexto estruturado
da operação (sem chamada LLM) e salva normalmente em `relatorios/`.

### Relatórios salvos

Cada execução salva um arquivo em `relatorios/relatorio_YYYYMMDD_HHMMSS.txt`.

---

## Configurações Ajustáveis

Todas as configurações principais estão no topo de `tsp.py`:

```python
# Algoritmo Genético
POPULATION_SIZE = 100    # tamanho da população
TOURNAMENT_SIZE = 3      # candidatos por torneio (menor = mais diversidade)
ELITE_SIZE      = 5      # indivíduos preservados por elitismo
STAGNATION_STOP = 400    # gerações sem melhoria para encerrar
MUTATION_START  = 0.30   # taxa de mutação inicial
MUTATION_MIN    = 0.05   # taxa de mutação mínima

# Prioridades por cidade
CITY_PRIORITY = {
    "São Paulo":       3,   # crítica
    "Guarulhos":       3,   # crítica
    "Santo André":     3,   # crítica
    "Suzano":          3,   # crítica
    "Mogi das Cruzes": 2,   # alta
    "Mauá":            2,   # alta
    # demais cidades → 1 (normal)
}

# Veículos
Vehicle(id=1, capacity=150, max_distance=5000)
Vehicle(id=2, capacity=150, max_distance=5000)
Vehicle(id=3, capacity=500, max_distance=8000)
```

Os pesos da função fitness podem ser ajustados em `core/fitness.py`:

```python
w_distance = 0.55   # peso da distância total
w_priority = 0.15   # peso da penalidade de prioridade
w_balance  = 0.05   # peso do balanceamento de carga
w_routes   = 0.25   # peso da penalidade de fragmentação
```
