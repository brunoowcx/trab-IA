import json
import os
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor

from dotenv import load_dotenv
from agno.agent import Agent
from agno.models.groq import Groq
from ddgs import DDGS
from rich.console import Console
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn

load_dotenv()

console = Console()


def web_search(query: str, max_results: int = 8) -> str:
    """Busca artigos e páginas na web sobre o tema informado.

    Faz uma busca textual na internet (DuckDuckGo) e retorna uma lista de
    resultados em JSON, cada um com título, link (URL) e um trecho descritivo.
    Use esta ferramenta para encontrar artigos científicos e fontes citáveis.

    Args:
        query: Os termos de busca (em português ou inglês).
        max_results: Número máximo de resultados a retornar (padrão 8).

    Returns:
        Uma string JSON com a lista de resultados, ou uma mensagem indicando
        que nenhum resultado foi encontrado após várias tentativas.
    """
    console.print(f"  [cyan]🔎 Buscando:[/cyan] [italic]{query}[/italic]")
    tentativas = 4
    for i in range(tentativas):
        try:
            resultados = list(DDGS().text(query, max_results=max_results))
            if resultados:
                console.print(
                    f"     [green]✓ {len(resultados)} resultado(s) encontrado(s)[/green]"
                )
                limpos = [
                    {
                        "titulo": r.get("title"),
                        "url": r.get("href"),
                        "trecho": r.get("body"),
                    }
                    for r in resultados
                ]
                return json.dumps(limpos, ensure_ascii=False)
        except Exception as e:  # throttling do DuckDuckGo cai aqui
            console.print(
                f"     [yellow]↻ tentativa {i + 1}/{tentativas} sem resultado "
                f"(aguardando…)[/yellow]"
            )
        # backoff progressivo antes de tentar de novo
        time.sleep(2 * (i + 1))
    return json.dumps(
        {"aviso": "Nenhum resultado retornado após várias tentativas (possível "
                  "limitação de taxa do provedor de busca). Tente novamente."},
        ensure_ascii=False,
    )


agent = Agent(
    model=Groq(id=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")),
    tools=[web_search],
    tool_call_limit=4,
    instructions="""Você é um pesquisador bibliográfico especializado em artigos científicos.
Seu papel é buscar, resumir e comparar artigos acadêmicos sobre um tema dado pelo usuário.

ESTRATÉGIA DE BUSCA:
- Use SEMPRE a ferramenta de busca antes de responder.
- Faça poucas buscas, porém bem elaboradas (no máximo 3 ou 4 consultas).
- Evite repetir consultas quase idênticas: muitas buscas seguidas são bloqueadas pelo
  provedor e retornam resultados vazios. Prefira termos amplos e representativos.
- Analise os resultados retornados antes de decidir se precisa de outra busca.

REGRA FUNDAMENTAL — INTEGRIDADE DAS CITAÇÕES:
- Cite APENAS trabalhos que aparecem efetivamente nos resultados da busca. NUNCA invente
  autores, títulos, anos, periódicos, DOIs ou números de citação.
- Se você não tem certeza de um detalhe (autor, ano, veículo), diga explicitamente
  "não confirmado pelos resultados da busca" em vez de preencher com um palpite.
- Para cada artigo citado, inclua o link (URL) da fonte de onde a informação foi obtida.
- Se a busca não retornar bons resultados sobre o tema, diga isso claramente em vez de
  fabricar uma lista de artigos.

FORMATO OBRIGATÓRIO DA RESPOSTA (use exatamente estas seções, nesta ordem, em Markdown):

# Pesquisa: <tema>

## 1. Resumo geral
Um ou dois parágrafos situando o tema e o panorama da literatura encontrada.

## 2. Principais trabalhos
Uma tabela em Markdown com as colunas:
| Título | Autores/Ano | Contribuição principal | Fonte (URL) |
Inclua apenas trabalhos efetivamente encontrados na busca.

## 3. Metodologias e abordagens
Descreva, em tópicos, as metodologias, datasets e resultados relevantes citados nas fontes.

## 4. Lacunas e questões em aberto
Liste, em tópicos, as lacunas e questões de pesquisa em aberto identificadas.

## 5. Referências
Lista numerada das fontes utilizadas, cada uma com seu link (URL).

Responda sempre em português, de forma estruturada e acadêmica. Se a busca não retornar
resultados úteis, preencha a seção "Resumo geral" explicando isso e deixe as demais seções
vazias ou com a observação "sem dados suficientes".""",
    debug_mode=False,
)


def _nome_arquivo(pergunta: str) -> str:
    """Gera um nome de arquivo seguro (sem acentos) a partir do tema pesquisado."""
    # Remove acentos para um slug 100% portável entre sistemas de arquivos.
    sem_acento = "".join(
        c for c in unicodedata.normalize("NFKD", pergunta)
        if not unicodedata.combining(c)
    )
    base = "".join(c if c.isalnum() or c in " -_" else "" for c in sem_acento)
    base = "-".join(base.lower().split())[:60].strip("-")
    return base or "pesquisa"


def salvar_resultado(pergunta: str, conteudo: str) -> str:
    """Grava o resultado em um arquivo Markdown dentro da pasta 'resultados'."""
    pasta = "resultados"
    os.makedirs(pasta, exist_ok=True)
    caminho = os.path.join(pasta, f"{_nome_arquivo(pergunta)}.md")
    cabecalho = f"> **Pergunta de pesquisa:** {pergunta}\n\n---\n\n"
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(cabecalho + conteudo + "\n")
    return caminho


def executar_pesquisa(pergunta: str) -> str:
    """Roda o agente em uma thread de fundo enquanto exibe uma barra de progresso
    animada no terminal. Retorna o conteúdo final da resposta."""
    with ThreadPoolExecutor(max_workers=1) as executor:
        futuro = executor.submit(agent.run, pergunta)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[cyan]trabalhando…[/cyan]"),
            console=console,
            transient=True,  # some quando termina, deixando o terminal limpo
        ) as progress:
            tarefa = progress.add_task("Pesquisando e redigindo", total=None)
            while not futuro.done():
                progress.advance(tarefa, 1)
                time.sleep(0.1)

        resultado = futuro.result()

    return resultado.content or ""


def main():
    pergunta_padrao = (
        "Quais são os principais artigos sobre aprendizado federado (federated learning)? "
        "Resuma as metodologias utilizadas e aponte lacunas na literatura."
    )

    console.rule("[bold]Pesquisador Bibliográfico — agente de IA[/bold]")
    console.print("Digite o tema ou a pergunta de pesquisa.")
    console.print(
        "[dim](Pressione Enter para usar a pergunta de exemplo sobre "
        "aprendizado federado.)[/dim]\n"
    )

    pergunta = input("Tema/pergunta> ").strip()
    if not pergunta:
        pergunta = pergunta_padrao
        console.print(f"\n[dim]Usando pergunta de exemplo:[/dim]\n{pergunta}\n")

    console.print()
    conteudo = executar_pesquisa(pergunta)

    # Renderiza a resposta final como Markdown formatado.
    console.rule("[bold green]Resultado[/bold green]")
    console.print(Markdown(conteudo))
    console.rule()

    # Barra de progresso ao salvar o arquivo.
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        console=console,
        transient=True,
    ) as progress:
        tarefa = progress.add_task("Salvando resultado", total=1)
        caminho = salvar_resultado(pergunta, conteudo)
        progress.advance(tarefa, 1)

    console.print(f"[green]✓ Resultado salvo em:[/green] {caminho}")


if __name__ == "__main__":
    main()
