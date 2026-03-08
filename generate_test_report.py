"""
generate_test_report.py
-----------------------
Executa os testes automatizados do projeto, captura os resultados
e usa a LLM (OpenAI GPT-4o-mini) para gerar um relatório gerencial
completo explicando as regras testadas e os resultados obtidos.

Uso:
    python generate_test_report.py

O relatório é salvo em: relatorios/relatorio_testes_TIMESTAMP.txt

Configuração da chave API:
    Crie um arquivo .env na raiz do projeto com:
        OPENAI_API_KEY=sk-proj-sua-chave-aqui
"""

import os
import sys
import ssl
import json
import unittest
import datetime
import io
import urllib.request
import urllib.error
from collections import defaultdict


# ── Chave da API ──────────────────────────────────────────────────────────────
# Cole sua chave aqui para testes locais (não sobe pro git)
OPENAI_API_KEY_DIRECT = ""


# ── Descrições das regras de negócio por módulo/classe ────────────────────────
REGRAS = {
    "TestOrderCrossover": {
        "modulo": "genetic_algorithm.py → order_crossover()",
        "descricao": (
            "Order Crossover (OX) é o operador de cruzamento genético. "
            "Recebe dois cromossomos pai (permutações de IDs de cidades) e gera "
            "um filho que herda um segmento contíguo do pai 1 e preenche o restante "
            "com os genes do pai 2 na ordem em que aparecem, sem repetições. "
            "É essencial para o VRP pois garante que cada cidade seja visitada exatamente uma vez."
        ),
        "regras": [
            "O filho deve ter o mesmo tamanho dos pais",
            "O filho é uma permutação válida: cada gene aparece exatamente uma vez",
            "O filho não contém duplicatas",
            "Todos os genes do pai 1 estão presentes no filho",
            "Pais idênticos geram filho com os mesmos genes",
            "Funciona corretamente com cromossomos de 1 e 2 elementos",
            "Não altera os cromossomos originais dos pais",
        ],
    },
    "TestMutate": {
        "modulo": "genetic_algorithm.py → mutate()",
        "descricao": (
            "Mutação por troca de posições adjacentes (adjacent swap). "
            "Com probabilidade mutation_probability, dois genes consecutivos são trocados. "
            "A taxa é adaptativa: sobe durante estagnação e cai após melhorias, "
            "equilibrando exploração e refinamento ao longo da evolução."
        ),
        "regras": [
            "A mutação preserva todos os genes (nenhum é criado ou perdido)",
            "Não gera duplicatas após a mutação",
            "Com probabilidade 0.0, o cromossomo não é alterado",
            "Com probabilidade 1.0, exatamente dois genes adjacentes são trocados",
            "Retorna uma cópia — não modifica o cromossomo original",
            "Funciona com cromossomos de 1 e 2 elementos",
            "Preserva o tamanho do cromossomo",
        ],
    },
    "TestSortPopulation": {
        "modulo": "genetic_algorithm.py → sort_population()",
        "descricao": (
            "Ordena a população pelo fitness em ordem crescente (menor = melhor). "
            "Usado após cada geração para identificar o melhor indivíduo (elitismo) "
            "e alimentar a seleção por torneio com os índices corretos."
        ),
        "regras": [
            "Ordena por fitness crescente (menor fitness = melhor solução)",
            "Cada cromossomo acompanha seu respectivo fitness na reordenação",
            "Populações já ordenadas permanecem inalteradas",
            "Fitness iguais mantêm todos os cromossomos na população",
            "Funciona com população de um único elemento",
            "Preserva o tamanho da população após ordenação",
        ],
    },
    "TestSortByPriority": {
        "modulo": "vrp/decoder.py → VRPDecoder._sort_by_priority()",
        "descricao": (
            "Reordena o cromossomo garantindo que cidades de maior prioridade "
            "sejam visitadas primeiro. Grupos: Crítica (3) > Alta (2) > Normal (1). "
            "Dentro de cada grupo, a ordem relativa otimizada pelo AG é preservada. "
            "Esta é a implementação estrutural da restrição de prioridade hospitalar."
        ),
        "regras": [
            "Cidades críticas (prioridade 3) aparecem sempre antes das demais",
            "Cidades de alta prioridade (2) aparecem antes das normais (1)",
            "A sequência de prioridades é sempre decrescente",
            "Todos os genes são preservados após a reordenação",
            "Quando todos são normais, a ordem original é mantida",
            "Quando todos são críticos, a ordem original é mantida",
        ],
    },
    "TestDecoderIntegridade": {
        "modulo": "vrp/decoder.py → VRPDecoder.decode()",
        "descricao": (
            "Testes de integridade básica do decoder: garante que todas as "
            "cidades recebem suas entregas, sem omissões nem duplicatas."
        ),
        "regras": [
            "Todos os pontos de entrega são incluídos nas rotas geradas",
            "Nenhum ponto de entrega aparece em mais de uma rota",
            "O retorno do decode() é sempre uma lista de objetos Route",
        ],
    },
    "TestDecoderCapacidade": {
        "modulo": "vrp/decoder.py → VRPDecoder.decode() [restrição de capacidade]",
        "descricao": (
            "Valida o respeito à capacidade máxima dos veículos. "
            "Quando a soma das demandas ultrapassa o limite, o decoder "
            "fecha a rota atual e abre uma nova com o próximo veículo disponível."
        ),
        "regras": [
            "A rota é fechada quando a capacidade do veículo seria excedida",
            "A carga total de cada rota nunca ultrapassa a capacidade do veículo",
            "Com capacidade restritiva, todos os pontos ainda são entregues",
        ],
    },
    "TestDecoderAutonomia": {
        "modulo": "vrp/decoder.py → VRPDecoder.decode() [restrição de autonomia]",
        "descricao": (
            "Valida o respeito à autonomia máxima (distância) dos veículos. "
            "O decoder calcula dist_ao_ponto + dist_retorno_depot e fecha "
            "a rota se a autonomia seria excedida."
        ),
        "regras": [
            "Com autonomia limitada, pontos distantes geram múltiplas rotas",
            "Todos os pontos são entregues mesmo com autonomia muito restritiva",
        ],
    },
    "TestDecoderMultiplosVeiculos": {
        "modulo": "vrp/decoder.py → VRPDecoder.decode() [múltiplos veículos]",
        "descricao": (
            "Valida o comportamento com frota de múltiplos veículos. "
            "O decoder rotaciona entre veículos ao fechar rotas e reutiliza "
            "o último quando a frota se esgota."
        ),
        "regras": [
            "Com restrições, mais de um veículo é utilizado",
            "Os vehicle_ids nas rotas sempre existem na frota definida",
            "Com frota vazia, o decode() retorna lista vazia sem erros",
        ],
    },
    "TestCalculoFitness": {
        "modulo": "core/fitness.py → calculo_fitness()",
        "descricao": (
            "Valida a função de fitness multiobjetivo que combina 4 componentes "
            "normalizados: distância total (55%), penalidade de prioridade (15%), "
            "variância de carga entre rotas (5%) e fragmentação de viagens (25%). "
            "Menor fitness = melhor solução."
        ),
        "regras": [
            "Retorna sempre um valor float",
            "O fitness é sempre positivo",
            "O fitness é sempre finito (sem NaN ou infinito)",
            "Ordens diferentes de visita produzem valores de fitness calculáveis",
            "Funciona com apenas 1 ponto de entrega",
            "Funciona quando todos os pontos estão no depósito (distância zero)",
            "Cidades críticas visitadas no fim geram fitness calculável e penalizado",
        ],
    },
    "TestRouteDistance": {
        "modulo": "core/fitness.py → route_distance()",
        "descricao": (
            "Valida o cálculo de distância euclidiana total de um cromossomo. "
            "Usado internamente pelo 2-opt para comparar variantes de rota."
        ),
        "regras": [
            "Distância entre dois pontos segue a fórmula euclidiana corretamente",
            "Distância de um único ponto é zero",
            "Distância é sempre não-negativa",
            "Distância é simétrica: A→B = B→A",
            "Valida triângulo 3-4-5 de Pitágoras",
        ],
    },
    "TestTwoOpt": {
        "modulo": "core/fitness.py → two_opt()",
        "descricao": (
            "Valida o refinamento local 2-opt: melhora iterativamente a ordem "
            "de visita revertendo segmentos do cromossomo. Aplicado ao melhor "
            "indivíduo de cada geração e a 5% dos filhos."
        ),
        "regras": [
            "O resultado é sempre uma permutação válida dos mesmos genes",
            "O resultado não contém duplicatas",
            "A distância após o 2-opt nunca é pior que antes",
            "O tamanho do cromossomo é preservado",
            "Não modifica o cromossomo original",
            "Funciona com 2 pontos sem erros",
            "Funciona com 1 ponto sem erros",
        ],
    },
}


# ── Runner personalizado ──────────────────────────────────────────────────────

class DetailedTestResult(unittest.TestResult):
    """Coleta resultados detalhados por classe e teste."""

    def __init__(self):
        super().__init__()
        self.test_details = []   # (classe, método, status, duracao_ms, mensagem)
        self._start_times = {}

    def startTest(self, test):
        super().startTest(test)
        import time
        self._start_times[test.id()] = time.perf_counter()

    def _record(self, test, status, msg=""):
        import time
        elapsed = (time.perf_counter() - self._start_times.get(test.id(), 0)) * 1000
        parts   = test.id().split(".")
        classe  = parts[-2] if len(parts) >= 2 else "?"
        metodo  = parts[-1]
        self.test_details.append((classe, metodo, status, elapsed, msg))

    def addSuccess(self, test):
        super().addSuccess(test)
        self._record(test, "PASSOU")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self._record(test, "FALHOU", str(err[1]))

    def addError(self, test, err):
        super().addError(test, err)
        self._record(test, "ERRO", str(err[1]))

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self._record(test, "PULADO", reason)


def run_tests() -> DetailedTestResult:
    """Descobre e executa todos os testes, retornando resultado detalhado."""
    loader = unittest.TestLoader()
    suite  = loader.discover(
        start_dir=os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests"),
        pattern="test_*.py",
    )
    result = DetailedTestResult()
    suite.run(result)
    return result


# ── Construção do contexto para o LLM ────────────────────────────────────────

def build_test_context(result: DetailedTestResult) -> str:
    """Monta o contexto estruturado dos testes para enviar ao LLM."""

    # Agrupa por classe
    por_classe = defaultdict(list)
    for classe, metodo, status, ms, msg in result.test_details:
        por_classe[classe].append((metodo, status, ms, msg))

    total     = result.testsRun
    passou    = sum(1 for _, _, s, _, _ in result.test_details if s == "PASSOU")
    falhou    = len(result.failures)
    erro      = len(result.errors)
    taxa      = (passou / total * 100) if total > 0 else 0
    tempo_total = sum(ms for _, _, _, ms, _ in result.test_details)

    lines = []
    lines.append("=== RELATÓRIO DE EXECUÇÃO DOS TESTES AUTOMATIZADOS ===")
    lines.append(f"Data/Hora      : {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}")
    lines.append(f"Projeto        : VRP Hospitalar — Distribuição de Medicamentos RMSP")
    lines.append(f"Framework      : Python unittest")
    lines.append("")
    lines.append("── RESUMO GERAL ──────────────────────────────────────────")
    lines.append(f"Total de testes : {total}")
    lines.append(f"Passaram        : {passou} ✓")
    lines.append(f"Falharam        : {falhou} ✗")
    lines.append(f"Erros           : {erro} !")
    lines.append(f"Taxa de sucesso : {taxa:.1f}%")
    lines.append(f"Tempo total     : {tempo_total:.1f} ms")
    lines.append("")

    lines.append("── DETALHAMENTO POR MÓDULO ───────────────────────────────")
    for classe, testes in sorted(por_classe.items()):
        info   = REGRAS.get(classe, {})
        modulo = info.get("modulo", classe)
        passou_cls = sum(1 for _, s, _, _ in testes if s == "PASSOU")
        lines.append("")
        lines.append(f"[{classe}]")
        lines.append(f"  Módulo  : {modulo}")
        lines.append(f"  Testes  : {passou_cls}/{len(testes)} passaram")

        # Regras de negócio
        regras = info.get("regras", [])
        if regras:
            lines.append(f"  Regras testadas ({len(regras)}):")
            for r in regras:
                lines.append(f"    • {r}")

        # Resultado por teste
        lines.append("  Resultados:")
        for metodo, status, ms, msg in sorted(testes):
            icone = "✓" if status == "PASSOU" else "✗"
            lines.append(f"    {icone} {metodo} ({ms:.1f} ms)")
            if msg:
                lines.append(f"       → {msg}")

    # Falhas detalhadas
    if result.failures or result.errors:
        lines.append("")
        lines.append("── FALHAS DETALHADAS ─────────────────────────────────────")
        for test, tb in result.failures + result.errors:
            lines.append(f"  {test}: {tb[:300]}")

    return "\n".join(lines)


def build_test_prompt(context: str) -> str:
    """Monta o prompt para o LLM gerar o relatório gerencial."""
    return f"""Você é um engenheiro de software sênior especializado em qualidade de software e algoritmos de otimização.

Com base nos resultados dos testes automatizados abaixo, gere um relatório gerencial completo em português brasileiro para ser apresentado ao avaliador acadêmico do projeto.

{context}

Gere exatamente as 5 seções abaixo, nessa ordem:

## 1. VISÃO GERAL DO PROJETO
Explique em linguagem acessível o que é o projeto (VRP hospitalar com Algoritmo Genético) e por que os testes automatizados são importantes para garantir a confiabilidade do sistema. Máximo 10 linhas.

## 2. ESTRATÉGIA DE TESTES
Explique a estratégia adotada:
- Quais módulos foram testados e por quê foram priorizados
- Tipos de testes utilizados (unitários, de restrição, de integridade)
- Por que cada módulo é crítico para o funcionamento do sistema
- Cobertura alcançada

## 3. REGRAS DE NEGÓCIO VALIDADAS
Para cada módulo/classe de teste, explique em linguagem gerencial:
- O que a função faz no contexto do sistema
- Quais regras de negócio foram validadas
- Por que essas regras são importantes para a operação hospitalar
Use linguagem clara, evitando jargões técnicos desnecessários.

## 4. RESULTADOS OBTIDOS
- Apresente os números de forma clara (total, aprovados, taxa de sucesso)
- Destaque o desempenho (tempo de execução)
- Analise o que os resultados significam para a qualidade do sistema
- Se houver falhas, explique o impacto e o que deve ser corrigido

## 5. CONCLUSÃO E RECOMENDAÇÕES
- Avaliação geral da qualidade do código testado
- Confiabilidade do sistema para uso em ambiente hospitalar
- Recomendações para evolução futura da suite de testes
- Conclusão sobre a maturidade do projeto
"""


# ── Chamada à API ─────────────────────────────────────────────────────────────

def call_openai(prompt: str, api_key: str) -> str:
    """Chama GPT-4o-mini e retorna o texto gerado."""
    payload = json.dumps({
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.4,
        "max_tokens": 3000,
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

    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode    = ssl.CERT_NONE

    try:
        with urllib.request.urlopen(req, timeout=60, context=ssl_ctx) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        raise Exception(f"HTTP {e.code}: {body}")


def load_api_key() -> str:
    """Carrega a chave API na ordem: .env → variável de ambiente → constante direta."""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ[k.strip()] = v.strip()

    return (os.environ.get("OPENAI_API_KEY", "") or OPENAI_API_KEY_DIRECT).strip()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  GERADOR DE RELATÓRIO GERENCIAL DE TESTES")
    print("  Projeto: VRP Hospitalar — RMSP")
    print("=" * 60)

    # 1. Executa os testes
    print("\n[1/4] Executando testes automatizados...")
    result  = run_tests()
    passou  = result.testsRun - len(result.failures) - len(result.errors)
    print(f"      {result.testsRun} testes | {passou} passaram | "
          f"{len(result.failures)} falharam | {len(result.errors)} erros")

    # 2. Monta o contexto
    print("\n[2/4] Montando contexto dos testes...")
    context = build_test_context(result)

    # 3. Chama o LLM
    api_key = load_api_key()
    if api_key:
        print("\n[3/4] Chamando OpenAI GPT-4o-mini para gerar relatório...")
        try:
            prompt  = build_test_prompt(context)
            relatorio = call_openai(prompt, api_key)
            print("      Relatório gerado com sucesso.")
        except Exception as e:
            print(f"      Erro ao chamar a API: {e}")
            print("      Usando contexto estruturado como fallback.")
            relatorio = (
                "⚠ Erro ao chamar a API LLM — exibindo contexto estruturado.\n\n"
                + context
            )
    else:
        print("\n[3/4] OPENAI_API_KEY não configurada — usando contexto estruturado.")
        relatorio = (
            "⚠ OPENAI_API_KEY não configurada.\n"
            "Configure em .env para gerar o relatório com LLM.\n\n"
            + context
        )

    # 4. Salva o relatório
    print("\n[4/4] Salvando relatório...")
    out_dir   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "relatorios")
    os.makedirs(out_dir, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path  = os.path.join(out_dir, f"relatorio_testes_{timestamp}.txt")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(relatorio)

    print(f"      Salvo em: {out_path}")
    print("\n" + "=" * 60)
    print("  CONCLUÍDO")
    print("=" * 60)

    # Exibe prévia
    print("\n── PRÉVIA DO RELATÓRIO ───────────────────────────────────\n")
    print(relatorio[:800] + "\n[... relatório completo no arquivo ...]")


if __name__ == "__main__":
    main()
