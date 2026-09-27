# 🎯 Monitor Inteligente de Concursos Públicos

Sistema autônomo, rápido e modular para monitoramento contínuo de editais, vagas e salários de concursos públicos no Brasil.

Construído em **Python puro** (sem dependências externas pesadas como Selenium ou Node.js), pronto para uso imediato no Windows.

---

## 🌟 Principais Recursos

- **📡 Coleta Abrangente:** Monitora mais de **470+ editais ativos** em todo o Brasil (Nacional e todos os 27 estados: SP, MG, RJ, DF, etc.) via PCI Concursos.
- **💰 Normalização Inteligente de Salários:** Converte faixas salariais em números de ponto flutuante, permitindo filtros matemáticos (ex: `salário >= R$ 10.000,00`).
- **⏳ Contagem Regressiva de Inscrições:** Rastreia as datas limites com alerta de urgência ("Restam 3 dias", "Último dia hoje!").
- **🛡️ Deduplicação & Zero Spam:** Banco SQLite integrado que registra o que já foi visto e alerta apenas sobre **novos editais** ou retificações.
- **🌐 Painel Web Interativo (Dashboard):** Interface moderna local (`http://127.0.0.1:8090`) com filtros dinâmicos, busca instantânea, favoritos e botão de varredura sob demanda.
- **🔔 Canais de Notificação:**
  - Exibição rica no terminal (com suporte UTF-8).
  - Relatório consolidado em Markdown (`data/relatorio_atual.md`).
  - Alertas diretos no **Telegram** (Bot API gratuito).
  - Alertas em canal do **Discord** (Embeds coloridos via Webhook).

---

## 🚀 Como Usar

### 1. Iniciar o Painel Web (Dashboard Visual)
Abra o painel no seu navegador para pesquisar, filtrar por sua carreira e favoritar oportunidades:
```bash
python main.py dashboard
# ou especificar outra porta:
python main.py dashboard --port 8090
```
> O navegador abrirá automaticamente em `http://127.0.0.1:8090`.

---

### 2. Executar Varredura de Novos Editais
Para escanear todos os editais do Brasil e registrar no banco:
```bash
python main.py check
```

Para escanear apenas estados específicos:
```bash
python main.py check --uf sp rj mg
```

---

### 3. Pesquisar Concursos pelo Terminal
Busque por palavra-chave, cargo, salário mínimo e estado:
```bash
# Buscar editais para "analista" com salário acima de R$ 6.000:
python main.py search -q "analista" --min-salary 6000

# Buscar editais de TI no estado de São Paulo:
python main.py search -q "ti" --uf SP

# Buscar editais de nível superior:
python main.py search --education Superior --min-salary 10000
```

---

### 4. Ver Estatísticas e Favoritos
```bash
# Ver resumo geral (total de editais abertos, maior salário, estados com mais vagas):
python main.py stats

# Listar concursos marcados como favoritos:
python main.py list --favorites
```

---

### 5. Configurar Filtros e Canais de Alerta

#### Configurar Piso Salarial e Palavras-chave de Interesse:
```bash
# Adicionar palavras-chave (notifica automaticamente quando surgirem editais compatíveis):
python main.py config --add-keyword "analista"
python main.py config --add-keyword "tecnologia"

# Definir piso salarial de interesse:
python main.py config --min-salary 8000
```

#### Ativar Notificações no Telegram:
1. Crie um bot no Telegram com o [@BotFather](https://t.me/BotFather) e pegue o `TOKEN`.
2. Pegue seu `CHAT_ID` (com o bot [@userinfobot](https://t.me/userinfobot)).
3. Ative com o comando:
```bash
python main.py config --telegram-token "SEU_TOKEN_AQUI" --telegram-chat "SEU_CHAT_ID_AQUI"
```

#### Ativar Notificações no Discord:
Crie um webhook no canal do Discord e configure:
```bash
python main.py config --discord-webhook "https://discord.com/api/webhooks/..."
```

---

## ⏰ Como Agendar a Execução Automática

### Opção 1: Agendador de Tarefas do Windows (Task Scheduler)
Para executar a cada 6 ou 12 horas em segundo plano:
1. Abra o **PowerShell** como Administrador.
2. Execute o comando para criar a tarefa:
```powershell
$Action = New-ScheduledTaskAction -Execute "python.exe" -Argument "main.py check" -WorkingDirectory "C:\Users\jeffe\.gemini\antigravity\scratch\monitor-concursos"
$Trigger = New-ScheduledTaskTrigger -Daily -At 08:00
Register-ScheduledTask -TaskName "MonitorConcursosCheck" -Action $Action -Trigger $Trigger
```

### Opção 2: Comando `/schedule` do Antigravity
Você pode pedir ao agente Antigravity para agendar a varredura recorrente usando o comando `/schedule`.

---

## 📁 Estrutura do Projeto

```text
monitor-concursos/
├── .github/workflows/
│   └── scrape_and_deploy.yml  # Automação GitHub Actions: varredura 6h/6h e deploy Pages
├── config/
│   └── settings.json          # Filtros salvos, UFs alvo e credenciais de notificação
├── data/
│   ├── concursos.db           # Banco de dados SQLite persistente e otimizado
│   └── relatorio_atual.md     # Relatório executivo gerado na última checagem
├── docs/                      # Bundle estático pronto para GitHub Pages (zero servidor)
│   ├── index.html
│   ├── style.css
│   ├── app.js
│   ├── concursos.json
│   └── data/
├── src/
│   ├── collector.py           # Coletor HTTP com detecção automática de charset
│   ├── database.py            # Persistência SQLite, deduplicação e busca com filtros
│   ├── geo_engine.py          # Cálculo de distância Haversine e radar de proximidade
│   ├── notifiers/             # Console, Markdown, Telegram e Discord
│   ├── parsers/               # Parser estruturado do PCI Concursos + detalhes profundos
│   └── web/                   # Servidor HTTP nativo e Dashboard web interativo
├── tests/
│   └── test_monitor.py        # 11 testes automatizados (100% passando)
├── export_static.py           # Gerador da versão estática para GitHub Pages
├── main.py                    # Ponto de entrada CLI e Dashboard local
└── README.md                  # Este manual
```

---

## 🌐 Publicação no GitHub Pages (100% Grátis)

O projeto já conta com arquitetura **JAMstack híbrida**: ele pode rodar localmente no seu computador ou 100% online no GitHub Pages sem precisar de nenhum servidor ligado.

### Como subir para o seu GitHub:

1. **Crie um repositório no GitHub** (pode ser público ou privado).
2. **Faça o commit e push dos arquivos:**
   ```bash
   git add .
   git commit -m "feat: publicar monitor de concursos com suporte a GitHub Pages"
   git remote add origin https://github.com/SEU_USUARIO/SEU_REPOSITORIO.git
   git branch -M main
   git push -u origin main
   ```
3. **Ative o GitHub Pages:**
   - No GitHub, acesse: **Settings** > **Pages**.
   - Em **Build and deployment** > **Source**, escolha:
     - Opção 1 (*Mais fácil*): Selecione **Deploy from a branch**, escolha o branch `main` e a pasta `/docs`, e clique em **Save**.
     - Opção 2 (*Automático via Actions*): Selecione **GitHub Actions**. O workflow `.github/workflows/scrape_and_deploy.yml` fará o deploy automático!
4. **Pronto!** Em poucos segundos seu site estará acessível no link público:
   `https://SEU_USUARIO.github.io/SEU_REPOSITORIO/`

### ⏰ Varredura Automática (GitHub Actions)
- O GitHub Actions executará o scraper automaticamente **a cada 6 horas**, atualizará a base de editais e publicará no GitHub Pages sem gastar nada da sua cota.
- Você também pode forçar uma varredura a qualquer momento na aba **Actions** > **Varredura de Editais & Publicação GitHub Pages** > **Run workflow**.
