// Função para enviar um formulário
function submitForm(formulario) {
    // Exibe a ampulheta antes de enviar o formulário
    showLoadingOverlay();

    // Verifica se o formulário de importação existe e o envia
    const entradaForm = document.getElementById(formulario);
    if (entradaForm) {
        entradaForm.submit(); // Envia o formulário

    } else {
        console.error(`Formulário de análise não encontrado. ${formulario}`);
    }
}

// Função para validar o formato do número
function validarNumero(valor) {
    // Expressão regular para validar números no formato 0,00
    const regex = /^\d{1,3}(\.\d{3})*,\d{2}$/;

    // Verifica se o formato está correto
    return regex.test(valor);
}


// Função para validar o formato e a validade da data
function validarData(data) {
    // Expressão regular para o formato dd/mm/yyyy
    const regex = /^(0[1-9]|[12][0-9]|3[01])\/(0[1-9]|1[0-2])\/\d{4}$/;

    // Verifica se o formato está correto
    if (!regex.test(data)) {
        return false;
    }

    // Divide a data em dia, mês e ano
    const [dia, mes, ano] = data.split('/').map(Number);

    // Cria um objeto Date e verifica se a data é válida
    const dataObj = new Date(ano, mes - 1, dia);
    return (
        dataObj.getFullYear() === ano &&
        dataObj.getMonth() === mes - 1 &&
        dataObj.getDate() === dia
    );
}

function loadPage(page) {
    // Carrega página
    // Exibe a ampulheta antes de enviar o formulário
    window.location.href = page;
   
}
// Tornar a função acessível globalmente
// window.validarNumero = validarNumero;
// window.validarData = validarData;
// window.submitForm = submitForm;