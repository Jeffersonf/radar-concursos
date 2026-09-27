import argparse
import os
import sys
import time
import webbrowser

# Garante suporte adequado a UTF-8 e proteção contra descritores nulos no Windows (modo desacoplado)
if sys.stdout is None:
    try:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    except Exception:
        pass
elif hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

if sys.stderr is None:
    try:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")
    except Exception:
        pass
elif hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from src.engine import ConcursosEngine
from src.web.server import start_server


def cmd_check(args, engine: ConcursosEngine):
    """Executa a verificação dos editais."""
    ufs = args.uf if args.uf else None
    engine.run_scan(ufs_override=ufs)


def cmd_dashboard(args, engine: ConcursosEngine):
    """Inicia o painel visual web."""
    web_conf = engine.config.get("web", {})
    host = args.host or web_conf.get("host", "127.0.0.1")
    port = args.port or web_conf.get("port", 8090)
    auto_open = not args.no_browser and web_conf.get("auto_open_browser", True)

    url = f"http://{host}:{port}/"
    print("\n" + "=" * 70)
    print(" 🚀 INICIANDO PAINEL VISUAL DO RADAR DE CONCURSOS")
    print(f" 🌐 Acesse no seu navegador: {url}")
    print("    Pressione Ctrl+C para encerrar o servidor.")
    print("=" * 70 + "\n")

    if auto_open:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    server = start_server(
        host=host,
        port=port,
        db=engine.db,
        config=engine.config,
        scan_callback=engine.run_scan,
        engine=engine
    )

    while True:
        try:
            server.serve_forever()
            break
        except KeyboardInterrupt:
            if getattr(args, "keep_alive", False):
                time.sleep(0.5)
                continue
            print("\n🛑 Servidor web encerrado com sucesso.")
            server.server_close()
            break
        except Exception:
            time.sleep(1)


def cmd_search(args, engine: ConcursosEngine):
    """Pesquisa rápida por palavra-chave, cargo, salário e UF."""
    results = engine.db.query_concursos(
        uf=args.uf,
        search_query=args.query,
        min_salary=args.min_salary,
        education=args.education,
        only_active=not args.all,
        only_favorites=args.favorites,
        limit=args.limit
    )

    print("\n" + "=" * 80)
    print(f" 🔍 RESULTADOS DA BUSCA (Total encontrado: {len(results)})")
    print("=" * 80)

    if not results:
        print(" Nenhum edital encontrado com os filtros informados.")
        print(" Experimente ampliar a busca ou executar 'python main.py check' primeiro.")
        print("=" * 80 + "\n")
        return

    for c in results:
        engine.console.print_concurso_card(c)
    print()


def cmd_list(args, engine: ConcursosEngine):
    """Lista os concursos cadastrados ou favoritados."""
    results = engine.db.query_concursos(
        only_active=not args.all,
        only_favorites=args.favorites,
        limit=args.limit
    )

    label = "MEUS CONCURSOS FAVORITOS ⭐" if args.favorites else "EDITAIS EM DESTAQUE"
    print("\n" + "=" * 80)
    print(f" 📋 {label} (Exibindo {len(results)})")
    print("=" * 80)

    if not results:
        if args.favorites:
            print(" Nenhum concurso favoritado ainda. Use o painel web ou o comando de favoritos para marcar.")
        else:
            print(" Nenhum concurso no banco. Execute 'python main.py check' primeiro.")
        print("=" * 80 + "\n")
        return

    for c in results:
        engine.console.print_concurso_card(c)
    print()


def cmd_stats(args, engine: ConcursosEngine):
    """Exibe estatísticas gerais dos concursos cadastrados."""
    stats = engine.db.get_stats()
    print("\n" + "=" * 60)
    print(" 📊 ESTATÍSTICAS DO RADAR DE CONCURSOS")
    print("=" * 60)
    print(f" • Total de editais no banco: {stats['total']}")
    print(f" • Editais com inscrições abertas: {stats['open']}")
    print(f" • Concursos marcados como favoritos: {stats['favorites']}")
    
    sal_max = f"R$ {stats['max_salary']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    print(f" • Maior salário registrado: {sal_max}")

    print("\n 📍 Principais Estados com Vagas:")
    for item in stats.get("top_ufs", []):
        print(f"   - {item['uf']}: {item['count']} editais")
    print("=" * 60 + "\n")


def cmd_config(args, engine: ConcursosEngine):
    """Gerencia filtros e preferências."""
    cfg = engine.config

    if args.add_keyword:
        kw = args.add_keyword.strip().lower()
        if kw not in cfg["filters"]["keywords"]:
            cfg["filters"]["keywords"].append(kw)
            print(f"✅ Palavra-chave '{kw}' adicionada aos filtros.")

    if args.del_keyword:
        kw = args.del_keyword.strip().lower()
        if kw in cfg["filters"]["keywords"]:
            cfg["filters"]["keywords"].remove(kw)
            print(f"🗑️ Palavra-chave '{kw}' removida dos filtros.")

    if args.min_salary is not None:
        cfg["filters"]["min_salary"] = args.min_salary
        print(f"✅ Salário mínimo configurado para R$ {args.min_salary:,.2f}")

    if args.telegram_token and args.telegram_chat:
        cfg["notifications"]["telegram"]["enabled"] = True
        cfg["notifications"]["telegram"]["bot_token"] = args.telegram_token
        cfg["notifications"]["telegram"]["chat_id"] = args.telegram_chat
        print("✅ Notificações do Telegram configuradas e ativadas.")

    if args.discord_webhook:
        cfg["notifications"]["discord"]["enabled"] = True
        cfg["notifications"]["discord"]["webhook_url"] = args.discord_webhook
        print("✅ Webhook do Discord configurado e ativado.")

    engine.save_config(cfg)

    print("\n" + "=" * 60)
    print(" ⚙️ CONFIGURAÇÃO ATUAL:")
    print("=" * 60)
    print(f" • UFs monitoradas: {', '.join(cfg['sources']['pci_concursos']['ufs']).upper()}")
    print(f" • Salário mínimo: R$ {cfg['filters'].get('min_salary', 0):,.2f}")
    keywords = cfg['filters'].get('keywords', [])
    print(f" • Palavras-chave: {', '.join(keywords) if keywords else 'Nenhuma (coleta tudo)'}")
    print(f" • Telegram ativado: {'Sim' if cfg['notifications']['telegram'].get('enabled') else 'Não'}")
    print(f" • Discord ativado: {'Sim' if cfg['notifications']['discord'].get('enabled') else 'Não'}")
    print("=" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="🎯 Monitor Inteligente de Concursos Públicos - Rastreamento contínuo de editais, vagas e salários.",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest="command", help="Comando a ser executado")

    # Comando 'check'
    p_check = subparsers.add_parser("check", help="Executa varredura de novos editais no PCI Concursos")
    p_check.add_argument("--uf", nargs="+", help="UFs específicas para escanear (ex: --uf sp rj nacional)")
    p_check.set_defaults(func=cmd_check)

    # Comando 'dashboard'
    p_dash = subparsers.add_parser("dashboard", help="Inicia o painel visual interativo no navegador")
    p_dash.add_argument("--port", type=int, default=None, help="Porta HTTP do servidor (padrão: 8090 ou configurada no settings.json)")
    p_dash.add_argument("--host", default="127.0.0.1", help="Endereço IP (padrão: 127.0.0.1)")
    p_dash.add_argument("--no-browser", action="store_true", help="Não abre automaticamente o navegador")
    p_dash.add_argument("--keep-alive", action="store_true", help="Mantém o servidor ativo ininterruptamente")
    p_dash.set_defaults(func=cmd_dashboard)

    # Comando 'search'
    p_search = subparsers.add_parser("search", help="Busca editais no banco por palavras, cargos e valores")
    p_search.add_argument("-q", "--query", help="Termo de busca (ex: analista, ti, tribunal)")
    p_search.add_argument("--uf", help="Filtrar por estado (ex: SP, DF, NACIONAL)")
    p_search.add_argument("--min-salary", type=float, help="Filtrar por salário mínimo (ex: 5000)")
    p_search.add_argument("--education", help="Filtrar por escolaridade (Superior, Médio, Técnico)")
    p_search.add_argument("--favorites", action="store_true", help="Apenas concursos marcados como favoritos")
    p_search.add_argument("--all", action="store_true", help="Incluir concursos com prazo expirado")
    p_search.add_argument("--limit", type=int, default=20, help="Quantidade de itens exibidos (padrão: 20)")
    p_search.set_defaults(func=cmd_search)

    # Comando 'list'
    p_list = subparsers.add_parser("list", help="Lista editais com inscrições abertas ou favoritos")
    p_list.add_argument("--favorites", action="store_true", help="Listar apenas favoritos")
    p_list.add_argument("--all", action="store_true", help="Incluir encerrados")
    p_list.add_argument("--limit", type=int, default=25, help="Limite de editais (padrão: 25)")
    p_list.set_defaults(func=cmd_list)

    # Comando 'stats'
    p_stats = subparsers.add_parser("stats", help="Exibe resumo estatístico dos concursos monitorados")
    p_stats.set_defaults(func=cmd_stats)

    # Comando 'config'
    p_conf = subparsers.add_parser("config", help="Visualiza ou altera parâmetros de busca e notificações")
    p_conf.add_argument("--add-keyword", help="Adicionar palavra-chave de interesse aos filtros")
    p_conf.add_argument("--del-keyword", help="Remover palavra-chave")
    p_conf.add_argument("--min-salary", type=float, help="Definir piso salarial de interesse")
    p_conf.add_argument("--telegram-token", help="Token do Bot do Telegram")
    p_conf.add_argument("--telegram-chat", help="ID do Chat do Telegram")
    p_conf.add_argument("--discord-webhook", help="URL do Webhook do Discord")
    p_conf.set_defaults(func=cmd_config)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    engine = ConcursosEngine()
    args.func(args, engine)


if __name__ == "__main__":
    main()
