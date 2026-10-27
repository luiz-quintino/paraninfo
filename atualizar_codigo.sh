#!/bin/bash
echo ""
echo "**************************************************************************************"
echo "*                      Uptade files version 1.0.0 - by Luiz Quintino                 *"
echo "**************************************************************************************"

# Identifica o ambiente: dev | prod
CURRENT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PASTA_AMBIENTE="$(basename "$(dirname "$CURRENT_DIR")")"

case "$PASTA_AMBIENTE" in
    dev_paraninfo)
        GUNICORN_SERVICE="gunicorn_paraninfo_dev"
		AMBIENTE="dev"
		BRANCH="development"
		
        ;;
    prod_paraninfo)
        GUNICORN_SERVICE="gunicorn_paraninfo"
		AMBIENTE="prod"
		BRANCH="main"
		
        ;;
    *)
        echo "[1] ❌  Ambiente desconhecido: $PASTA_AMBIENTE"
        exit 1
        ;;
esac

# Caminho do projeto
PROJETO_DIR="$CURRENT_DIR"
DJANGO_DIR="$PROJETO_DIR/django"
VENV_DIR="$(dirname -- "$CURRENT_DIR")/env"

# Nome do branch
#BRANCH="main"

# Nome do remoto
REMOTO="origin"

echo "🔄 🚀  🚀  Atualizando projeto de PRODUÇÃO em: $PROJETO_DIR..."

# Acessa o diretório do projeto
cd "$PROJETO_DIR" || { echo "[2] ❌  Diretório não encontrado!"; exit 1; }

# Verifica se há mudanças locais não comitadas
if ! git diff-index --quiet HEAD --; then
    echo "⚠️  Existem alterações locais não comitadas?"
    git status
    
    echo ""
    read -r -p "Quer continuar? (s/n):" resposta

    if [[ "$resposta" = "n" || "$resposta" = "N" ]]; then
       echo "Execução abortada."
       exit 1
    fi
    
    echo ""
    echo "forçando atualização..."
    git fetch origin
fi

# Atualiza o código
echo ""
echo "📥  Executando git pull..."

git reset --hard "$REMOTO/$BRANCH"

# Verifica se o pull foi bem-sucedido
if [ $? -eq 0 ]; then
    echo "✅  Código atualizao!"
	chmod +x atualizar_codigo.sh
else
    echo "[3] ❌  Falha ao atualizar o código."
    exit 1
fi
echo ""
echo "🐍  Ativando virtua environment..."
source "$VENV_DIR/bin/activate" || { echo "[4] ❌  Não foi possível ativar o virtualenv!"; exit 1; }


#echo "📦  (Opcional) Instalando dependências..."
# pip install -r "$PROJETO_DIR/requirements.txt"


echo "📂  Coletando arquivos estáticos..."
cd "$DJANGO_DIR" || { echo "[5] ❌  Diretório Django não encontrado!"; exit 1; }
python manage.py collectstatic --noinput
if [ $? -ne 0 ]; then
 echo "[6] ❌  Erro ao executar collectstatic."
 deactivate
 exit 1
fi

echo ""
echo "🚀  Reiniciando Gunicorn..."
sudo systemctl restart "$GUNICORN_SERVICE"
if [ $? -ne 0 ]; then
 echo "[7] ❌  Erro ao reiniciar Gunicorn."
 deactivate
 exit 1
fi

deactivate
echo "✅  Deploy concluído com sucesso!"
