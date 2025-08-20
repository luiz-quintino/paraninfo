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