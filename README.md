# VRP — Distribuição de Medicamentos e Insumos (RMSP)

Sistema de otimização de rotas para distribuição de medicamentos e insumos hospitalares
na Região Metropolitana de São Paulo, desenvolvido como Tech Challenge Fase 2 — FIAP Pós-Tech.

O sistema resolve o **Problema de Roteamento de Veículos (VRP)** usando um **Algoritmo Genético**,
com duas formas de execução: interface desktop (Pygame) e aplicação web (FastAPI + Leaflet.js),
com suporte a deploy em nuvem via **Azure Container Apps**.

🌐 **Demo online:** https://vrp-rmsp.nicerock-a43e5f49.brazilsouth.azurecontainerapps.io

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
- [Visualização Desktop](#visualização-desktop)
- [Interface Web](#interface-web)
- [API REST](#api-rest)
- [Integração com LLM](#integração-com-llm)
- [Testes Automatizados](#testes-automatizados)
- [Deploy no Azure](#deploy-no-azure)
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
| Interface web com mapa Leaflet interativo | `api/templates/index.html` |
| API REST para execução headless do AG | `api/main.py` |
| Integração com LLM (relatórios, instruções) | `llm_report.py` → `generate_report()` |
| Testes automatizados (unitários e de restrição) | `tests/test_*.py` — 58 testes, 100% aprovados |
| Relatório gerencial de testes via LLM | `generate_test_report.py` |
| Refinamento local (2-opt) | `core/fitness.py` → `two_opt()` |
| Dataset real (39 cidades RMSP) | `benchmark_greater_sp.py` |
| Deploy em nuvem (Azure Container Apps) | `Dockerfile`, `deploy_azure.ps1` |

---

## Arquitetura do Projeto

```
genetic_algorithm_tsp/
│
├── tsp.py                    # Entry point desktop — loop AG + visualização Pygame
├── genetic_algorithm.py      # Operadores genéticos: crossover OX, mutação, ordenação
├── draw_functions.py         # Visualização: gráficos fitness/KM e rotas no mapa
├── benchmark_greater_sp.py   # Dataset: 39 municípios da RMSP com lat/lon
├── llm_report.py             # Integração LLM: relatórios operacionais das rotas
├── generate_test_report.py   # Executa testes + gera relatório gerencial via LLM
├── map_background.py         # Download e cache de tiles OpenStreetMap
├── environment.yml           # Ambiente Conda com todas as dependências
├── requirements_api.txt      # Dependências da API web
├── Dockerfile                # Imagem Docker para deploy em nuvem
├── deploy_azure.ps1          # Script de deploy no Azure (primeira vez)
├── update_azure.ps1          # Script de atualização no Azure
│
├── api/
│   ├── main.py               # FastAPI — endpoints REST + serve a página web
│   ├── runner.py             # AG headless (sem Pygame) para execução via API
│   └── templates/
│       └── index.html        # Interface web: Leaflet.js + Chart.js + polling
│
├── core/
│   ├── algorithm.py          # Geração de população inicial (aleatória, NN, convex)
│   └── fitness.py            # Função fitness multiobjetivo + refinamento 2-opt
│
├── domain/
│   ├── models.py             # Entidades: DeliveryPoint, Vehicle, Route
│   └── problem.py            # VRPProblem — agrega depot, pontos e frota
│
├── tests/
│   ├── test_genetic_algorithm.py  # Testes: order_crossover, mutate, sort_population
│   ├── test_decoder.py            # Testes: VRPDecoder — prioridade, capacidade, autonomia
│   └── test_fitness.py            # Testes: calculo_fitness, route_distance, two_opt
│
└── vrp/
    └── decoder.py            # Decodifica cromossomo → rotas respeitando restrições
```

---

## Pré-requisitos

- Python **3.9** ou superior
- [Anaconda](https://www.anaconda.com/download) ou [Miniconda](https://docs.conda.io/en/latest/miniconda.html) (recomendado para modo desktop)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (necessário apenas para deploy no Azure)
- [Azure CLI](https://aka.ms/installazurecliwindows) (necessário apenas para deploy no Azure)

---

## Instalação

### Opção 1 — Conda (recomendado para modo desktop)

```bash
cd genetic_algorithm_tsp
conda env create --file environment.yml
conda activate fiap_tsp
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

pip install pygame matplotlib numpy requests pillow
```

### Para o modo web (API)

```bash
pip install fastapi uvicorn
```

### Configuração da chave OpenAI

```bash
cp .env.example .env
# Edite o .env e adicione:
# OPENAI_API_KEY=sk-sua-chave-aqui
```

---

## Como Executar

### Modo Desktop (Pygame)

```bash
cd genetic_algorithm_tsp
python tsp.py
```

Na primeira execução, o sistema baixa os tiles do mapa OpenStreetMap para `.map_cache/`.

**Controles:**
- `Q` ou fechar a janela → encerra
- `L` → gera relatório LLM da solução atual (salvo em `relatorios/`)
- O sistema encerra automaticamente após **400 gerações sem melhoria**

### Modo Web (FastAPI)

```bash
cd genetic_algorithm_tsp
uvicorn api.main:app --reload --port 8000
```

Abra no navegador: **http://localhost:8000**

A interface permite configurar parâmetros via sliders, acompanhar a evolução em tempo real,
visualizar as rotas no mapa interativo, executar testes e gerar relatórios LLM.

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

### O que é o Fitness

O fitness é um número entre 0 e 1 que representa a qualidade da solução — **quanto menor, melhor**.
Não é a distância em KM diretamente, mas uma combinação ponderada de 4 componentes normalizados:

| Componente | Peso | O que mede |
|---|---|---|
| Distância total | 0.55 | KM percorridos por todos os veículos |
| Penalidade de prioridade | 0.15 | Cidades críticas visitadas tarde |
| Balanceamento de carga | 0.05 | Variância de carga entre veículos |
| Fragmentação de rotas | 0.25 | Número de rotas (evita muitas viagens curtas) |

A normalização garante que nenhum componente domine por diferença de escala.
Por exemplo, `Fitness: 0.6091` com `KM: 711` significa que o AG ainda não convergiu para
a melhor solução — o `Melhor: 0.6043` registrado anteriormente é a solução preservada.

### Mecanismo anti-estagnação

Quando o melhor fitness global não melhora por **160 gerações consecutivas**
(40% do limite), metade da população é substituída por indivíduos aleatórios —
forçando exploração de novas regiões do espaço de busca.

### Critério de parada

O algoritmo encerra quando o **melhor fitness global** não melhora por
**400 gerações consecutivas** (modo desktop) ou pelo valor configurado nos sliders (modo web).

O critério de parada compara `best_global` com o valor da geração anterior (`previous_global`),
garantindo que somente melhorias reais zeram o contador. O melhor cromossomo é preservado em
`best_solution_ever` — independente dos restarts parciais, a melhor solução nunca é perdida
e é exibida no mapa ao convergir.

---

## Restrições Implementadas

| Restrição | Como funciona |
|---|---|
| **Capacidade** | Quando `carga_atual + demand > vehicle.capacity`, fecha a rota e avança para o próximo veículo |
| **Autonomia** | Quando `distância + próximo + retorno_depot > max_distance`, fecha a rota |
| **Múltiplos veículos** | O decoder avança sequencialmente pela frota ao fechar cada rota |
| **Prioridade garantida** | `_sort_by_priority()` reordena o cromossomo antes de decodificar |
| **Balanceamento** | A função fitness penaliza alta variância de carga entre rotas |

### Configuração dos veículos

| Veículo | Capacidade | Perfil |
|---|---|---|
| V1 | 150 unid. | Leve — atendimento local |
| V2 | 150 unid. | Leve — atendimento local |
| V3 | 500 unid. | Pesado — distribuição regional |

---

## Prioridades de Entrega

As prioridades são **fixas por cidade**, definidas no dicionário `CITY_PRIORITY` em `tsp.py`.
O decoder **garante estruturalmente** que cidades críticas sejam sempre visitadas primeiro.

| Cidade | Prioridade | Nível |
|---|---|---|
| São Paulo | 3 | Crítica ⚠ |
| Guarulhos | 3 | Crítica ⚠ |
| Santo André | 3 | Crítica ⚠ |
| Suzano | 3 | Crítica ⚠ |
| Mogi das Cruzes | 2 | Alta ⚡ |
| Mauá | 2 | Alta ⚡ |
| Demais 32 cidades | 1 | Normal |

---

## Visualização Desktop

A janela (1500×800px) é dividida em duas áreas:

**Lado esquerdo — Painéis de monitoramento:**
- Gráfico superior: evolução do fitness com **duas linhas**:
  - 🔵 Azul: fitness de cada geração (sobe e desce — mostra exploração do espaço de busca)
  - 🔴 Vermelho: melhor fitness global acumulado (monotonicamente decrescente — mostra convergência)
- Gráfico inferior: distância em KM com **duas linhas**:
  - 🟠 Laranja: KM de cada geração (oscila conforme a exploração)
  - 🔴 Vermelho: melhor KM já encontrado (valor anotado na linha — só diminui)

**Lado direito — Mapa da RMSP:**
- Tiles reais do OpenStreetMap (cacheados em `.map_cache/`)
- Rotas coloridas por veículo: vermelho=V1, azul=V2, verde=V3
- Labels com fundo semitransparente
- Depósito (Barueri) marcado em verde

---

## Interface Web

A interface web roda em `http://localhost:8000` e oferece:

**Sidebar esquerda:**
- Sliders para configurar população, estagnação e taxa de mutação
- Barra de progresso e métricas em tempo real (geração, fitness, KM, estagnação)
- Gráficos de evolução do fitness e da distância atualizados ao vivo
- Ao convergir, a janela permanece aberta para análise — **pressione ENTER no terminal para fechar**
- Aba **Rotas**: painel detalhado com paradas, carga e distância por veículo
- Aba **Log**: console ao vivo com o progresso geração a geração
- Aba **Relatório LLM**: relatório operacional gerado ao convergir
- Aba **🧪 Testes**: executa os 58 testes + gera relatório gerencial via LLM

**Mapa interativo (Leaflet.js):**
- Tiles OpenStreetMap reais
- Rotas coloridas por veículo desenhadas ao convergir
- Markers com tooltip: nome da cidade, demanda e prioridade
- Zoom automático para enquadrar todas as rotas

---

## API REST

| Método | Endpoint | Descrição |
|---|---|---|
| `GET` | `/` | Página web principal |
| `POST` | `/otimizar` | Inicia o AG em background — retorna `job_id` |
| `GET` | `/status/{job_id}` | Progresso em tempo real (polling) |
| `GET` | `/resultado/{job_id}` | Resultado completo: rotas + relatório LLM |
| `GET` | `/jobs` | Lista todos os jobs |
| `DELETE` | `/jobs/{job_id}` | Cancela job em andamento |
| `POST` | `/testes/executar` | Executa os 58 testes + gera relatório LLM |
| `GET` | `/testes/status/{job_id}` | Status do job de testes |
| `GET` | `/health` | Healthcheck |
| `GET` | `/docs` | Swagger UI interativo |

```bash
# Exemplo: inicia otimização
curl -X POST http://localhost:8000/otimizar \
  -H "Content-Type: application/json" \
  -d '{"population_size": 50, "stagnation_stop": 150}'
```

---

## Integração com LLM

O sistema integra com **OpenAI GPT-4o-mini** para geração de relatórios operacionais.

### Quando é gerado

| Modo | Quando |
|---|---|
| Desktop | Automático ao convergir + tecla `L` |
| Web — Rotas | Automático ao convergir (aba Relatório LLM) |
| Web — Testes | Ao clicar em "Executar Testes" na aba 🧪 Testes |

### Relatório de rotas (4 seções)

1. **Instruções por Motorista** — sequência, quantidades e horários estimados (partindo às 08h)
2. **Relatório de Eficiência** — distância por veículo, taxa de utilização de capacidade
3. **Alertas de Prioridade Crítica** — confirmação das cidades críticas nas primeiras posições
4. **Resumo Executivo** — métricas principais e recomendações para o gestor

### Relatório de testes (5 seções)

1. Visão geral e importância dos testes
2. Estratégia de testes — módulos priorizados e justificativa
3. Regras de negócio validadas — explicação gerencial
4. Resultados obtidos — análise quantitativa
5. Conclusão e recomendações de evolução

Relatórios salvos em `relatorios/relatorio_YYYYMMDD_HHMMSS.txt`.

---

## Testes Automatizados

```bash
# Executa todos os 58 testes
python -m unittest discover -s tests -v
# Resultado: Ran 58 tests in 0.007s — OK

# Gera relatório gerencial via LLM
python generate_test_report.py
```

| Arquivo | Testes | O que cobre |
|---|---|---|
| `test_genetic_algorithm.py` | 22 | Crossover OX, mutação adjacent swap, ordenação por fitness |
| `test_decoder.py` | 19 | Prioridade crítica > alta > normal, capacidade, autonomia, múltiplos veículos |
| `test_fitness.py` | 17 | Fitness multiobjetivo, distância euclidiana, refinamento 2-opt |

---

## Deploy no Azure

### Pré-requisitos

- Docker Desktop instalado e rodando
- Azure CLI instalado
- Conta Azure com créditos ativos

### Deploy inicial

```powershell
# Libera execução de scripts
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned

# Registra namespaces (só na primeira vez)
az provider register --namespace Microsoft.ContainerRegistry --wait
az provider register --namespace Microsoft.App --wait

# Login
az login

# Build e push da imagem
docker build -t vrprmspcr.azurecr.io/vrp-rmsp:latest .
docker push vrprmspcr.azurecr.io/vrp-rmsp:latest

# Deploy
az containerapp create `
    --name vrp-rmsp `
    --resource-group vrp-rmsp-rg `
    --environment vrp-rmsp-env `
    --image vrprmspcr.azurecr.io/vrp-rmsp:latest `
    --registry-server vrprmspcr.azurecr.io `
    --registry-username vrprmspcr `
    --registry-password (az acr credential show --name vrprmspcr --query "passwords[0].value" -o tsv) `
    --target-port 8000 --ingress external --min-replicas 1 --cpu 1.0 --memory 2.0Gi

# Injeta a chave OpenAI
az containerapp update `
    --name vrp-rmsp `
    --resource-group vrp-rmsp-rg `
    --set-env-vars "OPENAI_API_KEY=sk-sua-chave-aqui"
```

### Atualização após mudanças no código

```powershell
docker build -t vrprmspcr.azurecr.io/vrp-rmsp:latest .
docker push vrprmspcr.azurecr.io/vrp-rmsp:latest
az containerapp update --name vrp-rmsp --resource-group vrp-rmsp-rg --image vrprmspcr.azurecr.io/vrp-rmsp:latest
```

### Recursos no Azure

| Recurso | Nome | Região |
|---|---|---|
| Resource Group | `vrp-rmsp-rg` | Brazil South |
| Container Registry | `vrprmspcr` | Brazil South |
| Container Apps Environment | `vrp-rmsp-env` | Brazil South |
| Container App | `vrp-rmsp` | Brazil South |

> Para o guia completo com solução de problemas, consulte `deploy_azure_guia.txt`.

---

## Configurações Ajustáveis

Parâmetros em `tsp.py` (modo desktop) ou via sliders na interface web:

```python
POPULATION_SIZE = 100    # tamanho da população
TOURNAMENT_SIZE = 3      # candidatos por torneio
ELITE_SIZE      = 5      # indivíduos preservados por elitismo
STAGNATION_STOP = 400    # gerações sem melhoria para encerrar
MUTATION_START  = 0.30   # taxa de mutação inicial
MUTATION_MIN    = 0.05   # taxa de mutação mínima

CITY_PRIORITY = {
    "São Paulo":       3,   # crítica
    "Guarulhos":       3,   # crítica
    "Santo André":     3,   # crítica
    "Suzano":          3,   # crítica
    "Mogi das Cruzes": 2,   # alta
    "Mauá":            2,   # alta
}
```

Pesos da função fitness em `core/fitness.py`:

```python
w_distance = 0.55   # peso da distância total
w_priority = 0.15   # peso da penalidade de prioridade
w_balance  = 0.05   # peso do balanceamento de carga
w_routes   = 0.25   # peso da penalidade de fragmentação
```

---

*FIAP Pós-Tech — Inteligência Artificial para Devs — Fase 2 — Tech Challenge*
