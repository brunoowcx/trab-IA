import reflex as rx
from app.states.search_state import (
    SearchState,
    MIN_QUERY_LENGTH,
    MAX_QUERY_LENGTH,
)


def header() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.icon("book-open", class_name="h-8 w-8 text-indigo-600"),
                rx.el.h1(
                    "ScholarAgent",
                    class_name="text-2xl font-bold text-gray-900 font-['Inter']",
                ),
                class_name="flex items-center gap-3",
            ),
            rx.el.div(
                rx.el.span(
                    "Pesquisa Bibliográfica de Alta Integridade",
                    class_name="text-sm text-gray-500 font-medium hidden sm:inline",
                ),
                rx.el.span(
                    "IA + Buscas em tempo real",
                    class_name="ml-3 px-2 py-1 text-xs bg-indigo-50 text-indigo-700 rounded-full font-semibold border border-indigo-100",
                ),
                class_name="flex items-center",
            ),
            class_name="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center",
        ),
        class_name="bg-white border-b border-gray-200 sticky top-0 z-50 shadow-xs",
    )


def info_card() -> rx.Component:
    return rx.el.div(
        rx.el.h3(
            "📚 Diretrizes Acadêmicas",
            class_name="text-lg font-bold text-gray-900 mb-3",
        ),
        rx.el.p(
            "Nosso agente garante a integridade científica recuperando referências de fontes reais através do DuckDuckGo. Ele constrói respostas estruturadas com:",
            class_name="text-sm text-gray-600 mb-4",
        ),
        rx.el.ul(
            rx.el.li(
                "✓ Resumo sistemático e panorama da literatura",
                class_name="text-sm text-gray-700 flex items-center gap-2 mb-2 font-medium",
            ),
            rx.el.li(
                "✓ Tabela comparativa detalhada de trabalhos",
                class_name="text-sm text-gray-700 flex items-center gap-2 mb-2 font-medium",
            ),
            rx.el.li(
                "✓ Metodologias e abordagens reportadas",
                class_name="text-sm text-gray-700 flex items-center gap-2 mb-2 font-medium",
            ),
            rx.el.li(
                "✓ Mapeamento preciso de lacunas de pesquisa",
                class_name="text-sm text-gray-700 flex items-center gap-2 mb-2 font-medium",
            ),
            rx.el.li(
                "✓ Links e referências originais checados",
                class_name="text-sm text-gray-700 flex items-center gap-2 font-semibold text-indigo-600",
            ),
            class_name="space-y-1 pl-1",
        ),
        rx.el.div(
            rx.el.div(
                rx.icon(
                    "shield-alert",
                    class_name="h-5 w-5 text-indigo-600 shrink-0",
                ),
                rx.el.span(
                    "Academic-Only Scope",
                    class_name="text-xs font-bold uppercase tracking-wider text-indigo-900",
                ),
                class_name="flex items-center gap-1.5 mb-2",
            ),
            rx.el.p(
                "Todas as consultas são estritamente limitadas a repositórios científicos, papers, anais de congressos, periódicos acadêmicos credenciados e servidores de preprints para evitar blogs ou opiniões não-científicas.",
                class_name="text-xs text-indigo-950 font-medium leading-relaxed",
            ),
            class_name="mt-5 p-3 rounded-xl bg-indigo-50 border border-indigo-100",
        ),
        class_name="bg-indigo-50/50 rounded-2xl p-6 border border-indigo-100",
    )


def example_item(example_text: str) -> rx.Component:
    return rx.el.button(
        rx.el.span(
            example_text,
            class_name="text-left block text-sm font-medium text-gray-700 truncate w-full hover:text-indigo-600",
        ),
        type="button",
        on_click=lambda: SearchState.select_example(example_text),
        class_name="w-full text-left p-3 rounded-xl border border-gray-200 bg-white hover:bg-indigo-50/30 hover:border-indigo-200 transition-all flex items-center justify-between",
    )


def index() -> rx.Component:
    return rx.el.div(
        header(),
        rx.el.main(
            rx.el.div(
                # Left column (Form & Examples)
                rx.el.div(
                    rx.el.div(
                        rx.el.h2(
                            "Nova Pesquisa Bibliográfica",
                            class_name="text-xl font-bold text-gray-900 mb-4",
                        ),
                        rx.el.form(
                            rx.el.div(
                                rx.el.label(
                                    "Sua pergunta ou tema de pesquisa:",
                                    class_name="block text-sm font-semibold text-gray-700 mb-2",
                                ),
                                rx.el.textarea(
                                    name="query",
                                    on_change=SearchState.set_query.debounce(
                                        150
                                    ),
                                    placeholder="Ex: Quais os avanços recentes em arquiteturas transformers de poucos parâmetros?",
                                    class_name=rx.cond(
                                        SearchState.query_too_short,
                                        "w-full h-32 px-4 py-3 rounded-xl border border-amber-300 bg-white text-gray-900 focus:outline-hidden focus:ring-2 focus:ring-amber-400 focus:border-amber-400 font-medium placeholder-gray-400 resize-none",
                                        "w-full h-32 px-4 py-3 rounded-xl border border-gray-200 bg-white text-gray-900 focus:outline-hidden focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 font-medium placeholder-gray-400 resize-none",
                                    ),
                                    default_value=SearchState.query,
                                    max_length=MAX_QUERY_LENGTH,
                                    disabled=SearchState.is_searching,
                                ),
                                rx.el.div(
                                    rx.cond(
                                        SearchState.query_too_short,
                                        rx.el.span(
                                            f"Mínimo de {MIN_QUERY_LENGTH} caracteres para uma busca de qualidade.",
                                            class_name="text-xs font-semibold text-amber-600",
                                        ),
                                        rx.el.span(
                                            "Descreva o tema com clareza para melhores referências.",
                                            class_name="text-xs font-medium text-gray-400",
                                        ),
                                    ),
                                    rx.el.span(
                                        f"{SearchState.query_length} / {MAX_QUERY_LENGTH}",
                                        class_name=rx.cond(
                                            SearchState.query_length
                                            > (MAX_QUERY_LENGTH - 50),
                                            "text-xs font-mono font-semibold text-amber-600",
                                            "text-xs font-mono font-medium text-gray-400",
                                        ),
                                    ),
                                    class_name="flex items-center justify-between mt-2 px-1",
                                ),
                                class_name="mb-5",
                            ),
                            rx.el.div(
                                rx.el.div(
                                    rx.el.label(
                                        "Idioma do Relatório / Search Language:",
                                        class_name="block text-sm font-semibold text-gray-700 mb-2",
                                    ),
                                    rx.el.div(
                                        rx.el.select(
                                            rx.el.option(
                                                "Português (BR)", value="pt"
                                            ),
                                            rx.el.option("English", value="en"),
                                            name="search_language",
                                            value=SearchState.search_language,
                                            on_change=SearchState.set_search_language,
                                            disabled=SearchState.is_searching,
                                            class_name="w-full px-4 py-2.5 rounded-xl border border-gray-200 bg-white text-gray-900 font-medium focus:outline-hidden focus:ring-2 focus:ring-indigo-500 appearance-none cursor-pointer disabled:bg-gray-50 disabled:text-gray-400 disabled:cursor-not-allowed",
                                        ),
                                        rx.icon(
                                            "chevron-down",
                                            class_name="absolute right-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400 pointer-events-none",
                                        ),
                                        class_name="relative",
                                    ),
                                    class_name="flex-1",
                                ),
                                rx.el.div(
                                    rx.el.label(
                                        "Artigos Máximos:",
                                        class_name="block text-sm font-semibold text-gray-700 mb-2",
                                    ),
                                    rx.el.div(
                                        rx.el.select(
                                            rx.el.option(
                                                "3 Artigos", value="3"
                                            ),
                                            rx.el.option(
                                                "5 Artigos", value="5"
                                            ),
                                            rx.el.option(
                                                "8 Artigos", value="8"
                                            ),
                                            rx.el.option(
                                                "12 Artigos", value="12"
                                            ),
                                            name="max_results",
                                            value=SearchState.max_results.to_string(),
                                            on_change=lambda val: (
                                                SearchState.set_max_results(
                                                    val.to(int)
                                                )
                                            ),
                                            disabled=SearchState.is_searching,
                                            class_name="w-full px-4 py-2.5 rounded-xl border border-gray-200 bg-white text-gray-900 font-medium focus:outline-hidden focus:ring-2 focus:ring-indigo-500 appearance-none cursor-pointer disabled:bg-gray-50 disabled:text-gray-400 disabled:cursor-not-allowed",
                                        ),
                                        rx.icon(
                                            "chevron-down",
                                            class_name="absolute right-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400 pointer-events-none",
                                        ),
                                        class_name="relative",
                                    ),
                                    class_name="w-32",
                                ),
                                rx.el.div(
                                    rx.el.div(
                                        "⠀", class_name="text-sm mb-2 invisible"
                                    ),
                                    rx.el.button(
                                        rx.icon(
                                            "trash-2", class_name="h-4 w-4 mr-2"
                                        ),
                                        "Limpar",
                                        type="button",
                                        on_click=SearchState.clear_search,
                                        disabled=SearchState.is_searching,
                                        class_name="px-4 py-2.5 rounded-xl border border-gray-200 bg-white text-gray-700 font-semibold hover:bg-gray-50 hover:text-red-600 transition-colors flex items-center justify-center w-full disabled:opacity-50 disabled:cursor-not-allowed",
                                    ),
                                    class_name="w-24",
                                ),
                                class_name="flex gap-4 mb-6",
                            ),
                            rx.el.button(
                                rx.cond(
                                    SearchState.is_searching,
                                    rx.el.div(
                                        rx.spinner(size="1", class_name="mr-2"),
                                        rx.el.span(
                                            f"Buscando... ({SearchState.elapsed_time:.1f}s)",
                                            class_name="font-semibold",
                                        ),
                                        class_name="flex items-center justify-center",
                                    ),
                                    rx.el.div(
                                        rx.icon(
                                            "search", class_name="h-5 w-5 mr-2"
                                        ),
                                        rx.el.span(
                                            "Iniciar Pesquisa Bibliográfica",
                                            class_name="font-semibold",
                                        ),
                                        class_name="flex items-center justify-center",
                                    ),
                                ),
                                type="submit",
                                disabled=SearchState.is_searching,
                                class_name="w-full bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-400 text-white py-3 px-4 rounded-xl transition-colors cursor-pointer flex items-center justify-center shadow-xs",
                            ),
                            on_submit=SearchState.submit_search,
                            reset_on_submit=False,
                        ),
                        class_name="bg-white rounded-2xl border border-gray-200 p-6 shadow-xs mb-6",
                    ),
                    # Examples Card
                    rx.el.div(
                        rx.el.h3(
                            "💡 Sugestões de Pesquisa",
                            class_name="text-sm font-bold text-gray-400 uppercase tracking-wider mb-3",
                        ),
                        rx.el.div(
                            rx.foreach(SearchState.examples, example_item),
                            class_name=rx.cond(
                                SearchState.is_searching,
                                "space-y-2 opacity-50 pointer-events-none",
                                "space-y-2",
                            ),
                        ),
                        class_name="mb-6",
                    ),
                    info_card(),
                    class_name="w-full lg:w-[420px] shrink-0",
                ),
                # Right column (Search Results / Guidance)
                rx.el.div(
                    rx.cond(
                        SearchState.is_searching,
                        rx.el.div(
                            rx.el.div(
                                rx.spinner(
                                    size="3", class_name="text-indigo-600 mb-4"
                                ),
                                rx.el.h3(
                                    "Varrendo a Web & Analisando Artigos",
                                    class_name="text-xl font-bold text-gray-900 mb-2",
                                ),
                                rx.el.p(
                                    "Isso pode levar de 30 a 60 segundos. Estamos buscando apenas fontes científicas confirmadas.",
                                    class_name="text-gray-500 max-w-md text-center text-sm font-medium mb-4",
                                ),
                                rx.el.div(
                                    rx.el.div(
                                        rx.icon(
                                            "loader",
                                            class_name="h-4 w-4 text-indigo-500 animate-spin shrink-0",
                                        ),
                                        rx.el.span(
                                            SearchState.progress_stage,
                                            class_name="text-sm font-medium text-indigo-900",
                                        ),
                                        class_name="flex items-center gap-2 bg-indigo-50 border border-indigo-100 px-4 py-2 rounded-xl mb-3 max-w-md",
                                    ),
                                    rx.el.div(
                                        rx.el.div(
                                            class_name="h-full bg-indigo-500 rounded-full animate-pulse",
                                            style={"width": "60%"},
                                        ),
                                        class_name="w-full max-w-md h-1.5 bg-indigo-100 rounded-full overflow-hidden mb-4",
                                    ),
                                    rx.el.div(
                                        rx.icon(
                                            "timer",
                                            class_name="h-4 w-4 text-indigo-600",
                                        ),
                                        rx.el.span(
                                            f"Tempo decorrido: {SearchState.elapsed_time:.1f}s",
                                            class_name="text-indigo-600 font-bold font-mono text-sm",
                                        ),
                                        class_name="bg-indigo-50 border border-indigo-100 px-4 py-2 rounded-full flex items-center gap-2",
                                    ),
                                    class_name="flex flex-col items-center w-full",
                                ),
                                class_name="flex flex-col items-center justify-center py-12 px-4",
                            ),
                            class_name="bg-white rounded-2xl border border-gray-200 shadow-xs p-8 flex items-center justify-center min-h-[500px]",
                        ),
                        rx.cond(
                            SearchState.error_message,
                            rx.el.div(
                                rx.el.div(
                                    rx.icon(
                                        "circle_alert",
                                        class_name="h-12 w-12 text-red-500 mb-4",
                                    ),
                                    rx.el.h3(
                                        "Ops! Algo deu errado",
                                        class_name="text-lg font-bold text-gray-900 mb-2",
                                    ),
                                    rx.el.p(
                                        SearchState.error_message,
                                        class_name="text-red-600 text-sm font-medium text-center mb-6 max-w-md",
                                    ),
                                    rx.el.div(
                                        rx.el.h4(
                                            "Sugestões",
                                            class_name="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2",
                                        ),
                                        rx.el.ul(
                                            rx.el.li(
                                                "• Aguarde alguns segundos e tente novamente.",
                                                class_name="text-sm text-gray-700 font-medium",
                                            ),
                                            rx.el.li(
                                                "• Refine o tema com termos mais específicos.",
                                                class_name="text-sm text-gray-700 font-medium",
                                            ),
                                            rx.el.li(
                                                "• Reduza a quantidade máxima de artigos.",
                                                class_name="text-sm text-gray-700 font-medium",
                                            ),
                                            class_name="space-y-1",
                                        ),
                                        class_name="bg-gray-50 border border-gray-200 rounded-xl p-4 max-w-md w-full",
                                    ),
                                    class_name="flex flex-col items-center justify-center py-12",
                                ),
                                class_name="bg-white rounded-2xl border border-red-200 p-8 min-h-[500px] flex items-center justify-center",
                            ),
                            rx.cond(
                                SearchState.result_content,
                                rx.el.div(
                                    rx.el.div(
                                        rx.el.div(
                                            rx.el.div(
                                                rx.el.h3(
                                                    "Relatório Gerado com Sucesso",
                                                    class_name="text-lg font-bold text-gray-900",
                                                ),
                                                rx.el.p(
                                                    f"Salvo em: {SearchState.saved_file_path}",
                                                    class_name="text-xs text-gray-500 font-mono mt-1 break-all",
                                                ),
                                                rx.el.p(
                                                    f"Concluído em {SearchState.last_completed_seconds:.1f}s",
                                                    class_name="text-xs text-indigo-600 font-semibold mt-1",
                                                ),
                                            ),
                                            class_name="flex-1 min-w-0",
                                        ),
                                        rx.el.div(
                                            rx.el.button(
                                                rx.icon(
                                                    "copy",
                                                    class_name="h-4 w-4 mr-1.5",
                                                ),
                                                "Copiar",
                                                type="button",
                                                on_click=rx.set_clipboard(
                                                    SearchState.result_content
                                                ),
                                                class_name="px-3 py-1.5 rounded-lg border border-gray-200 bg-white text-gray-700 font-semibold text-xs hover:bg-indigo-50 hover:text-indigo-700 hover:border-indigo-200 transition-colors flex items-center",
                                            ),
                                            rx.el.span(
                                                "Resultado Final",
                                                class_name="bg-emerald-100 text-emerald-800 text-xs font-semibold px-2.5 py-1 rounded-full",
                                            ),
                                            class_name="flex items-center gap-2 shrink-0",
                                        ),
                                        class_name="flex justify-between items-start gap-4 border-b border-gray-100 pb-4 mb-6 flex-wrap",
                                    ),
                                    rx.el.div(
                                        rx.markdown(
                                            SearchState.result_content,
                                            class_name="prose prose-indigo max-w-none prose-headings:font-bold prose-p:text-gray-700 prose-li:text-gray-700 prose-table:table-auto prose-th:bg-gray-50 prose-th:p-3 prose-td:p-3 prose-th:border prose-td:border prose-border-gray-200",
                                        ),
                                        class_name="overflow-x-auto",
                                    ),
                                    class_name="bg-white rounded-2xl border border-gray-200 shadow-xs p-8 min-h-[500px]",
                                ),
                                # Initial / Guidance State
                                rx.el.div(
                                    rx.el.div(
                                        rx.icon(
                                            "search-code",
                                            class_name="h-16 w-16 text-indigo-200 mb-4",
                                        ),
                                        rx.el.h2(
                                            "Pronto para Pesquisa Bibliográfica",
                                            class_name="text-2xl font-bold text-gray-800 text-center mb-2",
                                        ),
                                        rx.el.p(
                                            "Insira sua pergunta de pesquisa ou selecione uma das sugestões ao lado para começar.",
                                            class_name="text-gray-500 text-center max-w-md font-medium text-sm mb-8",
                                        ),
                                        rx.el.div(
                                            rx.el.h3(
                                                "📋 O que esperar da resposta?",
                                                class_name="text-sm font-bold text-indigo-900 mb-3 uppercase tracking-wider",
                                            ),
                                            rx.el.ul(
                                                rx.el.li(
                                                    rx.icon(
                                                        "circle_check",
                                                        class_name="h-4 w-4 text-emerald-500 shrink-0",
                                                    ),
                                                    rx.el.span(
                                                        "Integridade absoluta de referências: sem citação fantasma.",
                                                        class_name="text-sm text-indigo-950 font-medium",
                                                    ),
                                                    class_name="flex gap-2.5 items-start",
                                                ),
                                                rx.el.li(
                                                    rx.icon(
                                                        "circle_check",
                                                        class_name="h-4 w-4 text-emerald-500 shrink-0",
                                                    ),
                                                    rx.el.span(
                                                        "Tabelas estruturadas de comparação de artigos científicos.",
                                                        class_name="text-sm text-indigo-950 font-medium",
                                                    ),
                                                    class_name="flex gap-2.5 items-start",
                                                ),
                                                rx.el.li(
                                                    rx.icon(
                                                        "circle_check",
                                                        class_name="h-4 w-4 text-emerald-500 shrink-0",
                                                    ),
                                                    rx.el.span(
                                                        "URLs diretas para validação e leitura de periódicos.",
                                                        class_name="text-sm text-indigo-950 font-medium",
                                                    ),
                                                    class_name="flex gap-2.5 items-start",
                                                ),
                                                class_name="space-y-3",
                                            ),
                                            class_name="bg-indigo-50 border border-indigo-100 rounded-xl p-5 w-full max-w-md",
                                        ),
                                        class_name="flex flex-col items-center py-8",
                                    ),
                                    class_name="bg-white rounded-2xl border border-gray-200 shadow-xs p-8 min-h-[500px] flex items-center justify-center",
                                ),
                            ),
                        ),
                    ),
                    class_name="flex-1 min-w-0",
                ),
                class_name="max-w-7xl mx-auto px-4 py-8 flex flex-col lg:flex-row gap-8",
            ),
        ),
        class_name="min-h-screen bg-gray-50 flex flex-col font-['Inter']",
    )


app = rx.App(
    theme=rx.theme(appearance="light"),
    head_components=[
        rx.el.link(
            rel="preconnect",
            href="https://fonts.googleapis.com",
        ),
        rx.el.link(
            rel="preconnect",
            href="https://fonts.gstatic.com",
            cross_origin="",
        ),
        rx.el.link(
            href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap",
            rel="stylesheet",
        ),
    ],
)
app.add_page(index, route="/")