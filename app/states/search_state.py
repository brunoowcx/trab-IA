import reflex as rx
import os
import time
import asyncio
import logging
from agent import agent, salvar_resultado

MIN_QUERY_LENGTH = 8
MAX_QUERY_LENGTH = 600
ALLOWED_MAX_RESULTS = [3, 5, 8, 12]


class SearchState(rx.State):
    query: str = ""
    max_results: int = 5
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
        if t < 5:
            return "Inicializando o agente e preparando consultas..."
        if t < 15:
            return "Pesquisando bases acadêmicas e fontes na web..."
        if t < 30:
            return "Analisando trechos relevantes e filtrando referências..."
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
    def set_max_results(self, value: int):
        try:
            value = int(value)
        except (TypeError, ValueError):
            logging.exception("Invalid max_results")
            value = 5
        if value not in ALLOWED_MAX_RESULTS:
            value = min(ALLOWED_MAX_RESULTS, key=lambda v: abs(v - value))
        self.max_results = value

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

    def _friendly_error(self, exc: Exception) -> str:
        msg = str(exc) or exc.__class__.__name__
        lowered = msg.lower()
        if (
            "api_key" in lowered
            or "unauthorized" in lowered
            or "401" in lowered
        ):
            return (
                "Falha de autenticação com o provedor Groq. Verifique se a "
                "variável de ambiente GROQ_API_KEY está configurada corretamente."
            )
        if "rate limit" in lowered or "429" in lowered:
            return (
                "Limite de requisições atingido no provedor Groq. Aguarde alguns "
                "segundos e tente novamente."
            )
        if "timeout" in lowered or "timed out" in lowered:
            return (
                "A requisição excedeu o tempo limite. O provedor pode estar "
                "instável — tente novamente em instantes."
            )
        if "connection" in lowered or "network" in lowered or "dns" in lowered:
            return (
                "Erro de rede ao contatar o provedor de IA ou o mecanismo de "
                "busca. Verifique sua conexão e tente novamente."
            )
        if "model" in lowered and (
            "not found" in lowered or "decommission" in lowered
        ):
            return (
                "O modelo configurado não está mais disponível no Groq. "
                "Atualize a variável GROQ_MODEL para um modelo suportado."
            )
        return f"Erro durante a execução: {msg}"

    def _build_prompt(self, query: str, max_results: int) -> str:
        return (
            f"{query}\n\n"
            f"Restrições importantes para esta pesquisa:\n"
            f"- Limite a tabela de Principais trabalhos a no MÁXIMO {max_results} artigos.\n"
            f"- Selecione os {max_results} trabalhos mais representativos e citáveis.\n"
            f"- Mantenha a estrutura completa do relatório (Resumo, Tabela, "
            f"Metodologias, Lacunas, Referências) mesmo com a limitação."
        )

    @rx.event(background=True)
    async def submit_search(self, form_data: dict):
        validation_error = ""
        async with self:
            if self.is_searching:
                validation_error = (
                    "Já existe uma pesquisa em andamento. Aguarde a conclusão "
                    "antes de iniciar outra."
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
                    max_results = min(
                        ALLOWED_MAX_RESULTS,
                        key=lambda v: abs(v - max_results),
                    )

                if not query:
                    validation_error = (
                        "Por favor, digite um tema ou pergunta de pesquisa "
                        "antes de iniciar."
                    )
                elif len(query) < MIN_QUERY_LENGTH:
                    validation_error = (
                        f"O tema é muito curto. Use pelo menos {MIN_QUERY_LENGTH} "
                        "caracteres descrevendo o assunto a pesquisar."
                    )
                elif len(query) > MAX_QUERY_LENGTH:
                    validation_error = (
                        f"O tema excede o limite de {MAX_QUERY_LENGTH} caracteres. "
                        "Reduza a descrição para iniciar a pesquisa."
                    )
                elif not os.getenv("GROQ_API_KEY"):
                    validation_error = (
                        "GROQ_API_KEY não está configurada no ambiente do "
                        "servidor. Configure a chave para habilitar a pesquisa."
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
                title="Não foi possível iniciar",
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
                    self.error_message = (
                        "O agente de IA não retornou conteúdo. Isso pode ocorrer "
                        "quando o provedor de busca limita as requisições. "
                        "Tente novamente em instantes ou refine o tema."
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
            yield rx.toast(
                title="Pesquisa concluída",
                description=f"Relatório gerado em {self.elapsed_time:.1f}s.",
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
            yield rx.toast(
                title="Falha na pesquisa",
                description=friendly,
                duration=6000,
                close_button=True,
                position="bottom-right",
            )