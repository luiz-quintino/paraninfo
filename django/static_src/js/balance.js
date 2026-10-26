document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-copy-pix-code]').forEach((button) => {
        button.addEventListener('click', async () => {
            const codeField = document.getElementById(button.dataset.copyPixCode);
            const status = button.parentElement.querySelector('.next-payment-copy-status');
            if (!codeField) return;

            try {
                if (navigator.clipboard?.writeText) {
                    await navigator.clipboard.writeText(codeField.value);
                } else {
                    codeField.focus();
                    codeField.select();
                    if (!document.execCommand('copy')) throw new Error('Cópia não disponível');
                }
                status.textContent = 'Código Pix copiado. Cole no aplicativo do seu banco.';
            } catch {
                codeField.focus();
                codeField.select();
                status.textContent = 'Selecione e copie o código Pix para colar no aplicativo do seu banco.';
            }
        });
    });
});
