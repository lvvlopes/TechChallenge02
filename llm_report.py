"""
llm_report.py
-------------
Integração com LLM (Anthropic Claude Haiku) para geração de relatórios
operacionais sobre as rotas otimizadas pelo Algoritmo Genético.

Requisito atendido (PDF – Projeto 2):
  - Integração com modelo de linguagem para geração de:
      * Instruções detalhadas por motorista
      * Relatório de eficiência operacional
      * Alertas de entregas críticas
      * Resumo executivo da operação
  - Ativação interativa via tecla L durante a visualização Pygame
  - Resultado salvo em arquivo .txt com timestamp

Configuração:
  Defina a variável de ambiente OPENAI_API_KEY antes de executar:
    Windows:  set OPENAI_API_KEY=sk-...
    Linux:    export OPENAI_API_KEY=sk-...

  Ou crie um arquivo .env na raiz do projeto:
    OPENAI_API_KEY=sk-...
"""

import os
import math
import datetime
from typing import List

from domain.models import Route, DeliveryPoint
from domain.problem import VRPProblem


# ── Constantes ────────────────────────────────────────────────────────────────
PRIORITY_LABEL = {1: "Normal", 2: "Alta", 3: "CRÍTICA"}
AVG_SPEED_KMH  = 40   # velocidade média urbana estimada para cálculo de tempo

# ── Chave da API ──────────────────────────────────────────────────────────────
# Cole sua chave OpenAI aqui — é a forma mais simples de configurar
# Obtenha em: https://platform.openai.com/api-keys
OPENAI_API_KEY_DIRECT = ""  # ex: "sk-proj-abc123..."


# ── Helpers ───────────────────────────────────────────────────────────────────

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distância real em KM entre dois pontos geográficos (fórmula Haversine)."""
    R    = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a    = (math.sin(dlat / 2) ** 2
            + math.cos(math.radians(lat1))
            * math.cos(math.radians(lat2))
            * math.sin(dlon / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


def build_route_km(route: Route, depot_name: str, city_geo: dict) -> float:
    """Calcula a distância total de uma única rota em KM reais."""
    total = 0.0
    dlat, dlon = city_geo[depot_name]
    prev_lat, prev_lon = dlat, dlon
    for stop in route.stops:
        slat, slon = city_geo[stop.name]
        total += haversine_km(prev_lat, prev_lon, slat, slon)
        prev_lat, prev_lon = slat, slon
    total += haversine_km(prev_lat, prev_lon, dlat, dlon)
    return total


def build_operation_context(
    routes:      List[Route],
    problem:     VRPProblem,
    city_geo:    dict,
    depot_name:  str,
    generation:  int,
    best_fitness: float,
    total_km:    float,
) -> str:
    """
    Monta o contexto estruturado da operação para enviar ao LLM.
    Contém todas as informações necessárias para geração dos relatórios.
    """
    lines = []
    lines.append("=== CONTEXTO DA OPERAÇÃO DE DISTRIBUIÇÃO ===")
    lines.append(f"Data/Hora    : {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}")
    lines.append(f"Depósito     : {depot_name}")
    lines.append(f"Geração AG   : {generation}")
    lines.append(f"Fitness      : {best_fitness:.4f}")
    lines.append(f"Distância total: {total_km:.1f} km")
    lines.append(f"Nº de rotas  : {len(routes)}")
    lines.append(f"Total cidades: {len(problem.delivery_points)}")
    lines.append("")

    # Alertas de cidades críticas
    criticas = [p for p in problem.delivery_points if p.priority == 3]
    altas    = [p for p in problem.delivery_points if p.priority == 2]
    lines.append(f"⚠ Entregas CRÍTICAS ({len(criticas)}): {', '.join(p.name for p in criticas)}")
    lines.append(f"! Entregas ALTAS    ({len(altas)}): {', '.join(p.name for p in altas)}")
    lines.append("")

    # Detalhes por rota/veículo
    for route in routes:
        km      = build_route_km(route, depot_name, city_geo)
        tempo_h = km / AVG_SPEED_KMH
        carga   = sum(s.demand for s in route.stops)
        veh     = next(v for v in problem.vehicles if v.id == route.vehicle_id)

        lines.append(f"--- Veículo {route.vehicle_id} (capacidade {veh.capacity}) ---")
        lines.append(f"  Distância : {km:.1f} km")
        lines.append(f"  Tempo est.: {tempo_h:.1f} h ({tempo_h*60:.0f} min) a {AVG_SPEED_KMH} km/h")
        lines.append(f"  Carga     : {carga}/{veh.capacity} unidades")
        lines.append(f"  Paradas   : {len(route.stops)}")
        lines.append("  Sequência :")

        for i, stop in enumerate(route.stops, 1):
            pri_label = PRIORITY_LABEL[stop.priority]
            marker    = "⚠" if stop.priority == 3 else ("!" if stop.priority == 2 else " ")
            lines.append(
                f"    {i:2d}. {marker} {stop.name:<30} "
                f"| {stop.demand:3d} unid. | Prioridade: {pri_label}"
            )
        lines.append("")

    return "\n".join(lines)


def build_prompt(context: str) -> str:
    """
    Monta o prompt completo para envio ao LLM.
    O prompt instrui o modelo a gerar os 4 componentes do relatório.
    """
    return f"""Você é um assistente especializado em logística hospitalar.
Com base nos dados da operação abaixo, gere um relatório completo em português brasileiro.

{context}

Gere exatamente as 4 seções abaixo, nessa ordem:

## 1. INSTRUÇÕES POR MOTORISTA
Para cada veículo, escreva instruções claras e diretas ao motorista:
- Sequência exata de cidades a visitar (use numeração)
- Quantidade a entregar em cada ponto
- Destaque visualmente as entregas críticas (use ⚠)
- Tempo estimado de chegada acumulado em cada parada (partindo às 08:00)
- Instrução de retorno ao depósito

## 2. RELATÓRIO DE EFICIÊNCIA
- Distância total percorrida pela frota
- Tempo total estimado de operação por veículo
- Taxa de utilização de capacidade por veículo (carga / capacidade)
- Veículo mais e menos eficiente
- Comparativo com a média esperada

## 3. ALERTAS DE PRIORIDADE CRÍTICA
- Liste todas as entregas críticas com o veículo responsável
- Confirme que estão nas primeiras posições da rota
- Estime horário de chegada a cada entrega crítica (partindo às 08:00)
- Recomendações caso algum atraso seja previsto

## 4. RESUMO EXECUTIVO
- Resumo da operação em no máximo 5 linhas
- Principais métricas (frota, cidades, KM, tempo total)
- Avaliação geral da eficiência da solução
- Recomendações operacionais para o gestor
"""


def call_llm(prompt: str, api_key: str) -> str:
    """
    Chama a API da OpenAI (GPT-4o-mini) e retorna o texto gerado.
    Usa apenas a biblioteca padrão (urllib) — sem dependência de openai SDK.
    Desabilita verificação de certificado SSL para compatibilidade com Windows.
    """
    import urllib.request
    import urllib.error
    import json
    import ssl

    payload = json.dumps({
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.4,
        "max_tokens": 2000,
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    # Contexto SSL sem verificação de revogação (necessário em alguns ambientes Windows)
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    try:
        with urllib.request.urlopen(req, timeout=60, context=ssl_ctx) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        raise Exception(f"HTTP {e.code}: {body}")


def generate_report(
    routes:       List[Route],
    problem:      VRPProblem,
    city_geo:     dict,
    depot_name:   str,
    generation:   int,
    best_fitness: float,
    total_km:     float,
) -> str:
    """
    Ponto de entrada principal. Orquestra a geração do relatório:
      1. Monta o contexto estruturado da operação
      2. Constrói o prompt para o LLM
      3. Chama a API da OpenAI
      4. Salva o resultado em arquivo .txt com timestamp
      5. Retorna o texto gerado

    Se a chave de API não estiver configurada, retorna o contexto
    estruturado diretamente (sem chamada LLM) como fallback.

    Parâmetros:
        routes       : lista de Route da melhor solução atual
        problem      : instância do VRPProblem
        city_geo     : dicionário {nome: (lat, lon)}
        depot_name   : nome da cidade depósito
        generation   : geração atual do AG
        best_fitness : melhor fitness global
        total_km     : distância total em KM reais

    Retorno:
        string com o relatório gerado (LLM ou fallback)
    """
    context = build_operation_context(
        routes, problem, city_geo, depot_name,
        generation, best_fitness, total_km,
    )

    # 1. Carrega .env PRIMEIRO (antes de qualquer leitura de variável)
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ[k.strip()] = v.strip()  # sobrescreve, não só setdefault
        print(f"[LLM] .env carregado de: {env_path}")
    else:
        print(f"[LLM] Arquivo .env não encontrado em: {env_path}")

    # Ordem de busca da chave:
    # 1. Arquivo .env (recomendado — nunca sobe pro git)
    # 2. Variável de ambiente OPENAI_API_KEY
    # 3. OPENAI_API_KEY_DIRECT no topo deste arquivo (apenas para testes locais)
    api_key = (
        os.environ.get("OPENAI_API_KEY", "")
        or OPENAI_API_KEY_DIRECT
    ).strip()

    print(f"[LLM] Chave encontrada: {'Sim (' + api_key[:12] + '...)' if api_key else 'NÃO'}")

    if not api_key:
        report = (
            "⚠ OPENAI_API_KEY não configurada — exibindo contexto estruturado.\n"
            "Configure a chave em .env (OPENAI_API_KEY=sk-...) ou via variável de ambiente.\n\n"
            + context
        )
    else:
        print("[LLM] Chamando OpenAI GPT-4o-mini...")
        try:
            prompt = build_prompt(context)
            report = call_llm(prompt, api_key)
            print("[LLM] Relatório gerado com sucesso.")
        except Exception as e:
            report = f"[LLM] Erro ao chamar a API: {e}\n\n{context}"
            print(f"[LLM] Erro: {e}")

    # Salva em arquivo com timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "relatorios")
    os.makedirs(out_dir, exist_ok=True)
    out_path  = os.path.join(out_dir, f"relatorio_{timestamp}.txt")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"[LLM] Relatório salvo em: {out_path}")
    return report
