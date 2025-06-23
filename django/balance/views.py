from django.shortcuts import render
import pandas as pd
from django.core.files.storage import FileSystemStorage

def balance_view(request):
    dataframe = None

    if request.method == 'POST' and 'file' in request.FILES:
        file = request.FILES['file']
        fs = FileSystemStorage()
        filename = fs.save(file.name, file)
        file_path = fs.path(filename)

        try:
            # Ler o arquivo Excel e convertê-lo em um DataFrame
            dataframe = pd.read_excel(file_path)
        except Exception as e:
            is_dataframe_empty = True
            print(f'Erro ao ler o arquivo Excel: {e}')
            return render(request, 'balance.html', {'error': f'O arquivo não e um Excel válido: "{file}"', 'is_dataframe_empty': is_dataframe_empty})

        # Passa uma flag para o template indicando se o DataFrame está vazio
        is_dataframe_empty = dataframe.empty if dataframe is not None else True
        if not is_dataframe_empty:

            if 'EXTRATO CONTA CORRENTE' in dataframe.head(0):
                dataframe = dataframe.fillna('')  # Preenche valores NaN com string vazia
                dataframe.drop(1, inplace=True)  # Remove a primeira linha do DataFrame
                dataframe.columns = ['data', 'documento', 'historico', 'valor']
                return render(request, 'balance.html', {'dataframe': dataframe, 'is_dataframe_empty': is_dataframe_empty, 'file_name': file})
    
        is_dataframe_empty = True
        return render(request, 'balance.html', {'error': f'O arquivo não e um extrato válido: "{file}"', 'is_dataframe_empty': is_dataframe_empty})
    
    return render(request, 'balance.html', {'is_dataframe_empty': True})