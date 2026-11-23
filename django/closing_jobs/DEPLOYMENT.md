# Fechamento assíncrono do balanço

A fila usa o banco de dados do próprio Django. Não precisa de Celery nem Redis. O comando de consumo é o mesmo no Windows e no Linux; muda somente a forma de manter o processo ativo.

## Desenvolvimento local no Windows

1. Aponte o `.env` para uma base de desenvolvimento/staging. O fechamento altera dados contábeis; não valide a fila usando a base de produção.
2. Em um terminal, na pasta `django`, aplique a migração:

   ```powershell
   ..\env\Scripts\python.exe manage.py migrate closing_jobs
   ```

3. Em outro terminal, inicie o worker e deixe-o ativo:

   ```powershell
   ..\env\Scripts\python.exe manage.py run_balance_closing_worker --poll-interval 3
   ```

4. Inicie o Django como de costume. Confirme um fechamento pela página. A página mostrará o estado da tarefa; fechar ou atualizar o navegador não para o worker.

Para interromper o worker durante desenvolvimento, use Ctrl+C. Ele terminará a tarefa atual e então sairá. Não teste um fechamento real sem validar antes a base de dados configurada no `.env`.

## Servidor Linux com Nginx

1. Publique o mesmo código e as mesmas dependências usadas localmente. Configure o `.env` do projeto com os dados do banco e caminhos corretos, sem versioná-lo.
2. Execute a migração uma vez, usando o mesmo ambiente virtual e `.env` do Django:

   ```bash
   /srv/paraninfo/env/bin/python /srv/paraninfo/django/manage.py migrate closing_jobs
   ```

3. Crie `/etc/systemd/system/paraninfo-balance-worker.service`, ajustando usuário e diretório para a instalação real:

   ```ini
   [Unit]
   Description=Worker de fechamento de balanço Paraninfo
   After=network.target

   [Service]
   Type=simple
   User=paraninfo
   Group=paraninfo
   WorkingDirectory=/srv/paraninfo/django
   Environment=PYTHONUNBUFFERED=1
   ExecStart=/srv/paraninfo/env/bin/python manage.py run_balance_closing_worker --poll-interval 3
   Restart=on-failure
   RestartSec=5
   TimeoutStopSec=infinity

   [Install]
   WantedBy=multi-user.target
   ```

4. Habilite e inicie o serviço:

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now paraninfo-balance-worker
   sudo systemctl status paraninfo-balance-worker
   ```

5. Veja os logs:

   ```bash
   sudo journalctl -u paraninfo-balance-worker -f
   ```

O Nginx não precisa encaminhar tráfego para o worker nem de uma configuração nova. Ele continua encaminhando as requisições web ao Django; o worker é um serviço separado, ligado ao mesmo banco e ao mesmo diretório de mídia/recursos. Garanta que o usuário do serviço possa ler os recursos e certificados e gravar os relatórios e arquivos necessários.

## Operação e recuperação

Execute inicialmente **um único worker**. Cada tarefa salva a comissão, mês, ano e sequência esperados, e o sistema impede uma segunda solicitação para o mesmo fechamento. Uma falha fica registrada e não é reenfileirada automaticamente, pois o processamento pode já ter feito gravações parciais. Revise banco, relatório e logs antes de qualquer recuperação manual.

Um encerramento normal do serviço (Ctrl+C ou SIGTERM) espera a tarefa atual terminar. Desligamento forçado, falha de máquina ou `kill -9` ainda pode interrompê-la; nesse caso, a tarefa fica com estado `Em execução` para revisão manual e não deve ser repetida sem conferir os efeitos já realizados.
