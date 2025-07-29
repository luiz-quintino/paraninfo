function showPopup(type, message, title, callback) {
    const popup = document.getElementById('custom-popup');
    const popupIcon = document.getElementById('popup-icon');
    const popupTitle = document.getElementById('popup-title');
    const popupMessage = document.getElementById('popup-message');
    const popupInput = document.getElementById('popup-input');
    const popupCancel = document.getElementById('popup-cancel');
    const popupClose = document.getElementById('popup-close');
    const popupConfirm = document.getElementById('popup-confirm');

    // Configurar o ícone e a cor do título com base no tipo
    switch (type) {
        case 'warning':
            popupIcon.src = "/static/media/icons/alerta.png";
            popupTitle.style.color = '#ff9800';
            popupCancel.style.display = 'none';
            popupConfirm.style.display = 'none';
            popupInput.style.display = 'none';
            title = title || 'Alerta'; // Definir título padrão se não for fornecido
            break;
        case 'info':
            popupIcon.src = "/static/media/icons/info.png";
            popupTitle.style.color = '#2196f3';
            popupCancel.style.display = 'none';
            popupConfirm.style.display = 'none';
            popupInput.style.display = 'none';
            title = title || 'Informação'; // Definir título padrão se não for fornecido
            break;
        case 'error':
            popupIcon.src = "/static/media/icons/error.png";
            popupTitle.style.color = '#f44336';
            popupCancel.style.display = 'none';
            popupConfirm.style.display = 'none';
            popupInput.style.display = 'none';
            title = title || 'Erro'; // Definir título padrão se não for fornecido
            break;
        case 'confirm':
            popupIcon.src = "/static/media/icons/confirm.png";
            popupTitle.style.color = '#4caf50';
            popupCancel.style.display = 'inline-block';
            popupConfirm.style.display = 'inline-block';
            popupInput.style.display = 'none';
            title = title || 'Confirmação'; // Definir título padrão se não for fornecido
            break;
            break;
        case 'input':
            popupIcon.src = "/static/media/icons/entrada.png";
            popupTitle.style.color = '#4caf50';
            popupCancel.style.display = 'inline-block';
            popupConfirm.style.display = 'inline-block';
            popupInput.style.display = 'block';
            title = title || 'Entrada de Dados'; // Definir título padrão se não for fornecido
            break;
        default:
            console.error('Tipo de popup inválido.');
            return;
    }

    // Configurar o título e a mensagem
    popupTitle.innerText = title;
    popupMessage.innerText = message;

    // Exibir o popup
    popup.style.display = 'flex';

    // Fechar o popup ao clicar em "Fechar"
    popupClose.onclick = () => {
        popup.style.display = 'none';
    };

    // Fechar o popup ao clicar em "Cancelar"
    popupCancel.onclick = () => {
        popup.style.display = 'none';
    };

    // Confirmar ação ao clicar em "Confirmar"
    popupConfirm.onclick = () => {
        const inputValue = popupInput.value;
        console.log(callback, inputValue); // Log para depuração

        if (callback) {
            console.log('Callback function is valid'); // Log para depuração
            if (inputValue) {
                callback(inputValue); // Chamar a função de callback com o valor do input
            } else {
                eval(callback); 
            }
        }
        popup.style.display = 'none';
    };
}