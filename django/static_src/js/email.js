document.addEventListener('DOMContentLoaded', () => {
    const available = document.getElementById('available-list');
    const selected = document.getElementById('selected-list');

    function syncInputs() {
        const container = document.getElementById('selected-inputs');
        if (!container) return;
        container.innerHTML = '';
        selected.querySelectorAll('.recipient').forEach(recipient => {
            const input = document.createElement('input');
            input.type = 'hidden';
            input.name = 'associados';
            input.value = recipient.dataset.id;
            container.appendChild(input);
        });
    }

    function moveRecipient(recipient, destination) {
        destination.appendChild(recipient);
        syncInputs();
    }

    document.getElementById('select-all')?.addEventListener('click', () => {
        [...available.querySelectorAll('.recipient')].forEach(recipient => moveRecipient(recipient, selected));
    });
    document.getElementById('remove-all')?.addEventListener('click', () => {
        [...selected.querySelectorAll('.recipient')].forEach(recipient => moveRecipient(recipient, available));
    });
    available?.addEventListener('click', event => {
        const recipient = event.target.closest('.recipient');
        if (recipient) moveRecipient(recipient, selected);
    });
    selected?.addEventListener('click', event => {
        const recipient = event.target.closest('.recipient');
        if (recipient) moveRecipient(recipient, available);
    });
    syncInputs();

    const modal = document.getElementById('email-detail-modal');
    document.querySelectorAll('.email-row').forEach(row => {
        row.addEventListener('click', async () => {
            const response = await fetch(row.dataset.id + '/detail/');
            if (!response.ok) return;
            const detail = await response.json();
            document.getElementById('detail-data').textContent = detail.data;
            document.getElementById('detail-titulo').textContent = detail.titulo;
            document.getElementById('detail-conteudo').textContent = detail.conteudo;
            document.getElementById('detail-remetente').textContent = detail.remetente;
            document.getElementById('detail-distribuicao').replaceChildren(
                ...detail.distribuicao.map(name => {
                    const item = document.createElement('li');
                    item.textContent = name;
                    return item;
                })
            );
            modal.hidden = false;
        });
    });
    document.getElementById('email-modal-close')?.addEventListener('click', () => modal.hidden = true);
    modal?.addEventListener('click', event => {
        if (event.target === modal) modal.hidden = true;
    });
});
