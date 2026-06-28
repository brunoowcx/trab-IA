import reflex as rx
import os
import time
import asyncio
import logging
from agent import agent, salvar_resultado

MIN_QUERY_LENGTH = 8
MAX_QUERY_LENGTH = 600
ALLOWED_MAX_RESULTS = [3, 5, 8, 12]
ALLOWED_LANGUAGES = ["pt", "en"]

ACADEMIC_DOMAINS_HINT = (
    "arxiv.org, scholar.google.com, pubmed.ncbi.nlm.nih.gov, ieeexplore.ieee.org, "
    "dl.acm.org, link.springer.com, sciencedirect.com, scielo.br, scielo.org, "
    "nature.com, sciencemag.org, jstor.org, wiley.com, tandfonline.com, "
    "mdpi.com, plos.org, frontiersin.org, semanticscholar.org, openreview.net, "
    "biorxiv.org, medrxiv.org, ssrn.com, repositorio.* (university repositories), "
    "doi.org, citeseerx, dblp.org, acl anthology, neurips.cc, openaccess.thecvf.com"
)

NON_ACADEMIC_BLOCKLIST_HINT = (
    "blogs pessoais, Medium, Substack, LinkedIn posts, sites de notícias gerais "
    "(CNN, BBC News, G1, Folha, UOL, Forbes, Bloomberg, TechCrunch, The Verge, Wired), "
    "páginas de marketing/produto de empresas, posts de fórum (Reddit, Quora, "
    "Stack Overflow), Wikipédia, vídeos do YouTube, opinião não-revisada, "
    "press releases corporativos"
)


class SearchState(rx.State):
    query: str = ""
    max_results: int = 5
    search_language: str = "pt"  # Default to "pt" (Portuguese)
    is_searching: bool = False
    result_content: str = ""
    saved_file_path: str = ""
    elapsed_time: float = 0.0
    error_message: str = ""
    last_completed_seconds: float = 0.0

    examples: list[str] = [
        "Quais são os principais artigos sobre aprendizado federado (federated learning)? Resuma as metodologias utilizadas e aponte lacunas na literatura.",
        "Principais avanços e desafios em LLMs eficientes (LLM fine-tuning, Quantização) para dispositivos móveis.",
        "Impacto do aprendizado por reforço com feedback humano (RLHF) na segurança de modelos de inteligência artificial.",
    ]

    @rx.var
    def query_length(self) -> int:
        return len(self.query.strip())

    @rx.var
    def query_too_short(self) -> bool:
        ln = len(self.query.strip())
        return ln > 0 and ln < MIN_QUERY_LENGTH

    @rx.var
    def query_is_valid(self) -> bool:
        ln = len(self.query.strip())
        return MIN_QUERY_LENGTH <= ln <= MAX_QUERY_LENGTH

    @rx.var
    def progress_stage(self) -> str:
        if not self.is_searching:
            return ""
        t = self.elapsed_time
        if self.search_language == "en":
            if t < 5:
                return "Initializing agent and preparing scholarly queries..."
            if t < 15:
                return "Searching academic databases and web sources..."
            if t < 30:
                return "Analyzing relevant papers and filtering references..."
            if t < 50:
                return "Synthesizing methodologies and structuring report..."
            return "Finalizing: writing sections and verifying citations..."
        else:
            if t < 5:
                return "Inicializando o agente e preparando consultas..."
            if t < 15:
                return "Pesquisando bases acadêmicas e fontes na web..."
            if t < 30:
                return (
                    "Analisando trechos relevantes e filtrando referências..."
                )
            if t < 50:
                return "Sintetizando metodologias e estruturando o relatório..."
            return "Finalizando: redigindo seções e validando citações..."

    @rx.event
    def set_query(self, value: str):
        if value is None:
            value = ""
        self.query = value[:MAX_QUERY_LENGTH]
        if self.error_message:
            self.error_message = ""

    @rx.event
    def set_search_language(self, value: str):
        if value in ALLOWED_LANGUAGES:
            self.search_language = value
            if self.error_message:
                self.error_message = ""
        else:
            self.search_language = "pt"

    @rx.event
    def set_max_results(self, value: int):
        try:
            value = int(value)
        except (TypeError, ValueError):
            logging.exception("Invalid max_results")
            value = 5
        if value not in ALLOWED_MAX_RESULTS:
            value = min(ALLOWED_MAX_RESULTS, key=lambda v: abs(v - value))
        self.max_results = value
        if self.error_message:
            self.error_message = ""

    @rx.event
    def select_example(self, value: str):
        self.query = value[:MAX_QUERY_LENGTH]
        self.error_message = ""

    @rx.event
    def clear_search(self):
        self.query = ""
        self.result_content = ""
        self.saved_file_path = ""
        self.elapsed_time = 0.0
        self.error_message = ""
        self.last_completed_seconds = 0.0

    def _t(self, pt: str, en: str) -> str:
        return en if self.search_language == "en" else pt

    def _friendly_error(self, exc: Exception) -> str:
        msg = str(exc) or exc.__class__.__name__
        lowered = msg.lower()
        is_en = self.search_language == "en"
        if (
            "api_key" in lowered
            or "unauthorized" in lowered
            or "401" in lowered
        ):
            return self._t(
                "Falha de autenticação com o provedor Groq. Verifique se a "
                "variável de ambiente GROQ_API_KEY está configurada corretamente.",
                "Authentication failed with the Groq provider. Make sure the "
                "GROQ_API_KEY environment variable is configured correctly.",
            )
        if "rate limit" in lowered or "429" in lowered:
            return self._t(
                "Limite de requisições atingido no provedor Groq. Aguarde alguns "
                "segundos e tente novamente.",
                "Rate limit reached on the Groq provider. Please wait a few "
                "seconds and try again.",
            )
        if "timeout" in lowered or "timed out" in lowered:
            return self._t(
                "A requisição excedeu o tempo limite. O provedor pode estar "
                "instável — tente novamente em instantes.",
                "The request timed out. The provider may be unstable — please "
                "try again shortly.",
            )
        if "connection" in lowered or "network" in lowered or "dns" in lowered:
            return self._t(
                "Erro de rede ao contatar o provedor de IA ou o mecanismo de "
                "busca. Verifique sua conexão e tente novamente.",
                "Network error contacting the AI provider or search engine. "
                "Check your connection and try again.",
            )
        if "model" in lowered and (
            "not found" in lowered or "decommission" in lowered
        ):
            return self._t(
                "O modelo configurado não está mais disponível no Groq. "
                "Atualize a variável GROQ_MODEL para um modelo suportado.",
                "The configured model is no longer available on Groq. "
                "Update the GROQ_MODEL variable to a supported model.",
            )
        return self._t(
            f"Erro durante a execução: {msg}",
            f"Error during execution: {msg}",
        )

    def _build_prompt(self, query: str, max_results: int) -> str:
        if self.search_language == "en":
            return (
                f"Research topic / question (treat as the user's bibliographic "
                f"query): {query}\n\n"
                f"=== STRICT ACADEMIC-ONLY CONSTRAINTS ===\n"
                f"1. SCOPE — ALLOWED SOURCES ONLY: Use the web_search tool to "
                f"retrieve and cite ONLY peer-reviewed academic and scientific "
                f"sources. Acceptable sources include: peer-reviewed journal "
                f"articles, conference papers and proceedings, preprints on "
                f"reputable servers (arXiv, bioRxiv, medRxiv, SSRN), recognized "
                f"scholarly repositories, university theses/dissertations from "
                f"institutional repositories, DOI-resolved publications, and "
                f"papers indexed by databases such as PubMed, IEEE Xplore, ACM "
                f"Digital Library, SpringerLink, ScienceDirect/Elsevier, Wiley, "
                f"Nature, Science, JSTOR, MDPI, PLOS, Frontiers, SciELO, "
                f"Semantic Scholar, OpenReview, ACL Anthology, NeurIPS, "
                f"OpenAccess CVF, and DBLP. Examples of acceptable domains: "
                f"{ACADEMIC_DOMAINS_HINT}.\n"
                f"2. SCOPE — FORBIDDEN SOURCES: NEVER cite blogs, Medium, "
                f"Substack, LinkedIn posts, generic news sites (CNN, BBC, "
                f"Forbes, Bloomberg, TechCrunch, The Verge, Wired, etc.), "
                f"company marketing/product pages, forums (Reddit, Quora, "
                f"Stack Overflow), Wikipedia, YouTube videos, opinion pieces, "
                f"or corporate press releases. If the only available results "
                f"are non-academic, explicitly state that no qualifying "
                f"academic sources were found instead of citing them.\n"
                f"3. SEARCH STRATEGY: Issue your web_search queries in "
                f"English, using scholarly terminology and operators like "
                f"'site:arxiv.org', 'site:ieeexplore.ieee.org', 'filetype:pdf', "
                f"or appending terms like 'paper', 'journal', 'proceedings', "
                f"'preprint', 'doi'. Make at most 3-4 well-crafted queries.\n"
                f"4. CITATION INTEGRITY: Cite ONLY works that explicitly "
                f"appear in the search results. NEVER fabricate authors, "
                f"titles, years, venues, or DOIs. If a detail is not confirmed "
                f"by the search results, mark it as 'not confirmed by search "
                f"results'.\n"
                f"5. OUTPUT LANGUAGE: Produce the ENTIRE report — all section "
                f"headings, the summary, the comparison table, methodology "
                f"bullets, gap analysis, and the references list — in ENGLISH. "
                f"Do not mix languages.\n"
                f"6. ARTICLE LIMIT: The 'Main works' table must contain AT "
                f"MOST {max_results} entries. Choose the {max_results} most "
                f"representative and citable academic works from the results.\n"
                f"7. STRUCTURE: Keep the full report structure (Summary, "
                f"Table, Methodologies, Gaps, References) even with the "
                f"article limit. Use English section headers: "
                f"'# Research: <topic>', '## 1. General summary', "
                f"'## 2. Main works', '## 3. Methodologies and approaches', "
                f"'## 4. Gaps and open questions', '## 5. References'."
            )
        # Portuguese
        return (
            f"Tema/pergunta de pesquisa (tratar como a consulta bibliográfica "
            f"do usuário): {query}\n\n"
            f"=== RESTRIÇÕES ESTRITAS — APENAS FONTES ACADÊMICAS ===\n"
            f"1. ESCOPO — FONTES PERMITIDAS: Use a ferramenta web_search para "
            f"recuperar e citar APENAS fontes acadêmicas e científicas "
            f"revisadas por pares. São aceitáveis: artigos em periódicos "
            f"revisados por pares, artigos e anais de congressos, preprints "
            f"em servidores reconhecidos (arXiv, bioRxiv, medRxiv, SSRN), "
            f"repositórios acadêmicos reconhecidos, teses e dissertações em "
            f"repositórios institucionais de universidades, publicações com "
            f"DOI, e artigos indexados em bases como PubMed, IEEE Xplore, ACM "
            f"Digital Library, SpringerLink, ScienceDirect/Elsevier, Wiley, "
            f"Nature, Science, JSTOR, MDPI, PLOS, Frontiers, SciELO, Semantic "
            f"Scholar, OpenReview, ACL Anthology, NeurIPS, OpenAccess CVF e "
            f"DBLP. Exemplos de domínios aceitos: {ACADEMIC_DOMAINS_HINT}.\n"
            f"2. ESCOPO — FONTES PROIBIDAS: NUNCA cite {NON_ACADEMIC_BLOCKLIST_HINT}. "
            f"Se os únicos resultados disponíveis forem não-acadêmicos, "
            f"declare explicitamente que não foram encontradas fontes "
            f"acadêmicas qualificadas em vez de citá-las.\n"
            f"3. ESTRATÉGIA DE BUSCA: Faça as consultas via web_search em "
            f"português E/OU inglês, usando terminologia acadêmica e "
            f"operadores como 'site:arxiv.org', 'site:scielo.br', "
            f"'site:ieeexplore.ieee.org', 'filetype:pdf', ou termos como "
            f"'paper', 'periódico', 'anais', 'preprint', 'doi'. Faça no "
            f"máximo 3-4 buscas bem elaboradas.\n"
            f"4. INTEGRIDADE DAS CITAÇÕES: Cite APENAS trabalhos que "
            f"aparecem efetivamente nos resultados da busca. NUNCA invente "
            f"autores, títulos, anos, periódicos ou DOIs. Se algum detalhe "
            f"não estiver confirmado, marque como 'não confirmado pelos "
            f"resultados da busca'.\n"
            f"5. IDIOMA DA RESPOSTA: Produza TODO o relatório — cabeçalhos, "
            f"resumo, tabela comparativa, metodologias, lacunas e referências "
            f"— em PORTUGUÊS DO BRASIL. Não misture idiomas.\n"
            f"6. LIMITE DE ARTIGOS: A tabela de 'Principais trabalhos' deve "
            f"conter NO MÁXIMO {max_results} entradas. Selecione os "
            f"{max_results} trabalhos acadêmicos mais representativos e "
            f"citáveis dos resultados.\n"
            f"7. ESTRUTURA: Mantenha a estrutura completa do relatório "
            f"(Resumo, Tabela, Metodologias, Lacunas, Referências) mesmo com "
            f"a limitação. Use os cabeçalhos: '# Pesquisa: <tema>', "
            f"'## 1. Resumo geral', '## 2. Principais trabalhos', "
            f"'## 3. Metodologias e abordagens', '## 4. Lacunas e questões "
            f"em aberto', '## 5. Referências'."
        )

    @rx.event(background=True)
    async def submit_search(self, form_data: dict):
        validation_error = ""
        is_en = False
        async with self:
            # Resolve language first so that all subsequent validation
            # messages and toasts come out in the correct idiom.
            raw_lang = form_data.get("search_language", self.search_language)
            if raw_lang in ALLOWED_LANGUAGES:
                self.search_language = raw_lang
            else:
                self.search_language = "pt"
            is_en = self.search_language == "en"

            if self.is_searching:
                validation_error = (
                    "A search is already running. Please wait for it to finish "
                    "before starting another."
                    if is_en
                    else "Já existe uma pesquisa em andamento. Aguarde a "
                    "conclusão antes de iniciar outra."
                )
            else:
                query = (form_data.get("query") or self.query or "").strip()
                raw_max = form_data.get("max_results", self.max_results)
                try:
                    max_results = int(raw_max)
                except (TypeError, ValueError):
                    logging.exception("Invalid max_results value")
                    max_results = 5
                if max_results not in ALLOWED_MAX_RESULTS:
                    # Safe default: snap to nearest allowed value.
                    max_results = min(
                        ALLOWED_MAX_RESULTS,
                        key=lambda v: abs(v - max_results),
                    )

                if not query:
                    validation_error = (
                        "Please enter a research topic or question before "
                        "starting."
                        if is_en
                        else "Por favor, digite um tema ou pergunta de "
                        "pesquisa antes de iniciar."
                    )
                elif len(query) < MIN_QUERY_LENGTH:
                    validation_error = (
                        f"The topic is too short. Please use at least "
                        f"{MIN_QUERY_LENGTH} characters describing the "
                        f"academic subject to research."
                        if is_en
                        else f"O tema é muito curto. Use pelo menos "
                        f"{MIN_QUERY_LENGTH} caracteres descrevendo o "
                        f"assunto acadêmico a pesquisar."
                    )
                elif len(query) > MAX_QUERY_LENGTH:
                    validation_error = (
                        f"The topic exceeds the {MAX_QUERY_LENGTH} character "
                        f"limit. Please shorten the description to start the "
                        f"search."
                        if is_en
                        else f"O tema excede o limite de {MAX_QUERY_LENGTH} "
                        f"caracteres. Reduza a descrição para iniciar a "
                        f"pesquisa."
                    )
                elif max_results not in ALLOWED_MAX_RESULTS:
                    # Defensive: should never trigger because of snap above.
                    validation_error = (
                        "Invalid number of articles. Choose 3, 5, 8, or 12."
                        if is_en
                        else "Quantidade de artigos inválida. Escolha 3, 5, "
                        "8 ou 12."
                    )
                elif not os.getenv("GROQ_API_KEY"):
                    validation_error = (
                        "GROQ_API_KEY is not configured on the server. Set "
                        "the key to enable the bibliographic search."
                        if is_en
                        else "GROQ_API_KEY não está configurada no ambiente "
                        "do servidor. Configure a chave para habilitar a "
                        "pesquisa."
                    )

            if validation_error:
                self.error_message = validation_error
            else:
                self.query = query
                self.max_results = max_results
                self.is_searching = True
                self.error_message = ""
                self.result_content = ""
                self.saved_file_path = ""
                self.elapsed_time = 0.0
                self.last_completed_seconds = 0.0

        if validation_error:
            yield rx.toast(
                title="Unable to start"
                if is_en
                else "Não foi possível iniciar",
                description=validation_error,
                duration=5000,
                close_button=True,
                position="bottom-right",
            )
            return

        start_time = time.time()
        prompt = self._build_prompt(query, max_results)

        loop = asyncio.get_running_loop()
        future = loop.run_in_executor(None, lambda: agent.run(prompt))

        # Poll the future while updating the elapsed-time counter so the UI
        # stays responsive and shows live progress.
        try:
            while not future.done():
                await asyncio.sleep(0.25)
                async with self:
                    self.elapsed_time = round(time.time() - start_time, 1)

            response = future.result()
            response_content = (getattr(response, "content", "") or "").strip()

            if not response_content:
                async with self:
                    self.error_message = self._t(
                        "O agente de IA não retornou conteúdo. Isso pode "
                        "ocorrer quando o provedor de busca limita as "
                        "requisições ou nenhuma fonte acadêmica qualificada "
                        "foi encontrada. Tente novamente em instantes ou "
                        "refine o tema com termos mais acadêmicos.",
                        "The AI agent returned no content. This can happen "
                        "when the search provider rate-limits requests or no "
                        "qualifying academic sources were found. Please try "
                        "again shortly or refine the topic with more "
                        "scholarly terminology.",
                    )
                    self.is_searching = False
                    self.elapsed_time = round(time.time() - start_time, 1)
                return

            try:
                file_path = await loop.run_in_executor(
                    None, lambda: salvar_resultado(query, response_content)
                )
            except Exception as save_exc:
                logging.exception("Erro ao salvar resultado")
                file_path = f"(não foi possível salvar: {save_exc})"

            async with self:
                self.result_content = response_content
                self.saved_file_path = file_path
                self.is_searching = False
                self.elapsed_time = round(time.time() - start_time, 1)
                self.last_completed_seconds = self.elapsed_time
                final_seconds = self.elapsed_time
                lang_is_en = self.search_language == "en"
            yield rx.toast(
                title="Search completed"
                if lang_is_en
                else "Pesquisa concluída",
                description=(
                    f"Report generated in {final_seconds:.1f}s."
                    if lang_is_en
                    else f"Relatório gerado em {final_seconds:.1f}s."
                ),
                duration=4000,
                close_button=True,
                position="bottom-right",
            )
        except Exception as exc:
            logging.exception("Erro ao executar pesquisa bibliográfica")
            friendly = self._friendly_error(exc)
            async with self:
                self.error_message = friendly
                self.is_searching = False
                self.elapsed_time = round(time.time() - start_time, 1)
                lang_is_en = self.search_language == "en"
            yield rx.toast(
                title="Search failed" if lang_is_en else "Falha na pesquisa",
                description=friendly,
                duration=6000,
                close_button=True,
                position="bottom-right",
            )